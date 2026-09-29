# 02 Execution log

Labels: `PASS`, `FAIL`, `SKIPPED (reason)`, `UNVERIFIED (reason)`. Times in UTC, 2026-09-29. Backups taken before any write: pg dump `lotus_pre_audit.dump` (1,206,065 bytes, custom format, full local DB) plus a full copy of `data/` (3,236,908 bytes). Baseline git state: branch `audit/20260929` off `main` at `296a7f8`, one pre existing uncommitted edit (`.dockerignore` plus one ignore line).

Environment note: the shared temp dir holds other agents' helper files, including an `inspect.py` that shadows the standard library when scripts run from that directory. All helper scripts were moved to a clean `lotus_audit` subdirectory before use. Nothing in the repo was touched by this.

## 4.1 Bring up

`docker info --format ...` shows server 29.7.2 on linux. Result `PASS`.

`powershell -File scripts/docker_up.ps1 up -d postgres mongo pgbouncer` brings three containers to healthy. The stack was already up from earlier work. Result `PASS`.

Mongo row counts through the root account inside the container (values only, no secrets shown):

* `fact_returns:1056`, `dim_employees:216`, `dim_customers:3050`, `dim_products:345`, `dim_date:1096`, `fact_orders_2022_2023:7942`, `fact_orders_2024:4058`, `dim_stores:15`, `fact_order_details:25099`.
* Total 42,877, matching the spec number exactly. Result `PASS`.

Postgres init check through the superuser account: schemas `gold`, `marts`, `ops` present; 8 gold tables, 3 marts tables, 5 ops tables; all 8 expected roles present (`airflow_meta`, `lotus_api_reader`, `lotus_app`, `lotus_bi`, `lotus_ops`, `lotus_pii_reader`, `lotus_pipeline`, `pii_reader`). Result `PASS`.

## 4.2 Run order

Unit plus smoke plus DAG integrity: `uv run pytest tests/unit tests/smoke tests/dag -q` gives `61 passed, 1 skipped in 22.61s`. The skip is `tests/dag/test_dag.py:141`, reason `could not import airflow`. Result `PASS` with one skip.

Integration: `uv run pytest tests/integration -q` gives `3 passed`. Result `PASS`.

A1 source checks: `uv run python main.py plpgsql-source` ends `plpgsql done suite=source`. Result `PASS`.

A2 bronze: `uv run python main.py bronze` ends `bronze done total=42877`. Every collection skipped on equal row counts. Result `PASS`.

A3 GX bronze: `uv run python main.py gx-bronze` ends `gx done suite=bronze ... failed=0`. Result `PASS`.

A4 silver: `uv run python main.py silver` ends `silver done in=42877 out=42827`. Customers 3050 to 3000, orders 7942 plus 4058 to 12000. Result `PASS`.

SCD2: `uv run python main.py scd2` ends `anchor=2022-01-01`, customers rows 3000 with 0 closed, employees 216 with 0 closed. Rerun later also gives 0 closed. Result `PASS`, rerun stable.

A5 GX silver: `gx done suite=silver ... failed=0`. Result `PASS`.

A6 gold: all dims plus facts plus three marts built (revenue mart 540 rows, return rate 345, Ramadan 42). Result `PASS`.

A7 GX gold: `failed=0`. Result `PASS`.

Pandas quality: `quality done ... blocked=False`, all suites 100.0. Result `PASS`.

sql gold as default local role: `uv run python main.py sql-gold` raises `psycopg2.errors.InsufficientPrivilege: must be owner of table fact_orders` on `CREATE INDEX idx_fact_orders_order_date`. Result `FAIL`, evidence kept in `05` fix plan input. Rerun with the pipeline role override (same override the compose pipeline service uses) ends `sql done db=gold`. Result `PASS (with role override)`.

A8 publish as default local role: `uv run python main.py publish` raises `permission denied for database lotus_gold_dev` at `run_publish.py:86` (`CREATE SCHEMA IF NOT EXISTS gold`). Result `FAIL`. Rerun as the pipeline role publishes all 8 tables, total 42827. Result `PASS (with role override)`.

plpgsql gold: `plpgsql done suite=gold`. Result `PASS`.

A9 dbt as default local role: `dbt run --target dev` gives `permission denied for schema marts` on all 3 models. Result `FAIL`. Rerun as the pipeline role: `PASS=3`, then `dbt test` gives `PASS=12`. Result `PASS (with role override)`.

A10 R: `quarto render r/report.qmd --to pdf` ends `Output created: report.pdf` (219,303 bytes, written to `r/report.pdf`). R itself is found by quarto through the registry although `Rscript` is not on PATH. Result `PASS` with a PATH note. Whether the numbers rendered are live or demo fallback was not confirmed from the render log, recorded as a check for Phase 4.

