# Testing

Tests run before every commit, not just before a PR. Green means unit plus smoke plus DAG plus lint all pass.

```mermaid
graph LR
  UNIT[pytest unit<br>Silver pure funcs] --> CI[GitHub CI]
  SMOKE[pytest smoke<br>sampled run] --> CI
  DAG[pytest dag<br>parse plus no cycles] --> CI
  INT[pytest integration<br>gold plus publish] --> CI
  CI --> DBT[dbt run plus test<br>staging schema]
  CI --> LINT[ruff plus sqlfluff]
  CI --> IMG[docker build<br>no push]
  DBT --> MERGE[Merge to main]
  LINT --> MERGE
  IMG --> MERGE

  style UNIT fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  style SMOKE fill:#0277bd,stroke:#fff,stroke-width:2px,color:#fff
  style DAG fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  style INT fill:#00897b,stroke:#fff,stroke-width:2px,color:#fff
  style CI fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  style DBT fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  style LINT fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  style IMG fill:#0db7ed,stroke:#fff,stroke-width:2px,color:#fff
  style MERGE fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
```

Suites and where they live.

```text
tests/unit        : dedupe trim gender split union enrich plus SCD2 plus gold builders
tests/smoke       : fast run on sampled data in dev
tests/dag         : DAG imports clean, no cycles, retries set, SLA set, graph complete
tests/integration : gold build plus publish plus PLpgSQL checks on clean versus bad seed
tests/fixtures    : seed_gold_clean.sql plus seed_gold_bad.sql
```

Run everything locally before commit.

```bash
uv run pytest tests/unit tests/smoke tests/dag tests/integration -q
uv run ruff check .
uv run ruff format --check src scripts tests dags dashboard
uv run sqlfluff lint sql/
```

Points to remember.

* 1. Every new Silver transform ships with a unit test before it counts as done.
* 2. Never comment out or skip a failing test to get green. Fix it or note it in the PR.
* 3. DAG tests catch parse errors and missing retries before Airflow sees them in prod.
* 4. dbt test runs in CI against a staging like schema, not dev, not prod.
* 5. Hooks in `.githooks` run lint plus tests on commit and push when wired.
