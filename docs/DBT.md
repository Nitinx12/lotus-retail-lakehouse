# dbt

dbt owns the governed metric layer on top of Postgres Gold. Spark builds staging marts. dbt builds served truth. If two dashboards disagree, dbt wins.

```mermaid
graph TD
  SRC1[(gold.fact_orders)] --> M1[revenue_by_store_month]
  SRC2[(gold.dim_stores)] --> M1
  SRC3[(gold.fact_order_details)] --> M2[return_rate_by_product]
  SRC4[(gold.fact_returns)] --> M2
  SRC1 --> M3[ramadan_seasonality]
  SRC5[(gold.dim_date)] --> M3
  M1 --> TST[dbt test]
  M2 --> TST
  M3 --> TST
  TST --> DOCS[dbt docs lineage]
  TST --> SERVE[Streamlit plus R plus API read marts]

  style SRC1 fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style SRC2 fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style SRC3 fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style SRC4 fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style SRC5 fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style M1 fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style M2 fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style M3 fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style TST fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style DOCS fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style SERVE fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
```

Models in this repo.

```text
models/marts/revenue_by_store_month.sql : store month revenue cost orders
models/marts/return_rate_by_product.sql : product times ordered times returned return rate
models/marts/ramadan_seasonality.sql    : month is_ramadan revenue orders
models/sources.yml : declares gold dims plus facts as sources
models/schema.yml  : not null plus unique plus relations tests
```

Run and test locally.

```bash
uv run dbt run --project-dir dbt --target dev
uv run dbt test --project-dir dbt --target dev
uv run dbt docs generate --project-dir dbt
```

Points to remember.

* 1. Mart names in dbt are bare names. Spark files use mart prefix and stay unpublished.
* 2. Casts use `::VARCHAR` style to satisfy SQLFluff.
* 3. dbt runs after JDBC publish and after PLpgSQL gold checks in the DAG.
* 4. dbt test failure blocks the run the same way a GX failure does.
* 5. Use `dbt docs serve` output as living lineage from source to mart.
