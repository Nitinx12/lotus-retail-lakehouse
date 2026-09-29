# 00 Recon: Lotus Retail Lakehouse

Branch: `audit/20260929`. Baseline: local `main` at `296a7f8` plus one uncommitted edit to `.dockerignore`. No history rewritten. `.env` exists locally and is gitignored, not tracked.

## 1. What this repo actually is

Pandas and parquet pipeline with Postgres serving, orchestrated by an Airflow DAG file and runnable through `main.py` stage map plus Make plus Windows batch. Spec describes Databricks plus PySpark plus Delta. Code implements pandas plus parquet. That gap shapes every phase below.

Stage map in `main.py`: `sql-ops`, `plpgsql-source`, `bronze`, `silver`, `scd2`, `gold`, `quality`, `sql-gold`, `publish`, `plpgsql-gold`. Group `all` runs those ten in that order. GX stages `gx-bronze`, `gx-silver`, `gx-gold` exist as separate entries but are not inside `all`.

## 2. Repo map against ARCHITECTURE.md Section 17

Present and matching: `dags/lotus_pipeline_dag.py`, `src/ingest` (as `src/bronze`), `src/silver` with `scd2.py`, `src/gold`, `src/quality`, `src/ops`, `dbt/models/marts` with three marts, `sql/ops_schema.sql`, `sql/plpgsql_checks`, `sql/security`, `dashboard/app.py`, `dashboard/pages`, `dotnet-api`, `runbooks/restore.md`, `tests/unit`, `tests/smoke`, `tests/dag`, `docker/docker-compose.yml`, `docker/Dockerfile.pipeline`, `docker/Dockerfile.dashboard`, `docker/Dockerfile.report`, `docker/Dockerfile.airflow`, `docker/entrypoint.sh`, `.env.example`, `ci.yml`.

Documented but missing or renamed:

* `scripts/run_all.sh` (named in Section 3 backfill discussion): absent. No equivalent single runner besides `main.py all`.
* `r/analysis.Rmd`: absent. Actual files are `r/analysis.qmd` plus `r/report.qmd`.
* `dbt/schema.yml` at project root: actual path is `dbt/models/schema.yml`.
* Section 17 layout omits `docker/Dockerfile.api` although the file exists and Section 16 points at a Section 16 layout that is really Section 17. Two doc bugs in one: wrong section number plus missing layout row.
* Section 17 shows `docker/postgres/init/` and `docker/mongo/init/` plus `mongo/seed.sh`. Actual paths are `docker/postgres/init/`, `docker/mongo/init/`, `docker/mongo/seed.sh`. Close enough, naming only.

Present but undocumented in Section 17:

* `main.py`, `Makefile`, `run_pipeline.bat`, `scripts/*.ps1` Windows twins of every stage, `scripts/run_bronze.py`, `scripts/run_publish.py`, `scripts/run_gx.py`, `scripts/run_plpgsql.py`, `scripts/run_scd2.py`, `scripts/run_sql.py`, `scripts/extract_to_mongo.py`, `scripts/init_ops.py`, `scripts/docker_up.*`
* `sql/functions`, `sql/procedures`, `sql/triggers`, `sql/index`, `sql/analysis`, `sql/apply_ops.sql`, `sql/apply_gold.sql`
* `dashboard/lib/`, `notebooks/` (four executed notebooks), `assets/`, `docs/`, `tests/integration/`, `tests/fixtures/`, `.githooks/`

## 3. Toolchain pinned versions

Local run reports Python 3.13.15. `pyproject.toml` requires Python `>=3.13` and every dependency is a lower bound only (`>=`). Real pins live in `uv.lock`: `dbt-core` 1.12.5, `dbt-postgres` 1.11.0, `great-expectations` 1.23.2, `streamlit` 1.64.0, `pandas` 3.0.6, `pyarrow` 25.0.1, `pymongo` 4.18.2, `pytest` 9.1.1, `ruff` 0.16.9, `sqlfluff` 4.3.0.