A11 LaTeX: `latexmk -pdf -outdir=reports reports/report.tex` ends `All targets up-to-date`. Result `PASS`.

A12 Streamlit: the compose dashboard answers `http://127.0.0.1:8501/_stcore/health` with 200 `ok`. Result `PASS`.

A13 Docker builds, all build only, no push:

* `Dockerfile.pipeline --target test` builds, but `docker run --rm lotus-pipeline:ci` ends `4 errors during collection`, all `ModuleNotFoundError: No module named 'scripts'` or `'dashboard'`. The test stage copies only `src`, `main.py`, `tests`. Result `FAIL`.
* `Dockerfile.dashboard`, `Dockerfile.report` (3.17 GB), `Dockerfile.api` (335 MB), `Dockerfile.airflow` (2.8 GB) all build. Result `PASS`.

A12 detail: the ops page import path was also covered by `tests/unit/test_dashboard.py` inside the 61 passed.

A14 push: not attempted, would hit real registries. Result `UNVERIFIED (would push to real registries)`.

Airflow task level: `airflow tasks test` and `airflow dags test` need a scheduler, not installed locally. Substitute: the DAG module imports cleanly under stubbed airflow modules (15 edges resolve, `LOTUS_ENV` defaults to dev, the notify callback runs). Result `UNVERIFIED (no Airflow runtime here)`, stub import `PASS`.

`dotnet test dotnet-api/LotusApi.sln` gives `Passed: 2, Failed: 0`. Result `PASS`.

Lint parity: `ruff check .` passes, `ruff format --check` passes on 52 files, `sqlfluff lint sql/` finishes with no violations. Result `PASS`.

## 4.3 Behavior tests

Idempotency: two consecutive full runs give identical row counts on every table. Full content hashes differ on every silver and gold file because `_batch_id` carries the new run id. Recomputed with batch columns excluded: run 2 and run 3 are byte identical on all 19 files. Verdict: business content idempotent, run tagging explains the diff. Evidence files kept outside the repo.

Retry safety, missing file: deleting `data/bronze/dim_stores.parquet` and rerunning bronze triggers a reload of that collection (`needs_reload` checks file presence, `run_bronze.py:86`), file restored, then the kept copy was put back. Partial file loss recovers. Mid collection resume does not exist (full re read), and `last_object_id` is write only.

Retry safety, counts: bronze skips on equal counts only, so a content change with equal counts would be missed. Verified by code path, not triggered live against the shared source.

SCD2 scenario: controlled region change on customer `CUS01518` closes 1 row (`effective_end_date 2024-06-15`, `is_current false`) and opens 1 row (sk 3001, current true). Exactly one current row for the victim. Point in time join over 12,000 facts returns 12,000 rows, 0 duplicated order ids, 0 null surrogate keys. Rerun with no change adds 0 rows. Result `PASS` on the happy path.

Schema evolution: live injection blocked, `pymongo.errors.OperationFailure: not authorized`, because the local Mongo URI uses the read only reader role. Source left untouched, bronze rerun still skips at 42,877. Live detection path stays `UNVERIFIED (read only source role, by design)`. By code reading, a same count schema drift would not trigger a reload, so the new column logger would never fire.

DQ injection: inserting a future dated order and a negative return as superuser is blocked at insert time by the guard triggers (`future order_date 2026-09-30 rejected`, `negative return_amount rejected for return bad`). `plpgsql-gold` passes on the clean data set. Result `PASS`.

Reconciliation: gold `fact_orders` holds 12,000 rows and revenue 45,350,979.0; dbt `revenue_by_store_month` holds 540 rows and revenue 45,350,979.0, exact match. Returns 1,056 on both sides. Return mart 345 rows, Ramadan mart 42 rows. Result `PASS`.

Referential integrity: 0 dangling customer keys, 0 null customer keys in published orders, 0 returns without an order. Result `PASS`.

Security: `lotus_app` selects the unmasked `gold.dim_customers` successfully (finding confirmed live) and the masked view as well. `lotus_api_reader` cannot create tables and cannot select unmasked customers. Result: app over privileged `CONFIRMED`, API reader correctly restricted `PASS`.

Failure paths: the two publish failures and the sql apply failure each wrote a `failed` row with error text to `ops.pipeline_runs`, and each produced a `critical` alert row in `ops.alerts` through the trigger path. Alert routing to Slack or PagerDuty itself stays `UNVERIFIED (stubbed webhook, no secret configured)`.

Timing: every task finished in seconds locally (bronze about 3 s, silver about 2 s, gold about 3 s, publish about 19 s, dbt run 11 s, dbt test 14 s). End to end manual run stays far under 30 minutes on this data size. Caveat: `ops.pipeline_runs` durations are unusable, `ended_at` equals `started_at` to the microsecond on success rows and stays NULL on failed rows, because all ops writes share one transaction per stage and `now()` is frozen. Recorded as a monitoring finding.
