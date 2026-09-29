# Environments

One codebase. Three targets. Airflow Variable selects target. Code never branches on hardcoded names.

```mermaid
graph TD
  CODE[Same DAG plus same src] --> VAR{LOTUS_ENV}
  VAR --> DEV[dev<br>sampled data]
  VAR --> STG[staging<br>full data no consumers]
  VAR --> PRD[prod<br>full data live consumers]
  DEV --> PROM1[Validate fix]
  PROM1 --> STG
  STG --> PROM2[Full run plus dbt test]
  PROM2 --> PRD

  style CODE fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style VAR fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style DEV fill:#0277bd,stroke:#fff,stroke-width:2px,color:#fff
  style STG fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style PRD fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style PROM1 fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
  style PROM2 fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
```

What changes per target.

```text
catalog : dev_lotus versus staging_lotus versus prod_lotus
gold db : lotus_gold_dev versus lotus_gold_staging versus lotus_gold_prod
ops db  : matching ops db per target, same 5 tables
conns   : postgres_ops_dev versus staging versus prod, same for gold plus databricks
api env : ASPNETCORE_ENVIRONMENT mirrors LOTUS_ENV for connection choice
```

Local bootstrap uses `.env` only for sandbox values.

```bash
Copy-Item .env.example .env
uv sync
powershell -File scripts/docker_up.ps1 up -d
uv run python scripts/init_ops.py
```

Points to remember.

* 1. Validate Silver change in dev on small data first.
* 2. Promote to staging for full data run with no downstream readers pointed at it.
* 3. Promote to prod only after staging run plus dbt test are green.
* 4. Staging and prod secrets come from Vault or cloud manager, never from `.env`.
* 5. Backfill by date range in Airflow, never by manual rerun of full pipeline.
