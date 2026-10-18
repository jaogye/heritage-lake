"""Silver: map each source's raw payload onto one common schema.

One small mapper per source, all returning the same `SilverRecord`. Mappers
only translate structure; the shared parsers (dates, names, institutions) do
the interpretation, so a fix there improves every source at once.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .dates import parse_date
from .institutions import resolve_institution
from .names import parse_creator

TAG = re.compile(r"<[^>]+>")


@dataclass
class SilverRecord:
    record_key: str
    source: str
    source_id: str
    url: str | None
    title: str | None
    title_lang: str | None = None
    creators: list[str] = field(default_factory=list)
    creator_roles: list[str] = field(default_factory=list)
    creator_keys: list[str] = field(default_factory=list)
    date_text: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    date_approx: bool | None = None
    object_type: str | None = None
    materials: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    institution: str | None = None
    institution_raw: str | None = None
    institution_known: bool = False
    city: str | None = None
    inventory_no: str | None = None
    image_url: str | None = None
    rights: str | None = None
    description: str | None = None
    wikidata_qid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clean_text(s: Any) -> str | None:
    if s is None:
        return None
    if isinstance(s, list):
        s = next((x for x in s if x), None)
        if s is None:
            return None
    s = TAG.sub(" ", str(s))
    s = " ".join(s.split()).strip(" .;,")
    return s or None


def norm_inventory(s: str | None) -> str | None:
    """'inv. 0584', 'Inv.nr. 584', '584' -> '584'; '0000.GRO0208.I' kept as '0000.gro0208.i'."""
    if not s:
        return None
    s = str(s).strip().lower()
    s = re.sub(r"^(inv(entaris)?\.?\s*(nr|no|n°)?\.?\s*)", "", s).strip(" :#")
    if s.isdigit():
        s = s.lstrip("0") or "0"
    return s or None


def _apply_creators(rec: SilverRecord, raw_names: list[str]) -> None:
    for raw in raw_names:
        c = parse_creator(raw)
        if c is None:
            continue
        rec.creators.append(c.name or "anonymous")
        rec.creator_roles.append(c.role)
        if c.key and c.key not in rec.creator_keys:
            rec.creator_keys.append(c.key)


def _apply_date(rec: SilverRecord, text: str | None) -> None:
    rec.date_text = text
    d = parse_date(text)
    if d:
        rec.year_start, rec.year_end, rec.date_approx = d.start, d.end, d.approx


def _apply_institution(rec: SilverRecord, raw: str | None) -> None:
    rec.institution_raw = raw
    rec.institution, rec.city, rec.institution_known = resolve_institution(raw)


def _https(url: str | None) -> str | None:
    if not url:
        return None
    return "https://" + url[len("http://") :] if url.startswith("http://") else url


# ----------------------------------------------------------------- mappers
def map_wikidata(r: dict[str, Any]) -> SilverRecord:
    p = r["payload"]
    label = p.get("itemLabel")
    if label == p.get("qid"):
        label = None  # WDQS returns the QID when no label exists in any requested language
    rec = SilverRecord(
        record_key=f"wikidata:{r['source_id']}",
        source="wikidata",
        source_id=r["source_id"],
        url=r["url"],
        title=clean_text(label),
        title_lang="en",
        object_type=next((t["label"] for t in p.get("type", []) if t.get("label")), None),
        materials=[m["label"] for m in p.get("material", []) if m.get("label")],
        subjects=[d["label"] for d in p.get("depicts", []) if d.get("label")],
        inventory_no=norm_inventory(p.get("inventory")),
        image_url=_https(p.get("image")),
        rights="https://commons.wikimedia.org (see file page)" if p.get("image") else None,
        description=clean_text(p.get("itemDescription")),
        wikidata_qid=p.get("qid"),
    )
    _apply_creators(rec, [c["label"] for c in p.get("creator", []) if c.get("label")])
    _apply_date(rec, p.get("inception"))
    coll = next((c["label"] for c in p.get("collection", []) if c.get("label")), None)
    _apply_institution(rec, coll)
    return rec


def map_europeana(r: dict[str, Any]) -> SilverRecord:
    p = r["payload"]
    lang_titles = p.get("dcTitleLangAware") or {}
    lang = next(iter(lang_titles), None)
    rec = SilverRecord(
        record_key=f"europeana:{r['source_id']}",
        source="europeana",
        source_id=r["source_id"],
        url=r["url"],
        title=clean_text(p.get("title")),
        title_lang=lang,
        object_type=clean_text(p.get("dcType")),
        inventory_no=norm_inventory(clean_text(p.get("dcIdentifier"))),
        image_url=_https(clean_text(p.get("edmIsShownBy")) or clean_text(p.get("edmPreview"))),
        rights=clean_text(p.get("rights")),
        description=clean_text(p.get("dcDescription")),
    )
    _apply_creators(rec, p.get("dcCreator") or [])
    _apply_date(rec, clean_text(p.get("year")) or clean_text(p.get("dcDate")))
    _apply_institution(rec, clean_text(p.get("dataProvider")))
    return rec


def map_web(r: dict[str, Any]) -> SilverRecord:
    """schema.org VisualArtwork extracted by heritage-harvest's crawler."""
    p = r["payload"]
    creators = p.get("creator") or []
    if not isinstance(creators, list):
        creators = [creators]
    names = [c.get("name") if isinstance(c, dict) else c for c in creators]
    image = p.get("image")
    if isinstance(image, dict):
        image = image.get("url") or image.get("contentUrl")
    medium = clean_text(p.get("artMedium"))
    publisher = p.get("publisher")
    rec = SilverRecord(
        record_key=f"{r['source']}:{r['source_id']}",
        source=r["source"],
        source_id=r["source_id"],
        url=p.get("url") or r["url"],
        title=clean_text(p.get("name")),
        title_lang=p.get("inLanguage"),
        object_type=clean_text(p.get("artform")),
        materials=[medium] if medium else [],
        inventory_no=norm_inventory(p.get("identifier")),
        image_url=_https(image),
        rights=clean_text(p.get("license")),
        description=clean_text(p.get("description")),
    )
    _apply_creators(rec, [n for n in names if n])
    _apply_date(rec, clean_text(p.get("dateCreated")))
    _apply_institution(rec, publisher.get("name") if isinstance(publisher, dict) else publisher)
    return rec


MAPPERS = {"wikidata": map_wikidata, "europeana": map_europeana}


def to_silver(raw_records: list[dict[str, Any]]) -> list[SilverRecord]:
    return [MAPPERS.get(r["source"], map_web)(r) for r in raw_records]
