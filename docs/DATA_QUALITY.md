# Data Quality

Quality gates sit before and after every layer change. Failure blocks promotion. Never route around a red gate.

```mermaid
graph TD
  PRE[Pre ingest<br>PLpgSQL source checks] --> BRZ[Bronze<br>GX suite]
  BRZ --> SIL[Silver<br>GX suite]
  SIL --> GLD[Gold<br>GX suite]
  GLD --> PSQL[Postgres Gold<br>PLpgSQL gold checks]
  PSQL --> DBT[dbt tests<br>not null plus unique plus relations]
  DBT --> OK[Promote to serve]
  BRZ -. fail .-> BLOCK[Block plus alert]
  SIL -. fail .-> BLOCK
  GLD -. fail .-> BLOCK
  PSQL -. fail .-> BLOCK
  DBT -. fail .-> BLOCK
  BLOCK --> OPS[(ops.quality_results<br>plus ops.alerts)]

  style PRE fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style BRZ fill:#cd7f32,stroke:#fff,stroke-width:2px,color:#fff
  style SIL fill:#90a4ae,stroke:#333,stroke-width:2px,color:#000
  style GLD fill:#ffd700,stroke:#333,stroke-width:2px,color:#000
  style PSQL fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style DBT fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style OK fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style BLOCK fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
  style OPS fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
```

What each gate checks.

```text
source_checks.sql : stuck running rows in ops.pipeline_runs, blocks ingest on dirty state
GX bronze : row count above zero plus key column exists for all 9 tables
GX silver : unique customer_id, gender in Male Female, product_name present,
            unique order_id, payment_method in Cash Credit Card Debit Card Fawry InstaPay Vodafone Cash
GX gold   : customer_sk present on facts, unique order_id on fact_orders
gold_checks.sql : no future order_date, no negative return_amount,
                  no orphan returns, no null customer_sk
dbt tests : not null plus unique plus foreign key relations on the 3 marts
```

Run gates locally with these entry points.

```bash
uv run python scripts/run_quality.py
uv run python scripts/run_gx.py --suite bronze
uv run python scripts/run_gx.py --suite silver
uv run python scripts/run_gx.py --suite gold
uv run python scripts/run_plpgsql.py
```

Points to remember.

* 1. Every Silver transform ships with a unit test. Done means code plus test plus green gate.
* 2. Great Expectations results land in `ops.quality_results` with pass percent and fail count.
* 3. PLpgSQL loops catch what GX and dbt miss, such as future dates and negative amounts.
* 4. Never skip or comment out a failing test to force green. Fix it or flag it in the PR.
* 5. Schema drift in Bronze uses mergeSchema true and logs to `ops.schema_changes`.
