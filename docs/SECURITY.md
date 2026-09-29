# Security

No live credential in files. Local `.env` is sandbox only. Staging and prod resolve from secrets backend at run time.

```mermaid
graph TD
  VAULT[(Vault or cloud manager<br>all live secrets)] --> AF[Airflow Connections<br>plus Variables]
  VAULT --> DBX[Databricks secret scopes]
  VAULT --> API[API startup<br>DSN from backend]
  AF --> PIPE[Pipeline tasks<br>scoped service accounts]
  PIPE --> PG[(Postgres Gold plus ops)]
  APP[Streamlit plus R plus API<br>app role through pooler] --> MASK[gold.dim_customers_masked<br>initials plus hash]
  ADMIN[Ops admin path<br>pii reader role] --> FULL[gold.dim_customers<br>full PII]
  PG --> MASK
  PG --> FULL

  style VAULT fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style AF fill:#0277bd,stroke:#fff,stroke-width:2px,color:#fff
  style DBX fill:#ff3621,stroke:#fff,stroke-width:2px,color:#fff
  style API fill:#512bd4,stroke:#fff,stroke-width:2px,color:#fff
  style PIPE fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style PG fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  style APP fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style ADMIN fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
  style MASK fill:#00897b,stroke:#fff,stroke-width:2px,color:#fff
  style FULL fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff
```

Roles and access in Postgres.

```text
lotus_pipeline  : writer, owns Gold plus marts plus ops writes
lotus_app       : reader through pooler, sees masked view, no unmasked PII
lotus_bi        : general BI grant base, assumed by app role
lotus_pii_reader: narrow admin role, sole reader of unmasked dim_customers
```

Masked view exposes safe columns only.

```sql
-- exposes masked customer pii to general bi roles
CREATE OR REPLACE VIEW gold.dim_customers_masked AS
SELECT
    customer_id::VARCHAR AS customer_id,
    regexp_replace(full_name::VARCHAR, '([A-Za-z])[A-Za-z]*', '\1', 'g') AS name_initials,
    encode(sha256(email::VARCHAR::bytea), 'hex') AS email_hash,
    city::VARCHAR AS city,
    region::VARCHAR AS region,
    loyalty_tier::VARCHAR AS loyalty_tier
FROM gold.dim_customers;
```

Points to remember.

* 1. Read secrets from `.env` via source locally. Never hardcode a credential or connection string.
* 2. Least privilege always. Bronze writer cannot touch Gold. App reader cannot write.
* 3. PII masking uses GRANT plus REVOKE in Postgres, not convention.
* 4. JDBC plus Mongo traffic uses TLS. Data at rest uses provider encryption.
* 5. Tokens never go into `.env` or DAG files. Refresh Databricks auth via login flow.
