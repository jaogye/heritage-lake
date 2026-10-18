"""End-to-end run on the committed sample data."""

import json
from pathlib import Path

import duckdb
import polars as pl
import pytest

from lake.pipeline import run

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


@pytest.fixture(scope="module")
def lake(tmp_path_factory):
    out = tmp_path_factory.mktemp("lake")
    summary = run(
        SAMPLE / "raw", out, SAMPLE / "inhouse_catalogue.csv", SAMPLE / "review_decisions.csv"
    )
    gold = pl.read_parquet(out / "gold.parquet")
    return out, summary, {r["entity_id"]: r for r in gold.to_dicts()}


def by_title(gold, title):
    return next(g for g in gold.values() if g["title"] == title)


def test_summary(lake):
    _, s, _ = lake
    assert s["bronze"] == {"files": 4, "versions": 45, "records": 44}
    assert s["quality_passed"]
    assert s["links"]["review"] == 1  # the Rubens pair nobody has looked at yet
    assert s["inhouse"] == {"inventory": 4, "title+creator": 3, "unmatched": 1}


def test_same_object_from_two_aggregators_and_wikidata_is_one_entity(lake):
    _, _, gold = lake
    angels = by_title(gold, "The Fall of the Rebel Angels")
    assert sorted(angels["source_records"]) == [
        "europeana:/2048128/BE_2",
        "europeana:/9200579/FR_2",
        "wikidata:Q9000002",
    ]
    assert "La Chute des anges rebelles" in angels["titles"]
    assert angels["inhouse_id"] == "IH-002"
    # the openly licensed image wins over the in-copyright one
    assert "publicdomain" in angels["rights"]


def test_provenance_points_to_winning_record(lake):
    _, _, gold = lake
    bosch = by_title(gold, "The Last Judgment")
    prov = json.loads(bosch["provenance"])
    assert prov["title"] == "wikidata:Q9000007"
    assert prov["creators"] == "musea_brugge:0000.GRO0208.I"  # museum's own attribution wins
    assert bosch["creators"] == ["Jheronimus Bosch"]


def test_curator_accept_merged_census(lake):
    _, _, gold = lake
    census = by_title(gold, "The Census at Bethlehem")
    assert census["n_sources"] == 2 and "pending-review" not in census["flags"]


def test_inhouse_only_and_unknown_institution_are_kept_and_flagged(lake):
    _, _, gold = lake
    lead = by_title(gold, "Unidentified altarpiece wing (research lead)")
    assert "inhouse-only" in lead["flags"]
    claus = by_title(gold, "Gezicht op de Leie")
    assert any(f.startswith("unknown-institution") for f in claus["flags"])


def test_latest_raw_version_is_used(lake):
    out, _, _ = lake
    con = duckdb.connect(str(out / "lake.duckdb"), read_only=True)
    desc = con.execute(
        "SELECT description FROM silver WHERE record_key = 'wikidata:Q9000003'"
    ).fetchone()[0]
    assert "probably a copy" in desc


def test_outputs_written(lake):
    out, _, _ = lake
    for f in [
        "silver.parquet",
        "links.parquet",
        "gold.parquet",
        "review_queue.csv",
        "inhouse_matches.csv",
        "quality_report.json",
        "lake.duckdb",
    ]:
        assert (out / f).exists(), f
