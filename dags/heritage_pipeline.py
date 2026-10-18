"""Weekly heritage pipeline: harvest -> lake -> atlas, as an Airflow DAG.

Each stage is a CLI call so the same commands run locally, in CI and here.
Harvest tasks run in parallel per source; the lake waits for all of them; the
quality gate's non-zero exit stops the atlas from embedding a bad dataset.

Requires: pip install "heritage-lake[airflow]" heritage-harvest heritage-atlas
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DATA = "/opt/heritage/data"
default_args = {"retries": 2, "retry_delay": timedelta(minutes=10), "owner": "data"}

with DAG(
    dag_id="heritage_pipeline",
    start_date=datetime(2026, 9, 1),
    schedule="0 3 * * 1",  # Mondays 03:00, after weekend Wikidata edits settle
    catchup=False,
    default_args=default_args,
    tags=["heritage"],
) as dag:
    harvest = [
        BashOperator(
            task_id=f"harvest_{name}",
            bash_command=f"harvest {cmd} --out {DATA}/raw --cache {DATA}/.cache/http",
            pool="external_apis",
        )
        for name, cmd in [
            ("wikidata", "wikidata"),
            ("europeana", "europeana"),
            (
                "musea_brugge",
                "crawl https://collectie.museabrugge.be/ --detail '/object/' "
                "--follow '[?&]page=' --name musea_brugge --delay 3",
            ),
        ]
    ]

    lake = BashOperator(
        task_id="lake_run",
        bash_command=(
            f"lake run --raw {DATA}/raw --out {DATA}/lake "
            f"--inhouse {DATA}/inhouse/catalogue.csv --decisions {DATA}/inhouse/review_decisions.csv"
        ),
    )

    atlas = BashOperator(
        task_id="atlas_build",
        bash_command=f"atlas build --gold {DATA}/lake/gold.parquet --out {DATA}/atlas",
    )

    harvest >> lake >> atlas
