# Monitoring

Every task writes run state to Postgres ops. Streamlit reads ops for history. Airflow callbacks push alerts for action.

```mermaid
graph TD
  TASKS[Airflow tasks<br>all stages] --> RUNS[(ops.pipeline_runs)]
  GX[GX plus dbt plus PLpgSQL] --> QUAL[(ops.quality_results)]
  BRZ[Bronze loader] --> SCH[(ops.schema_changes)]
  BRZ --> CHK[(ops.extract_checkpoints)]
  RUNS --> PAGE[Ops page<br>badges plus charts plus freshness]
  QUAL --> PAGE
  SCH --> PAGE
  RUNS --> ALERT[Slack plus PagerDuty]
  QUAL --> ALERT
  SCH --> ALERT
  SLA[Airflow SLA miss] --> ALERT

  style TASKS fill:#0277bd,stroke:#fff,stroke-width:2px,color:#fff
  style GX fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style BRZ fill:#cd7f32,stroke:#fff,stroke-width:2px,color:#fff
  style RUNS fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style QUAL fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style SCH fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style CHK fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style PAGE fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style ALERT fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
  style SLA fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
```

Ops page lives at `dashboard/pages/5_Ops.py` and shows only ops data.

```text
task status badges from ops.pipeline_runs
duration chart per task to spot slow stages
row count trend to spot silent drops
quality pass rate over time from ops.quality_results
schema change feed from ops.schema_changes
freshness banner red when Gold is older than SLA
```

Concrete SLAs measured on the page.

```text
Gold refreshed by 7 AM IST on scheduled run days
95 percent of DAG runs finish inside 30 minutes
No task retries more than twice before run marks failed
Quality suites stay above threshold or alert fires
Schema change insert always fires notice
```

Points to remember.

* 1. Page is for browsing history. Alerts are for waking up. Both read same ops rows.
* 2. Each task writes running on start and terminal state on finish with row counts.
* 3. All GX plus dbt results store pass percent plus failed count with timestamp.
* 4. Extract checkpoints store resume point so retry continues, not restarts.
* 5. Logs also land under `logs/` per stage for ops monitoring to tail.
