# Changelog

## Unreleased

* Fix customer Type 2 tracking to hash region and loyalty tier only, so a city
  move no longer mints a spurious version. Rebuild the Silver SCD tables after
  pulling this change because hashes from the old three column set never match
  the new two column set.
* Fix point in time joins to keep facts that have no active dimension version,
  with a null surrogate key, instead of dropping the fact row silently.
* Fix the Gold employee check to compare against all employee versions, so
  history rows no longer count as orphans once versioning starts.
* Fix gender cleaning to preserve unknown values for quality review instead of
  mapping them to null.
* Fix customer cleaning to drop rows with a null natural key.
* Flag returns that have no matching order detail with `return_orphan`
  instead of leaving them indistinguishable from matched rows.
* Stamp `_batch_id` with the producing run id on every Bronze Silver and Gold
  table.
* Bronze now resumes from `ops.extract_checkpoints` and skips collections
  whose row count is unchanged, and schema changes are logged only when a
  previous load exists to compare against.
* Every task writes a running row on start and a terminal row on completion,
  including failures with the error text.
* Add shell stage scripts with per stage logs, plus matching PowerShell
  scripts for Windows runs.
* Add Postgres security objects: least privilege roles, grants, and the
  masked customer view. `scripts/init_ops.py` applies them.
* Add smoke tests, a DAG integrity placeholder, `docker-compose.yml`,
  `Dockerfile.pipeline`, and the CI workflow.
* Remove the empty `main.py`, the empty dashboard requirements file, and the
  duplicate `env.example`.
* Add the Airflow control plane in `dags/` with retries, SLAs, failure alerts,
  and environment mapping, plus structural integrity tests that run without a
  scheduler installed.
* Publish Gold parquet to Postgres with per table transactions, and record
  publish rows in ops.
* Add PL/pgSQL source and Gold checks with a runner that records results in
  ops and blocks on violations.
* Add the dbt project with three marts and column plus relationship plus
  reconciliation tests, verified row for row against the pipeline marts.
* Add Great Expectations checkpoints for Bronze Silver and Gold that record
  into ops and block on failure.
* Add the Streamlit retail view and the pipeline ops page with the 7am IST
  freshness banner, reading through the pooler.
* Add the R analysis with PDF report build through latexmk.
* Strip mongo extract metadata before Silver, and drop serving remnants from
  Gold builders.
* Commit failure rows explicitly so crashed stages always leave a failed row,
  and clear the connection error state before recording.
* Wire the repo git hooks so lint and tests run on every commit and push.
* Add unified pipeline entrypoints through main dot py plus Makefile targets plus Windows batch runner so local Unix Docker and Windows runs share one stage map.
* Add pipeline and dashboard services to compose plus main dot py in the pipeline image so the full chain can run containerized.
* Add CI entrypoints job covering main dot py plus Make dry run plus batch file presence plus compose config plus concurrency cancel.
