# Project conventions for coding assistants

## What this repo is
Stage 2 of the heritage pipeline. Input: heritage-harvest's raw JSONL zone. Output:
`gold.parquet`, one row per real-world object, consumed by heritage-atlas. The gold
schema is `GOLD_SCHEMA` in `src/lake/pipeline.py`; changing it is a breaking change for
heritage-atlas.

## Rules
- Mappers in `normalize.py` only translate structure. Interpretation lives in `dates.py`,
  `names.py`, `institutions.py` so one fix helps every source.
- Every value in gold must be traceable: if you add a gold field, add it to `provenance`.
- Never silently drop records. Unknown institutions, unparseable dates and in-house rows
  without a match are kept and flagged.
- Resolution weights in `resolve.py` are documented decisions. If you change a weight, add
  a test showing the case that motivated it.
- New messy-data patterns go into the parametrised tests first (`tests/test_dates.py`,
  `tests/test_names.py`), then into the parser.
- Do not edit files under `data/sample/` by hand: change `scripts/make_sample_data.py` and
  regenerate, so the sample stays reproducible.

## Commands
- `pytest -q` – unit tests plus the end-to-end run on the sample
- `ruff check . && ruff format --check .`
- `lake run --inhouse data/sample/inhouse_catalogue.csv --decisions data/sample/review_decisions.csv`

## Before finishing a task
Run the tests and the sample pipeline, compare the summary counts with the ones in
README, and call out any change in entity counts in your summary.
