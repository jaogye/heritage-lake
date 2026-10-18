A new messy-data pattern was found in production: $ARGUMENTS

1. Decide which parser owns it: `dates.py`, `names.py`, `institutions.py`
   (alias table in `reference/institutions.csv`) or a source mapper in `normalize.py`.
2. Add the raw example and the expected output to the parametrised test for that parser.
   Run it and confirm it fails for the right reason.
3. Make the smallest change that makes it pass without breaking other cases.
4. Run `pytest -q` and the sample pipeline. If entity counts change, explain why.
5. If the pattern is common, add a representative record to `scripts/make_sample_data.py`.
