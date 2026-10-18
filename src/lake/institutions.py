"""Map the many names of a holding institution to one canonical name.

Exact alias lookup first (after folding case and accents), then a fuzzy match
with a high threshold. Anything still unknown is passed through and reported,
so the alias table grows from real data instead of guesswork.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from importlib.resources import files

from rapidfuzz import fuzz, process

from .names import fold


def _norm(s: str) -> str:
    return " ".join(fold(s).replace("–", "-").replace("’", "'").split())


@lru_cache(maxsize=1)
def _table() -> tuple[dict[str, tuple[str, str]], list[str]]:
    lookup: dict[str, tuple[str, str]] = {}
    text = files("lake.reference").joinpath("institutions.csv").read_text("utf-8")
    for row in csv.DictReader(text.splitlines()):
        for alias in [row["canonical"], *row["aliases"].split("|")]:
            lookup[_norm(alias)] = (row["canonical"], row["city"])
    return lookup, list(lookup)


def resolve_institution(raw: str | None) -> tuple[str | None, str | None, bool]:
    """Return (canonical name, city, known?)."""
    if not raw or not raw.strip():
        return None, None, False
    lookup, choices = _table()
    key = _norm(raw)
    if key in lookup:
        return (*lookup[key], True)
    best = process.extractOne(key, choices, scorer=fuzz.token_sort_ratio, score_cutoff=90)
    if best:
        return (*lookup[best[0]], True)
    return raw.strip(), None, False
