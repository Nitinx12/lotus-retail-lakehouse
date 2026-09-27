# Restore runbook

Use this when Gold output is corrupt or when the ops database is lost. Run all
commands from the repo root with the local `.env` present.

## Gold table corrupted

Gold parquet is rebuilt from Silver, which is never edited in place. Confirm
which Gold table looks wrong, then rebuild only that stage.

```powershell
$env:PYTHONPATH = "."
uv run python scripts/run_gold.py
uv run python scripts/run_quality.py
```

Confirm row counts before and after with the run rows:

```sql
SELECT task_name, status, rows_in, rows_out, started_at
FROM ops.pipeline_runs
WHERE task_name LIKE 'gold\_%' ESCAPE '\'
ORDER BY started_at DESC LIMIT 20;
```

If Silver itself is suspect, rebuild it first, then rebuild the Type 2
versions from scratch by deleting the two versioned files and rerunning the
versioning step. This is safe because versioning is a pure function of the
cleaned Silver tables plus the anchor date taken from the earliest order.

```powershell
Remove-Item data/silver/dim_customers_scd2.parquet
Remove-Item data/silver/dim_employees_scd2.parquet
uv run python scripts/run_silver.py
uv run python scripts/run_scd2.py
uv run python scripts/run_gold.py
uv run python scripts/run_quality.py
```

Every output carries `_batch_id`, so verify that a single run id owns the
fresh files before handing Gold to consumers:

```powershell
uv run python -c "import pandas as pd; print(pd.read_parquet('data/gold/fact_orders.parquet')['_batch_id'].unique())"
```

## Ops database lost

`ops` holds `pipeline_runs`, `quality_results`, `extract_checkpoints`, and
`schema_changes`. Without it the pipeline still runs but blind, so restore it
first with point in time recovery to the latest restorable moment, then
recreate the schema objects and roles:

```powershell
$env:PYTHONPATH = "."
uv run python scripts/init_ops.py
```

Then confirm the monitors read fresh data:

```sql
SELECT COUNT(*) FROM ops.pipeline_runs;
SELECT suite_name, success_percent, checked_at
FROM ops.quality_results ORDER BY checked_at DESC LIMIT 5;
SELECT source_collection, rows_copied, updated_at
FROM ops.extract_checkpoints ORDER BY source_collection;
```

If the Gold Postgres database is also lost, reload it from the Gold parquet
files on disk after the ops database is back, then reapply the security
objects with `scripts/init_ops.py`, which grants the masked customer view to
general BI roles and restricts the unmasked table to the PII reader role.

```powershell
$env:PYTHONPATH = "."
uv run python scripts/run_publish.py
uv run python scripts/init_ops.py
```

## Ingestion blocked by stuck rows

The pre ingest source check fails when a previous run died without marking
its tasks terminal. Confirm nobody is still running that run id, then clear
only its stale running rows and rerun ingestion:

```sql
SELECT run_id, task_name, started_at
FROM ops.pipeline_runs
WHERE status = 'running'
ORDER BY started_at;

UPDATE ops.pipeline_runs
SET status = 'failed', ended_at = now(), error_message = 'cleared as stuck'
WHERE status = 'running';
```
