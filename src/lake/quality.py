"""Quality gate: checks that must pass before gold is published.

Errors stop the pipeline; warnings are reported but let it continue. The
report is written next to the data so every published dataset carries its own
quality evidence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

CURRENT_YEAR = 2026


@dataclass
class Check:
    name: str
    severity: str  # "error" | "warning"
    failed: int
    examples: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def _check(name: str, severity: str, rows: list[dict], bad) -> Check:
    failing = [r["entity_id"] for r in rows if bad(r)]
    return Check(name, severity, len(failing), failing[:5])


def run_checks(gold: list[dict[str, Any]], silver_keys: set[str]) -> list[Check]:
    ids = Counter(r["entity_id"] for r in gold)
    covered = Counter(k for r in gold for k in r["source_records"])
    checks = [
        Check(
            "entity_id unique",
            "error",
            sum(c - 1 for c in ids.values() if c > 1),
            [k for k, c in ids.items() if c > 1][:5],
        ),
        Check(
            "every silver record in exactly one entity",
            "error",
            len(silver_keys ^ set(covered)) + sum(1 for c in covered.values() if c > 1),
            sorted(silver_keys ^ set(covered))[:5],
        ),
        _check("title present", "error", gold, lambda r: not r["title"]),
        _check(
            "year range ordered",
            "error",
            gold,
            lambda r: r["year_start"] is not None and r["year_start"] > r["year_end"],
        ),
        _check(
            "year not in the future",
            "error",
            gold,
            lambda r: r["year_end"] is not None and r["year_end"] > CURRENT_YEAR,
        ),
        _check(
            "image url is https",
            "error",
            gold,
            lambda r: r["image_url"] is not None and not r["image_url"].startswith("https://"),
        ),
        _check(
            "at most one Wikidata QID per entity",
            "error",
            gold,
            lambda r: isinstance(r["wikidata_qid"], list),
        ),
        _check(
            "institution known",
            "warning",
            gold,
            lambda r: any(f.startswith("unknown-institution") for f in r["flags"]),
        ),
        _check(
            "dates agree across sources", "warning", gold, lambda r: "date-conflict" in r["flags"]
        ),
        _check("has an image", "warning", gold, lambda r: "no-image" in r["flags"]),
        _check(
            "no pending curator review", "warning", gold, lambda r: "pending-review" in r["flags"]
        ),
    ]
    return checks


def summarize(checks: list[Check]) -> dict[str, Any]:
    return {
        "passed": all(c.ok for c in checks if c.severity == "error"),
        "checks": [
            {"name": c.name, "severity": c.severity, "failed": c.failed, "examples": c.examples}
            for c in checks
        ],
    }
