"""Creator-name normalisation.

Catalogues write the same painter as "Bruegel, Pieter (I)", "Pieter Bruegel de
Oude", "P. Brueghel the Elder (1525/30-1569)" or "toegeschreven aan Pieter
Bruegel". We separate three things: the display name, the attribution role
(attributed / workshop / follower ...), and a matching key that survives
spelling variants.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

ROLE_PREFIXES = {
    "attributed to": "attributed",
    "toegeschreven aan": "attributed",
    "attribué à": "attributed",
    "attribue a": "attributed",
    "workshop of": "workshop",
    "atelier van": "workshop",
    "werkplaats van": "workshop",
    "atelier de": "workshop",
    "studio of": "workshop",
    "follower of": "follower",
    "navolger van": "follower",
    "suiveur de": "follower",
    "circle of": "circle",
    "kring van": "circle",
    "entourage de": "circle",
    "school of": "school",
    "school van": "school",
    "école de": "school",
    "copy after": "after",
    "after": "after",
    "naar": "after",
    "d'après": "after",
    "d'apres": "after",
}
ANONYMOUS = re.compile(r"\b(unknown|anonymous|anoniem|anonyme|onbekend|inconnu)\b")
ELDER = re.compile(r"\b(the elder|de oude|l'ancien|der ältere)\b|\(i\)")
YOUNGER = re.compile(r"\b(the younger|de jonge|le jeune|der jüngere)\b|\(ii\)")
LIFE_DATES = re.compile(r"\((?=[^)]*\d)[^)]*\)")
PARTICLES = {"van", "der", "den", "de", "von", "le", "la", "du", "di", "da", "ter", "ten"}


@dataclass(frozen=True)
class Creator:
    name: str | None  # display name, None for anonymous
    role: str  # author, attributed, workshop, follower, circle, school, after, anonymous
    key: str | None  # matching key, None for anonymous


def fold(s: str) -> str:
    """Lowercase ASCII without accents."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def surname_key(surname: str) -> str:
    """Collapse common spelling variation: Brueghel/Bruegel, Memlinc/Memlinck, Rysselberghe."""
    k = re.sub(r"[^a-z]", "", fold(surname))
    k = re.sub(r"(?<=[gt])h", "", k)
    k = re.sub(r"(.)\1+", r"\1", k)  # double letters
    return re.sub(r"ck$", "c", k)


def parse_creator(raw: str | None) -> Creator | None:
    if raw is None:
        return None
    s = " ".join(str(raw).split())
    if not s or s.startswith("http"):
        return None  # agent URIs carry no name; the label usually appears separately
    low = fold(s)

    role = "author"
    for prefix in sorted(ROLE_PREFIXES, key=len, reverse=True):
        if low.startswith(fold(prefix) + " "):
            role = ROLE_PREFIXES[prefix]
            s = s[len(prefix) :].strip()
            low = fold(s)
            break

    if ANONYMOUS.search(low):
        return Creator(None, "anonymous", None)

    generation = "the Elder" if ELDER.search(low) else "the Younger" if YOUNGER.search(low) else ""
    s = re.sub(
        r"(?i)\b(the elder|de oude|l'ancien|the younger|de jonge|le jeune)\b|\((i|ii)\)", "", s
    )
    s = LIFE_DATES.sub("", s)
    s = " ".join(s.replace(" ,", ",").split()).strip(" ,;")

    if "," in s:  # inverted "Bruegel, Pieter" -> "Pieter Bruegel"
        last, _, first = s.partition(",")
        s = f"{first.strip()} {last.strip()}".strip()

    tokens = s.split()
    if not tokens:
        return None
    core = [t for t in tokens if fold(t) not in PARTICLES] or tokens
    surname = core[-1]
    display = " ".join(tokens) + (f" {generation}" if generation else "")
    return Creator(display, role, surname_key(surname))


def keys_match(a: str, b: str, threshold: float = 85.0) -> bool:
    from rapidfuzz.fuzz import ratio

    return a == b or ratio(a, b) >= threshold
