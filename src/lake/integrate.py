"""Gold: merge resolved records into one row per object and join in-house data.

Survivorship rules decide which source wins each field, and every winning value
keeps a pointer to the record it came from (`provenance`), so any number in the
final dataset can be traced back to a URL.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .institutions import resolve_institution
from .names import fold, keys_match, parse_creator
from .normalize import SilverRecord, norm_inventory
from .resolve import Link

DEFAULT_ORDER = ["wikidata", "*", "europeana"]  # "*" = museum websites and other sources
FIELD_ORDER = {
    "title": DEFAULT_ORDER,
    "creators": ["*", "wikidata", "europeana"],  # museums record attribution nuance best
    "object_type": DEFAULT_ORDER,
    "materials": ["*", "wikidata", "europeana"],
    "subjects": DEFAULT_ORDER,
    "inventory_no": ["*", "wikidata", "europeana"],
    "description": ["*", "europeana", "wikidata"],  # Wikidata descriptions are one-liners
    "institution": DEFAULT_ORDER,
    "wikidata_qid": DEFAULT_ORDER,
}
OPEN_RIGHTS = ("publicdomain", "creativecommons.org/licenses/by/", "/cc0", "zero/1.0")


def _rank(source: str, order: list[str]) -> int:
    return order.index(source) if source in order else order.index("*")


def _pick(members: list[SilverRecord], fld: str) -> tuple[Any, str | None]:
    order = FIELD_ORDER.get(fld, DEFAULT_ORDER)
    for r in sorted(members, key=lambda m: (_rank(m.source, order), m.record_key)):
        v = getattr(r, fld)
        if v not in (None, "", []):
            return v, r.record_key
    return ([] if isinstance(getattr(members[0], fld), list) else None), None


def _pick_image(members: list[SilverRecord]) -> tuple[str | None, str | None, str | None]:
    with_img = [m for m in members if m.image_url]
    if not with_img:
        return None, None, None

    def key(m: SilverRecord):
        is_open = bool(m.rights) and any(t in m.rights.lower() for t in OPEN_RIGHTS)
        return (not is_open, _rank(m.source, DEFAULT_ORDER), m.record_key)

    best = min(with_img, key=key)
    return best.image_url, best.rights, best.record_key


def _pick_date(members: list[SilverRecord]) -> tuple[dict[str, Any], str | None, bool]:
    dated = [m for m in members if m.year_start is not None]
    if not dated:
        return (
            {"year_start": None, "year_end": None, "date_approx": None, "date_text": None},
            None,
            False,
        )
    # the narrowest documented range wins; ties go to source priority
    best = min(dated, key=lambda m: (m.year_end - m.year_start, _rank(m.source, DEFAULT_ORDER)))
    conflict = any(
        m.year_start > o.year_end or o.year_start > m.year_end for m in dated for o in dated
    )
    return (
        {
            "year_start": best.year_start,
            "year_end": best.year_end,
            "date_approx": best.date_approx,
            "date_text": best.date_text,
        },
        best.record_key,
        conflict,
    )


@dataclass
class InhouseRow:
    catalogue_id: str
    institution: str | None
    inventory_no: str | None
    working_title: str
    artist: str | None
    themes: list[str] = field(default_factory=list)
    research_notes: str | None = None
    image_rights_cleared: bool = False


def load_inhouse(path: Path) -> list[InhouseRow]:
    rows = []
    with Path(path).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inst, _, _ = resolve_institution(r.get("institution"))
            rows.append(
                InhouseRow(
                    catalogue_id=r["catalogue_id"].strip(),
                    institution=inst,
                    inventory_no=norm_inventory(r.get("inventory_no")),
                    working_title=r["working_title"].strip(),
                    artist=(r.get("artist") or "").strip() or None,
                    themes=[t.strip() for t in (r.get("themes") or "").split(";") if t.strip()],
                    research_notes=(r.get("research_notes") or "").strip() or None,
                    image_rights_cleared=(r.get("image_rights_cleared") or "").strip().lower()
                    in {"1", "true", "yes", "y"},
                )
            )
    return rows


def build_gold(
    silver: list[SilverRecord],
    entity_of: dict[str, str],
    links: list[Link],
    inhouse: list[InhouseRow] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (gold rows, in-house match report)."""
    clusters: dict[str, list[SilverRecord]] = defaultdict(list)
    for r in silver:
        clusters[entity_of[r.record_key]].append(r)
    in_review = {entity_of[lk.left] for lk in links if lk.decision == "review"} | {
        entity_of[lk.right] for lk in links if lk.decision == "review"
    }

    gold: dict[str, dict[str, Any]] = {}
    for eid, members in clusters.items():
        row: dict[str, Any] = {"entity_id": eid}
        prov: dict[str, str | None] = {}
        for fld in FIELD_ORDER:
            row[fld], prov[fld] = _pick(members, fld)
        if prov["creators"]:
            src = next(m for m in members if m.record_key == prov["creators"])
            row["creator_roles"], row["creator_keys"] = src.creator_roles, src.creator_keys
        else:
            row["creator_roles"], row["creator_keys"] = [], []
        date, prov["date"], date_conflict = _pick_date(members)
        row.update(date)
        row["image_url"], row["rights"], prov["image_url"] = _pick_image(members)
        inst_rec = next((m for m in members if m.record_key == prov["institution"]), None)
        row["city"] = inst_rec.city if inst_rec else None
        row["titles"] = sorted({m.title for m in members if m.title})
        row["source_records"] = sorted(m.record_key for m in members)
        row["sources"] = sorted({m.source for m in members})
        row["source_urls"] = sorted({m.url for m in members if m.url})
        row["n_sources"] = len(row["sources"])

        flags = []
        if row["n_sources"] == 1:
            flags.append("single-source")
        if date_conflict:
            flags.append("date-conflict")
        if not row["image_url"]:
            flags.append("no-image")
        if eid in in_review:
            flags.append("pending-review")
        flags += sorted(
            {
                f"unknown-institution:{m.institution_raw}"
                for m in members
                if m.institution_raw and not m.institution_known
            }
        )
        row["flags"] = flags
        row["provenance"] = json.dumps(prov, sort_keys=True)
        row.update(inhouse_id=None, themes=[], research_notes=None, image_rights_cleared=None)
        gold[eid] = row

    report: list[dict[str, Any]] = []
    for ih in inhouse or []:
        eid, how = _match_inhouse(ih, gold)
        if eid is None:
            eid = "hl_" + hashlib.sha1(f"inhouse:{ih.catalogue_id}".encode()).hexdigest()[:10]
            creator = parse_creator(ih.artist)
            gold[eid] = {
                "entity_id": eid,
                "title": ih.working_title,
                "titles": [ih.working_title],
                "creators": [creator.name] if creator and creator.name else [],
                "creator_roles": [creator.role] if creator else [],
                "creator_keys": [creator.key] if creator and creator.key else [],
                "object_type": None,
                "materials": [],
                "subjects": [],
                "inventory_no": ih.inventory_no,
                "description": None,
                "institution": ih.institution,
                "wikidata_qid": None,
                "city": None,
                "year_start": None,
                "year_end": None,
                "date_approx": None,
                "date_text": None,
                "image_url": None,
                "rights": None,
                "source_records": [],
                "sources": ["inhouse"],
                "source_urls": [],
                "n_sources": 1,
                "flags": ["inhouse-only", "no-image"],
                "provenance": json.dumps({"title": f"inhouse:{ih.catalogue_id}"}),
            }
        else:
            if "inhouse" not in gold[eid]["sources"]:
                gold[eid]["sources"] = sorted([*gold[eid]["sources"], "inhouse"])
                gold[eid]["n_sources"] += 1
                if gold[eid]["n_sources"] > 1 and "single-source" in gold[eid]["flags"]:
                    gold[eid]["flags"].remove("single-source")
        gold[eid].update(
            inhouse_id=ih.catalogue_id,
            themes=ih.themes,
            research_notes=ih.research_notes,
            image_rights_cleared=ih.image_rights_cleared,
        )
        report.append({"catalogue_id": ih.catalogue_id, "entity_id": eid, "match": how})

    return sorted(gold.values(), key=lambda r: r["entity_id"]), report


def _match_inhouse(ih: InhouseRow, gold: dict[str, dict[str, Any]]) -> tuple[str | None, str]:
    candidates = [g for g in gold.values() if g["institution"] == ih.institution]
    if ih.inventory_no:
        for g in candidates:
            if g["inventory_no"] == ih.inventory_no:
                return g["entity_id"], "inventory"
    artist = parse_creator(ih.artist) if ih.artist else None
    best, best_sim = None, 0.0
    for g in candidates:
        sim = max(
            (fuzz.token_set_ratio(fold(ih.working_title), fold(t)) for t in g["titles"]), default=0
        )
        creator_ok = bool(
            artist and artist.key and any(keys_match(artist.key, k) for k in g["creator_keys"])
        )
        if (sim >= 85 and creator_ok) or sim >= 95:
            if sim > best_sim:
                best, best_sim = g["entity_id"], sim
    return (best, f"title+creator ({best_sim:.0f})") if best else (None, "unmatched")