Not installed and not in `pyproject.toml`: `pyspark`, `delta-spark`, Mongo Spark connector, `apache-airflow` plus providers. Airflow image pins `2.10.5` with `databricks<8` and `postgres<6` provider caps. `dotnet` 8.0.425 present. `latexmk` present through TinyTeX. `docker` present. `Rscript` absent from PATH. `data/raw` seed CSV folder absent, so `mongo-seed` has nothing to load.

Verdict: unpinned direct deps in `pyproject.toml` (drift risk on every fresh `uv sync` without `--frozen`), plus Spark and Airflow exist only inside Docker images, not in local dev deps.

## 4. DAG dependency graph: code against spec Section 2

Code tasks: `plpgsql_source_checks`, `bronze`, `gx_bronze`, `silver`, `gx_silver`, `gold`, `gx_gold`, `jdbc_to_postgres`, `plpgsql_gold_checks`, `dbt`, `r_analysis`, `latex_report`, `streamlit_refresh`, `docker_build`, `push`. Fifteen tasks against fourteen spec boxes A1 to A14.

Ordering matches the spec with one addition: `plpgsql_gold_checks` sits between `jdbc_to_postgres` (A8) and `dbt` (A9). The spec diagram has A8 feed A9 directly and mentions PL/pgSQL loops only in prose. `dbt` fans out to `r_analysis` then `latex_report`, and separately to `streamlit_refresh`; both converge on `docker_build` then `push`. That matches A9 to A10 to A11 to A13 plus A9 to A12 to A13 plus A13 to A14.

Spec issues confirmed by reading:

* Mermaid node `A[Airflow SLA miss]` reuses prefix `A` used by `A1`..`A14`. Cosmetic doc fix.
* `PostgresOperator` import at `dags/lotus_pipeline_dag.py:15` while the Airflow image caps the Postgres provider below 6. Import resolves today but the operator is deprecated in that range in favor of `SQLExecuteQueryOperator`.
* `LOTUS_ENV` resolves at DAG parse time through `Variable.get` with env fallback (`dags/lotus_pipeline_dag.py:60`). Wrapped in try and except, so parse survives, but every scheduler parse still attempts a DB read.
* Schedule is bare `@daily` with naive `start_date` 2024-01-01, `catchup=False`, `max_active_runs=1`. No timezone anywhere, so the 7 AM IST SLA in Section 12 has no schedule anchor.
* SLA budgets per task sum well past 30 minutes end to end before any retry. Two retries with 5 minute exponential backoff on a slow task alone can exceed the 30 minute DAG level SLA. Target and timeouts disagree.
* Daily DAG ends in `docker_build` plus `push` that runs `docker push` plus `git push origin HEAD`. A scheduled data DAG pushing images and git on every green run is a deployment side effect inside orchestration.

## 5. Postgres ops schema at a glance

`sql/ops_schema.sql` defines `ops.pipeline_runs` keyed on `(run_id, task_name)`, `ops.quality_results` keyed on `(run_id, suite_name)`, `ops.extract_checkpoints` keyed on `source_collection`, `ops.schema_changes` with no key, plus an `ops.alerts` table the spec Section 12 never mentions. Retry attempts share one `(run_id, task_name)` row, so per attempt history is lost unless the extra trigger and procedure layer handles it. Index and trigger coverage lives outside this file and gets checked in Phase 2.

## 6. Environment blockers for Phase 3

* No local Airflow, Spark, Delta, Mongo connector. Local substitute is pandas plus parquet plus file checkpoints. Anything Databricks specific (`OPTIMIZE`, `ZORDER`, Unity Catalog, `MERGE INTO`) stays `UNVERIFIED` on real infra.
* `data/raw` CSVS absent, so a clean `mongo-seed` run cannot load the 42,877 rows until seed data is provided.
* Docker daemon presence not yet verified on this Windows host. Compose bring up is the first Phase 3 command.
* `.env` contains local only placeholder values. No secret values were read or copied into this report.
