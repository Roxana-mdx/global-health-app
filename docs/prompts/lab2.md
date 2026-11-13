# Lab 2 – Prompts

Assistant used for all prompts below: Claude (Anthropic), in the Claude app with
code execution, model Claude Sonnet 5.5. I wrote my prompts in Romanian; they are
quoted exactly, with an English gloss where useful. Questions that only asked for
an explanation (for example where a piece of code came from) did not generate or
change code and are not listed.

Where the assistant had only the short code fragments printed in the lab PDF, the
code was written by the assistant following those fragments. The assistant did
not see the code in the teacher's repository. I ran every file myself and checked
it against the data (counts, SQL queries, the websites of the sources).

## Prompt 1 – plan and extractors/transforms for Lab 2
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-4
- Prompt: "phase 2" (with the Lab 2 PDF attached); later: "explain everything so that i can understand the lab"
- Result: `etl/json_types.py`, `etl/extract_worldbank.py`, `etl/transform_worldbank.py`, `etl/extract_ihme.py`, `etl/transform_ihme.py`. Commit "Lab 2: extractors and transforms (IHME, World Bank)". Git commit number: 628cb72
- Your changes: downloaded the files, moved the IHME CSV to `data/raw/ihme/`, ran the code; the list of 22 location names in `ISO3_EXCEPTIONS` is the assistant's, checked by running the transform: all 204 IHME locations were matched without errors.

## Prompt 2 – downloading the World Bank files
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09
- Prompt: "done with that. now i should do the world bank, right?"; then I pasted the IndentationError from the Python shell.
- Result: `download_worldbank.py` (helper script in the project root, not committed) that calls the extractors; the files in `data/raw/worldbank/` were downloaded.
- Your changes: ran the script instead of pasting code into the shell.

## Prompt 3 – exploration notebook (Task 2.1)
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09
- Prompt: "i've finished the download, now i'll continue with the notebook"
- Result: `notebooks/lab2_explore.ipynb`. Commit "Lab 2: exploration notebook (Task 2.1)". Git commit number: c8a6125
- Your changes: ran all cells with the `.venv` kernel and completed the "Notes" cell in my own words.

## Prompt 4 – cleaning rules (section 2.3)
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09
- Prompt: "the notebook is uploaded" after the notebook commit; the assistant then wrote `clean.py`. Follow-up with the numbers I got: "INFO etl.clean: dropped 6664 observation rows: not a valid country code ..."
- Result: `etl/clean.py`, the `Sex` enum in `app/models.py`. Commit "Lab 2: cleaning rules (clean.py) and Sex enum". Git commit number: 941b3fa
- Your changes: added the `Sex` enum to `models.py`; checked the cleaning on my data in the notebook; decided with the assistant to exclude 4 IHME locations without a World Bank counterpart (Taiwan, Tokelau, Cook Islands, Niue) and to keep the study window 1990–2023. The plausible bounds for the 13 indicators were proposed by the assistant.

## Prompt 5 – IQR outlier flag and Alembic migration (Task 2.2)
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09
- Prompt: "finished the uploading" (after the cleaning commit); later I pasted the output of `alembic init alembic`.
- Result: `_flag_outliers()` in `etl/clean.py`; `alembic/env.py` (reads `DATABASE_URL` from `.env`); migrations `edf3ac493aaf_baseline.py` (empty) and `bfc6908434a7_add_is_outlier_to_observations.py`; `is_outlier` in `app/models.py`. Commit "Lab 2: is outlier column with Alembic migration, IQR flag in clean.py". Git commit number: 78bc717
- Your changes: installed Alembic, ran `alembic init`, `alembic stamp head` and `alembic upgrade head`, added `alembic` to `requirements.txt`, updated `db/schema.sql`.

## Prompt 6 – loader and import scripts (section 2.4)
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09
- Prompt: I pasted my `app/models.py` (requested by the assistant) and the results of the queries on `source`, `indicator` and `observation`.
- Result: `etl/load.py`, `etl/import_worldbank.py`, `etl/import_ihme.py`. Commit "Lab 2: observation loader and per-source import scripts". Git commit number: 8e5173e
- Your changes: set `SOURCE_NAME = "World Bank Indicators API"` to match the existing `source` row; before the first import I ran `DELETE` statements in pgAdmin (4,727 rows with NULL values, 1,224 rows and 4 countries of the excluded territories); ran each import twice (Task 2.3).

## Prompt 7 – quality checks and results document (Tasks 2.3, 2.4)
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-09 and 2026-11-13
- Prompt: results of the idempotency test and of the seven SQL checks (screenshots); screenshots of the World Bank and GBD Results pages.
- Result: `docs/lab2_results.md` (the assistant drafted it from my results). Git commit number: 5680970
- Your changes: ran all queries myself; compared the three values (Romania, 2019) with data.worldbank.org and the GBD Results tool and filled in the comparison table.

## Prompt 8 – README
- Tool and model: Claude, Claude Sonnet 5.5
- Date: 2026-11-13
- Prompt: I pasted my current `README.md` and the content of `requirements.txt`.
- Result: updated `README.md`; `alembic` added to `requirements.txt`. Commit "Lab 2: README with setup, extraction and import instructions; add alembic to requirements". Git commit number: d4244d7
- Your changes: removed `etl/load_ihme.py` and `etl/load_worldbank.py` from Lab 1 (replaced by the import scripts).
