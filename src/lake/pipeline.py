"""Bronze -> silver -> resolution -> gold -> quality gate, end to end.

Outputs (in `out_dir`):
  silver.parquet          one row per source record, common schema
  links.parquet           every scored candidate pair, with decision and reasons
  gold.parquet            one row per real-world object, with provenance
  review_queue.csv        borderline pairs for a curator (add a `verdict` column and feed
                          it back with --decisions to settle them for good)
  inhouse_matches.csv     how each in-house catalogue row was linked
  quality_report.json     quality-gate results
  lake.duckdb             all of the above as queryable tables
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from .bronze import latest_records, load_bronze
from .integrate import build_gold, load_inhouse
from .normalize import to_silver
from .quality import run_checks, summarize
from .resolve import load_curator_decisions, resolve

log = logging.getLogger(__name__)

STR, INT, BOOL = pl.String, pl.Int64, pl.Boolean
LIST = pl.List(pl.String)

SILVER_SCHEMA = {
    "record_key": STR,
    "source": STR,
    "source_id": STR,
    "url": STR,
    "title": STR,
    "title_lang": STR,
    "creators": LIST,
    "creator_roles": LIST,
    "creator_keys": LIST,
    "date_text": STR,
    "year_start": INT,
    "year_end": INT,
    "date_approx": BOOL,
    "object_type": STR,
    "materials": LIST,
    "subjects": LIST,
    "institution": STR,
    "institution_raw": STR,
    "institution_known": BOOL,
    "city": STR,
    "inventory_no": STR,
    "image_url": STR,
    "rights": STR,
    "description": STR,
    "wikidata_qid": STR,
}
GOLD_SCHEMA = {
    "entity_id": STR,
    "title": STR,
    "titles": LIST,
    "creators": LIST,
    "creator_roles": LIST,
    "creator_keys": LIST,
    "year_start": INT,
    "year_end": INT,
    "date_approx": BOOL,
    "date_text": STR,
    "object_type": STR,
    "materials": LIST,
    "subjects": LIST,
    "institution": STR,
    "city": STR,
    "inventory_no": STR,
    "image_url": STR,
    "rights": STR,
    "description": STR,
    "wikidata_qid": STR,
    "sources": LIST,
    "n_sources": INT,
    "source_records": LIST,
    "source_urls": LIST,
    "inhouse_id": STR,
    "themes": LIST,
    "research_notes": STR,
    "image_rights_cleared": BOOL,
    "flags": LIST,
    "provenance": STR,
}
LINK_SCHEMA = {"left": STR, "right": STR, "score": pl.Float64, "decision": STR, "reasons": LIST}


class QualityGateFailed(RuntimeError):
    pass


def _frame(rows: list[dict[str, Any]], schema: dict[str, Any]) -> pl.DataFrame:
    return pl.DataFrame([{k: r.get(k) for k in schema} for r in rows], schema=schema)


def run(
    raw_root: Path,
    out_dir: Path,
    inhouse_path: Path | None = None,
    decisions_path: Path | None = None,
    fail_on_error: bool = True,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "lake.duckdb"
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        bronze_stats = load_bronze(con, Path(raw_root))
        silver = to_silver(latest_records(con))
        curator = load_curator_decisions(decisions_path) if decisions_path else {}
        entity_of, links = resolve(silver, curator)
        inhouse = load_inhouse(inhouse_path) if inhouse_path else []
        gold, inhouse_report = build_gold(silver, entity_of, links, inhouse)
        report = summarize(run_checks(gold, {s.record_key for s in silver}))

        silver_rows = [s.to_dict() | {"entity_id": entity_of[s.record_key]} for s in silver]
        frames = {
            "silver": _frame(silver_rows, SILVER_SCHEMA | {"entity_id": STR}),
            "links": _frame([vars(lk) for lk in links], LINK_SCHEMA),
            "gold": _frame(gold, GOLD_SCHEMA),
        }
        for name, df in frames.items():
            df.write_parquet(out_dir / f"{name}.parquet")
            con.execute(
                f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_parquet(?)",
                [str(out_dir / f"{name}.parquet")],
            )

        review = frames["links"].filter(pl.col("decision") == "review")
        review.with_columns(pl.col("reasons").list.join(" | ")).write_csv(
            out_dir / "review_queue.csv"
        )
        pl.DataFrame(
            inhouse_report, schema={"catalogue_id": STR, "entity_id": STR, "match": STR}
        ).write_csv(out_dir / "inhouse_matches.csv")
        (out_dir / "quality_report.json").write_text(json.dumps(report, indent=2), "utf-8")
    finally:
        con.close()

    summary = {
        "bronze": bronze_stats,
        "silver_records": len(silver),
        "entities": len(gold),
        "multi_source_entities": sum(1 for g in gold if g["n_sources"] > 1),
        "links": {
            d: sum(1 for lk in links if lk.decision == d)
            for d in ("match", "review", "non-match", "blocked")
        },
        "inhouse": {
            m: sum(1 for r in inhouse_report if r["match"].startswith(m))
            for m in ("inventory", "title+creator", "unmatched")
        },
        "quality_passed": report["passed"],
    }
    log.info("pipeline summary: %s", summary)
    if fail_on_error and not report["passed"]:
        failed = [c["name"] for c in report["checks"] if c["severity"] == "error" and c["failed"]]
        raise QualityGateFailed(f"quality gate failed: {failed}")
    return summary
