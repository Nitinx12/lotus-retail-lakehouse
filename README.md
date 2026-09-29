# Lotus Retail Lakehouse

Local pipeline that lands the Lotus retail dataset from MongoDB into Bronze
parquet, cleans it into Silver with Type 2 versioning on customers and
employees, builds the Gold star schema, publishes it to Postgres, builds the
governed dbt marts on top, and records every run and quality result in a
Postgres ops schema. See ARCHITECTURE.md for the full design and AGENTS.md
for the working rules of this repo.

## Setup

```powershell
uv sync
Copy-Item .env.example .env
powershell -File scripts/docker_up.ps1 up -d
$env:PYTHONPATH = "."
uv run python scripts/init_ops.py
```

Gold writers (publish, SQL apply, dbt) connect with the pipeline role,
which owns the Gold and marts schemas. Dashboard, R, and the API read
through the pooler with the app role, which sees the masked customer
view but not the unmasked PII table. Set the pool user and password
(`POSTGRES_GOLD_POOL_USER`, `POSTGRES_GOLD_POOL_PASSWORD`) for local
reader runs.

Git hooks live in `.githooks` and are wired with
`git config core.hooksPath .githooks`, so lint and tests run before every
commit and push.

## Run the stages in order

```powershell
powershell -File scripts/run_ingest.ps1
powershell -File scripts/run_silver.ps1
powershell -File scripts/run_gold.ps1
powershell -File scripts/run_publish.ps1
powershell -File scripts/run_quality_gate.ps1
powershell -File scripts/run_report.ps1
```

Linux and CI use the matching shell scripts in the same folder, for example
`bash scripts/run_silver.sh`. Each stage writes its own log under `logs/`.
The ingest wrapper runs the pre ingest source check first, the publish
wrapper runs the Gold PL/pgSQL checks right after loading, and the quality
gate runs the pandas suites plus the Great Expectations checkpoints for
Bronze Silver and Gold.

## Semantic layer and dashboard

```powershell
$env:DBT_PROFILES_DIR = "./dbt"
uv run dbt run --project-dir dbt --target dev
uv run dbt test --project-dir dbt --target dev
uv run streamlit run dashboard/app.py
```

The ops monitoring page lives at `dashboard/pages/5_Ops.py` and reads only the
ops tables through the pooler. The R report needs R plus pandoc plus latexmk
on PATH and renders with `scripts/run_report.ps1`.

## Databricks

The workspace host lives in `.env` as `DATABRICKS_HOST`. The saved CLI
profiles only hold an expired refresh token, so refresh it when needed with
`databricks auth login`, then confirm with `databricks current-user me`.
Tokens never go into `.env`; staging and prod credentials resolve through
Airflow Connections and Databricks secret scopes.

## Tests

```powershell
uv run pytest tests/unit tests/smoke tests/dag tests/integration -q
uv run ruff check .
uv run ruff format --check src scripts tests dags dashboard
uv run sqlfluff lint sql/
```

## Layout

`src/` holds the pure transforms, `scripts/` the stage runners, `sql/` the ops
DDL plus the security roles grants masked view and PL/pgSQL checks, `dags/`
the Airflow control plane, `dbt/` the governed marts, `dashboard/` the retail
view plus the ops page, `r/` the analysis sources, `tests/` the unit smoke
DAG integrity and integration suites, `runbooks/` the restore procedure.
