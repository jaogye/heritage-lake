"""Turn the many ways museums write dates into a numeric year range.

Covers what actually shows up across Belgian heritage sources, in English,
Dutch and French: ISO timestamps from Wikidata, "ca. 1520-1530", "1520-30",
"1520s", "before 1600", "16th century", "16de eeuw", "XVIe siècle",
"late 15th century", "tweede helft 17de eeuw"...

Every result says whether it is approximate, so downstream code can tell a
documented date from a cataloguer's estimate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MIN_YEAR, MAX_YEAR = 500, 2100


@dataclass(frozen=True)
class DateRange:
    start: int
    end: int
    approx: bool

    def overlaps(self, other: DateRange) -> bool:
        return self.start <= other.end and other.start <= self.end

    @property
    def width(self) -> int:
        return self.end - self.start


APPROX = re.compile(
    r"\b(ca\.?|c\.|circa|around|about|omstreeks|rond|vers|environ|approx\.?)(?=\s|\d|$)|~"
)
BEFORE = re.compile(r"\b(before|vóór|voor|avant|ante)\s+(\d{3,4})")
AFTER = re.compile(r"\b(after|na|après|post)\s+(\d{3,4})")
ISO = re.compile(r"^[+-]?(\d{3,4})-\d{2}-\d{2}(t[\d:]+z?)?$")
RANGE = re.compile(r"(?<!\d)(\d{3,4})\s*[-/]\s*(\d{1,4})(?!\d)")
DECADE = re.compile(r"(?<!\d)(\d{3})0\s*'?s\b")
YEAR = re.compile(r"(?<!\d)(\d{3,4})(?!\d)")

ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
CENTURY_ARABIC = re.compile(
    r"(?<!\d)(\d{1,2})\s*(?:st|nd|rd|th|e|de|ste|ème|eme|er)?\.?\s*"
    r"(?:century|cent\.?|eeuw|siècle|siecle|s\.)"
)
CENTURY_ROMAN = re.compile(
    r"\b([ivxlc]+)\s*(?:e|ème|eme|th)?\.?\s*(?:siècle|siecle|s\.|century|eeuw)"
)

PART = [  # (pattern, fraction start, fraction end)
    (re.compile(r"first half|eerste helft|première moitié|premiere moitie|1st half"), 0.0, 0.5),
    (re.compile(r"second half|tweede helft|seconde moitié|seconde moitie|2nd half"), 0.5, 1.0),
    (re.compile(r"\b(early|begin|vroeg|début|debut)\b"), 0.0, 0.33),
    (re.compile(r"\b(mid|midden|milieu)\b"), 0.33, 0.67),
    (re.compile(r"\b(late|laat|eind|fin)\b"), 0.67, 1.0),
]


def _roman_to_int(s: str) -> int | None:
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN.get(ch)
        if v is None:
            return None
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total or None


def _valid(r: DateRange) -> DateRange | None:
    if MIN_YEAR <= r.start <= r.end <= MAX_YEAR:
        return r
    return None


def _century(n: int, text: str) -> DateRange:
    start, end = (n - 1) * 100, (n - 1) * 100 + 99
    for pattern, f0, f1 in PART:
        if pattern.search(text):
            return DateRange(start + round(100 * f0), start + round(100 * f1) - 1, True)
    return DateRange(start, end, True)


def parse_date(text: str | None) -> DateRange | None:
    if text is None:
        return None
    t = str(text).strip().lower().replace("–", "-").replace("—", "-")
    if not t:
        return None

    if m := ISO.match(t):  # Wikidata: "+1432-01-01T00:00:00Z" is year precision in practice
        y = int(m.group(1))
        return _valid(DateRange(y, y, False))

    approx = bool(APPROX.search(t))

    if m := BEFORE.search(t):
        y = int(m.group(2))
        return _valid(DateRange(y - 25, y, True))
    if m := AFTER.search(t):
        y = int(m.group(2))
        return _valid(DateRange(y, y + 25, True))

    if m := CENTURY_ARABIC.search(t):
        return _valid(_century(int(m.group(1)), t))
    if m := CENTURY_ROMAN.search(t):
        n = _roman_to_int(m.group(1))
        if n:
            return _valid(_century(n, t))

    if m := DECADE.search(t):
        d = int(m.group(1)) * 10
        return _valid(DateRange(d, d + 9, True))

    if m := RANGE.search(t):
        a, b = m.group(1), m.group(2)
        start = int(a)
        end = int(a[: len(a) - len(b)] + b) if len(b) < len(a) else int(b)  # "1520-30"
        if end >= start:
            return _valid(DateRange(start, end, approx))

    years = [int(y) for y in YEAR.findall(t)]
    if len(years) == 1:
        y = years[0]
        return _valid(DateRange(y - 5, y + 5, True) if approx else DateRange(y, y, False))
    if years:
        return _valid(DateRange(min(years), max(years), True))
    return None
