# Deployment

Pipeline ships as images. Compose runs local stack. CI builds on PR. Main promotes through staging to prod.

```mermaid
graph TD
  PR[PR open] --> CI[GitHub CI<br>pytest plus dbt plus lint plus build]
  CI --> MERGE[Merge to main]
  MERGE --> STG[Deploy staging<br>full run]
  STG --> GATE{Staging green}
  GATE --> PRD[Promote prod<br>gated]
  GATE --> FIX[Fix plus new PR]
  PRD --> OBS[Ops page plus alerts<br>watch freshness]

  style PR fill:#0277bd,stroke:#fff,stroke-width:2px,color:#fff
  style CI fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style MERGE fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style STG fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style GATE fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
  style PRD fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style FIX fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
  style OBS fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
```

Local stack from compose.

```text
postgres  : Gold plus ops, seeded roles plus ops schema on first start
mongo     : raw landing, seeded from data/raw by mongo-seed
pgbouncer : pooler for app traffic on 6432
pipeline  : one shot run of main.py all with pipeline role
dashboard : Streamlit on 8501 with app role through pooler
report    : R plus LaTeX build to reports/
airflow   : standalone on 8081 with DAG plus scripts mounted
```

Images built from docker folder.

```text
Dockerfile.pipeline  : python plus deps plus src plus scripts
Dockerfile.dashboard : Streamlit app plus pooled engine
Dockerfile.report    : R plus pandoc plus latexmk
Dockerfile.airflow   : scheduler plus DAG plus providers
Dockerfile.api       : ASP.NET Core read only API
```

Bring up and run locally.

```bash
powershell -File scripts/docker_up.ps1 up -d
powershell -File scripts/run_ingest.ps1
powershell -File scripts/run_silver.ps1
powershell -File scripts/run_gold.ps1
powershell -File scripts/run_publish.ps1
powershell -File scripts/run_quality_gate.ps1
powershell -File scripts/run_report.ps1
```

Points to remember.

* 1. Use one branch per task with names like `feature/short name`. Never commit straight to main.
* 2. Rebase onto main before PR. Keep history linear. Squash merge then delete branch.
* 3. Update CHANGELOG only when behavior changes, not on every commit.
* 4. Prod promote is gated on green staging run plus green dbt test.
* 5. Restore path lives in `runbooks/restore.md` for corrupt Gold or lost ops.
