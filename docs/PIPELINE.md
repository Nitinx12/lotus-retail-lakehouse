# Pipeline

Lotus Retail Lakehouse moves retail data from Mongo landing to governed marts in Postgres. Airflow owns order, retries and SLAs. Databricks owns compute. Postgres owns serving and ops history.

```mermaid
graph TD
  MONGO[(Mongo lotus_retail<br>9 collections)] --> SRCCHK[Source checks<br>PLpgSQL]
  SRCCHK --> BRONZE[Bronze<br>PySpark Delta]
  BRONZE --> GXB[Great Expectations<br>Bronze suite]
  GXB --> SILVER[Silver<br>clean plus SCD2]
  SILVER --> GXS[Great Expectations<br>Silver suite]
  GXS --> GOLD[Gold<br>star schema]
  GOLD --> GXG[Great Expectations<br>Gold suite]
  GXG --> PG[(Postgres Gold<br>star plus marts)]
  PG --> GOLDCHK[Gold checks<br>PLpgSQL]
  GOLDCHK --> DBT[dbt run plus test]
  DBT --> R[R analysis]
  DBT --> APP[Streamlit refresh]
  R --> PDF[LaTeX PDF]
  PDF --> IMG[Docker build]
  APP --> IMG
  IMG --> PUSH[Push to registry]
  BRONZE -. log .-> OPS[(Postgres ops)]
  SILVER -. log .-> OPS
  GOLD -. log .-> OPS
  GXB -. results .-> OPS
  GXS -. results .-> OPS
  GXG -. results .-> OPS
  OPS --> OPSPAGE[Ops page]
  OPS --> ALERT[Slack plus PagerDuty]

  style MONGO fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style SRCCHK fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style BRONZE fill:#cd7f32,stroke:#fff,stroke-width:2px,color:#fff
  style GXB fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style SILVER fill:#90a4ae,stroke:#333,stroke-width:2px,color:#000
  style GXS fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style GOLD fill:#ffd700,stroke:#333,stroke-width:2px,color:#000
  style GXG fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style PG fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style GOLDCHK fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style DBT fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style R fill:#276dc3,stroke:#fff,stroke-width:2px,color:#fff
  style PDF fill:#00897b,stroke:#fff,stroke-width:2px,color:#fff
  style APP fill:#ff4b4b,stroke:#fff,stroke-width:2px,color:#fff
  style IMG fill:#0db7ed,stroke:#fff,stroke-width:2px,color:#fff
  style PUSH fill:#0db7ed,stroke:#fff,stroke-width:2px,color:#fff
  style OPS fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
  style OPSPAGE fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style ALERT fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
```

Stages in run order with local entry points.

```text
1 source checks : sql/plpgsql_checks/source_checks.sql
2 bronze ingest : scripts/run_ingest.py plus scripts/run_bronze.py
3 silver clean  : scripts/run_silver.py plus scripts/run_scd2.py
4 gold build    : scripts/run_gold.py
5 publish       : scripts/run_publish.py writes Gold to Postgres over JDBC
6 gold checks   : sql/plpgsql_checks/gold_checks.sql
7 quality gate  : scripts/run_quality_gate.py plus scripts/run_gx.py
8 semantic      : dbt run plus dbt test in dbt/
9 report        : scripts/run_report.py renders R plus LaTeX to reports/
```

Core rules to keep in mind.

* 1. Every write is idempotent. Bronze, Silver and Gold use MERGE on business keys. Rerun gives same result.
* 2. Every Airflow task retries twice with backoff. Failure lands in `ops.pipeline_runs` and fires alert.
* 3. One script per stage. Each stage logs to its own file under `logs/`.
* 4. Never write back into Mongo. Mongo stays untouched after load.
* 5. Gold refresh is the only path to Postgres, Streamlit, R and API. No side writes.
