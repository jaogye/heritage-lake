"""Command-line entry point.

lake run --raw ../heritage-harvest/data/raw --inhouse catalogue.csv
lake run --raw data/sample/raw --inhouse data/sample/inhouse_catalogue.csv \\
         --decisions data/sample/review_decisions.csv                          # demo
lake sql "SELECT title, n_sources FROM gold ORDER BY n_sources DESC LIMIT 10"
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb
import typer

from .pipeline import QualityGateFailed, run

app = typer.Typer(add_completion=False, help="Clean, resolve and integrate heritage records.")
OUT = typer.Option(Path("data/lake"), help="Output directory")


@app.command("run")
def run_cmd(
    raw: Path = typer.Option(Path("data/sample/raw"), help="heritage-harvest raw zone"),
    inhouse: Path = typer.Option(None, help="In-house catalogue CSV"),
    decisions: Path = typer.Option(None, help="Curator review decisions CSV"),
    out: Path = OUT,
    allow_failures: bool = typer.Option(False, help="Write outputs even if the gate fails"),
    verbose: bool = typer.Option(False, "-v"),
) -> None:
    """Run the full pipeline."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    try:
        summary = run(raw, out, inhouse, decisions, fail_on_error=not allow_failures)
    except QualityGateFailed as exc:
        typer.secho(str(exc), fg="red")
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(summary, indent=2, default=str))


@app.command()
def sql(query: str, out: Path = OUT) -> None:
    """Query the lake with DuckDB SQL."""
    con = duckdb.connect(str(out / "lake.duckdb"), read_only=True)
    print(con.sql(query))


if __name__ == "__main__":
    app()
