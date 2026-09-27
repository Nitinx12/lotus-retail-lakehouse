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
