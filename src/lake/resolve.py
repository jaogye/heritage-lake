"""Entity resolution: which records, across and within sources, are the same object?

Approach (a hand-weighted Fellegi–Sunter style model, chosen because the
evidence is few, strong signals and every decision must be explainable to a
curator):

1. Blocking: only compare records sharing an institution, a creator key, an
   inventory number or a Wikidata QID. Keeps comparisons near-linear.
2. Scoring: each piece of evidence adds or subtracts a log-odds-like weight and
   leaves a human-readable reason.
3. Decision: >= MATCH merges, between REVIEW and MATCH goes to a curator review
   queue, below is a non-match.
4. Clustering: constrained union-find, strongest links first, refusing any
   merge that would put two different Wikidata QIDs in one entity.

Titles are a weak signal here on purpose: the same painting is "The Fall of the
Rebel Angels", "De val van de opstandige engelen" and "La Chute des anges
rebelles". Cross-lingual title similarity is better handled with multilingual
embeddings (see heritage-atlas); inventory numbers do the heavy lifting.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from rapidfuzz import fuzz

from .names import fold, keys_match
from .normalize import SilverRecord

MATCH, REVIEW = 10.0, 5.0
MAX_BLOCK = 500
SOURCE_PRIORITY = {"wikidata": 0, "europeana": 2}  # websites default to 1


@dataclass
class Link:
    left: str
    right: str
    score: float
    decision: str
    reasons: list[str]


def _title_norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", fold(t))


def score_pair(a: SilverRecord, b: SilverRecord) -> tuple[float, list[str]]:
    score, why = 0.0, []

    def add(w: float, reason: str) -> None:
        nonlocal score
        score += w
        why.append(f"{w:+g} {reason}")

    if a.wikidata_qid and b.wikidata_qid:
        if a.wikidata_qid == b.wikidata_qid:
            add(20, "same Wikidata QID")
        else:
            add(-20, "different Wikidata QIDs")

    same_inst = None
    if a.institution_known and b.institution_known:
        same_inst = a.institution == b.institution
        add(2, "same institution") if same_inst else add(-6, "different institutions")

    if a.inventory_no and b.inventory_no and same_inst is not False:
        if a.inventory_no == b.inventory_no:
            add(9, f"same inventory number {a.inventory_no}")
        elif same_inst:
            add(-8, "different inventory numbers at same institution")

    if a.creator_keys and b.creator_keys:
        if any(keys_match(x, y) for x in a.creator_keys for y in b.creator_keys):
            add(3, "creator overlap")
        else:
            add(-3, "no creator overlap")

    if a.year_start is not None and b.year_start is not None:
        if a.year_start <= b.year_end and b.year_start <= a.year_end:
            add(1.5, "dates overlap")
        else:
            add(-4, "dates incompatible")

    if a.title and b.title:
        sim = fuzz.token_set_ratio(_title_norm(a.title), _title_norm(b.title))
        if sim >= 90:
            add(5, f"titles near-identical ({sim:.0f})")
        elif sim >= 75:
            add(2.5, f"titles similar ({sim:.0f})")
        elif sim < 40:
            add(-1, f"titles dissimilar ({sim:.0f})")

    return score, why


def candidate_pairs(records: list[SilverRecord]) -> set[tuple[int, int]]:
    blocks: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        if r.wikidata_qid:
            blocks[f"qid:{r.wikidata_qid}"].append(i)
        if r.institution:
            blocks[f"inst:{r.institution}"].append(i)
        if r.inventory_no:
            blocks[f"inv:{r.inventory_no}"].append(i)
        for k in r.creator_keys:
            blocks[f"creator:{k[:4]}"].append(i)  # prefix tolerates Memling/Memlinc
    pairs: set[tuple[int, int]] = set()
    for members in blocks.values():
        if len(members) > MAX_BLOCK:
            continue  # a huge block carries no discriminating power; other keys cover it
        pairs.update(combinations(sorted(set(members)), 2))
    return pairs


def _anchor_rank(r: SilverRecord) -> tuple[int, str]:
    return SOURCE_PRIORITY.get(r.source, 1), r.record_key


def resolve(
    records: list[SilverRecord], curator: dict[frozenset[str], str] | None = None
) -> tuple[dict[str, str], list[Link]]:
    """Return (record_key -> entity_id, scored links).

    `curator` holds past review decisions ({record_a, record_b} -> "accept" | "reject"),
    so a pair a curator has settled never comes back to the review queue.
    """
    curator = curator or {}
    links: list[Link] = []
    for i, j in candidate_pairs(records):
        a, b = records[i], records[j]
        s, why = score_pair(a, b)
        decision = "match" if s >= MATCH else "review" if s >= REVIEW else "non-match"
        verdict = curator.get(frozenset((a.record_key, b.record_key)))
        if verdict == "accept":
            decision, s = "match", max(s, MATCH)
            why.append("curator accepted")
        elif verdict == "reject":
            decision = "non-match"
            why.append("curator rejected")
        links.append(Link(a.record_key, b.record_key, s, decision, why))

    parent = {r.record_key: r.record_key for r in records}
    qids = {r.record_key: {r.wikidata_qid} - {None} for r in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for link in sorted(links, key=lambda lk: -lk.score):
        if link.decision != "match":
            continue
        ra, rb = find(link.left), find(link.right)
        if ra == rb:
            continue
        if qids[ra] and qids[rb] and qids[ra] != qids[rb]:
            link.decision = "blocked"
            link.reasons.append("merge refused: clusters carry different Wikidata QIDs")
            continue
        parent[rb] = ra
        qids[ra] |= qids[rb]

    clusters: dict[str, list[SilverRecord]] = defaultdict(list)
    for r in records:
        clusters[find(r.record_key)].append(r)
    entity_of: dict[str, str] = {}
    for members in clusters.values():
        anchor = min(members, key=_anchor_rank).record_key
        eid = "hl_" + hashlib.sha1(anchor.encode()).hexdigest()[:10]
        for m in members:
            entity_of[m.record_key] = eid
    links.sort(key=lambda lk: (lk.decision, -lk.score))
    return entity_of, links


def load_curator_decisions(path) -> dict[frozenset[str], str]:
    """CSV with columns left,right,verdict (accept|reject), e.g. exported from the review queue."""
    import csv
    from pathlib import Path

    out: dict[frozenset[str], str] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            verdict = row["verdict"].strip().lower()
            if verdict not in {"accept", "reject"}:
                raise ValueError(f"unknown verdict {verdict!r} for {row['left']} / {row['right']}")
            out[frozenset((row["left"].strip(), row["right"].strip()))] = verdict
    return out
