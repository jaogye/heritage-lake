"""Bronze: load heritage-harvest's raw JSONL zone into DuckDB.

The raw zone is append-only and may hold several versions of a record (one per
harvest in which it changed). Bronze keeps every version for audit and exposes
`bronze_latest`, the newest version per (source, source_id).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

COLUMNS = {
    "source": "VARCHAR",
    "source_id": "VARCHAR",
    "url": "VARCHAR",
    "fetched_at": "TIMESTAMPTZ",
    "payload": "JSON",
    "content_hash": "VARCHAR",
}


def load_bronze(con: duckdb.DuckDBPyConnection, raw_root: Path) -> dict[str, int]:
    files = sorted(str(p) for p in Path(raw_root).glob("*/*.jsonl"))
    if not files:
        raise FileNotFoundError(f"no raw JSONL files under {raw_root}")
    con.execute(
        "CREATE OR REPLACE TABLE bronze AS SELECT * FROM read_json(?, format='newline_delimited', "
        "columns=?, filename=true)",
        [files, COLUMNS],
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE bronze_latest AS
        SELECT * EXCLUDE (filename) FROM bronze
        QUALIFY row_number() OVER (PARTITION BY source, source_id ORDER BY fetched_at DESC) = 1
        """
    )
    total = con.execute("SELECT count(*) FROM bronze").fetchone()[0]
    latest = con.execute("SELECT count(*) FROM bronze_latest").fetchone()[0]
    return {"files": len(files), "versions": total, "records": latest}


def latest_records(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT source, source_id, url, CAST(fetched_at AS VARCHAR), payload FROM bronze_latest "
        "ORDER BY source, source_id"
    ).fetchall()
    return [
        {"source": s, "source_id": i, "url": u, "fetched_at": f, "payload": json.loads(p)}
        for s, i, u, f, p in rows
    ]
