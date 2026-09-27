# Lotus Retail Lakehouse

Local pipeline that lands the Lotus retail dataset from MongoDB into Bronze
parquet, cleans it into Silver with Type 2 versioning on customers and
employees, builds the Gold star schema plus three marts, and records every run
and quality result in a Postgres ops schema. See ARCHITECTURE.md for the full
design and AGENTS.md for the working rules of this repo.

## Setup

```powershell
uv sync
Copy-Item .env.example .env
docker compose up -d
$env:PYTHONPATH = "."
uv run python scripts/init_ops.py
```

## Run the stages in order

```powershell
powershell -File scripts/run_ingest.ps1
powershell -File scripts/run_silver.ps1
powershell -File scripts/run_gold.ps1
powershell -File scripts/run_quality_gate.ps1
```

Linux and CI use the matching shell scripts in the same folder, for example
`bash scripts/run_silver.sh`. Each stage writes its own log under `logs/`.

## Tests

```powershell
uv run pytest tests/unit tests/smoke tests/dag -q
uv run ruff check .
uv run ruff format --check src scripts tests
```

## Layout

`src/` holds the pure transforms, `scripts/` the stage runners, `sql/` the ops
DDL plus the security roles grants and masked view, `tests/` the unit smoke
and DAG integrity suites, `runbooks/` the restore procedure.
