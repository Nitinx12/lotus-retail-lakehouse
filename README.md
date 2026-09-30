<div align="center">

![Project logo](assets/logo.png)

# Lotus Retail Lakehouse

**A retail lakehouse that carries data from raw landing to governed marts, with full operational visibility.**

</div>

Lotus Retail Lakehouse moves the Lotus retail dataset from MongoDB through Bronze, Silver and Gold layers into a Postgres serving warehouse and dbt marts. Quality gates and ops tracking run at every stage.

For the full design read [ARCHITECTURE.md](ARCHITECTURE.md). For working rules read [AGENTS.md](AGENTS.md).

## Highlights

* **MongoDB** is the raw landing zone and stays untouched after load.
* **PySpark** transforms data on Delta tables across the medallion layers.
* **Postgres** is both the serving warehouse and the ops store.
* **Airflow** is the control plane, with retries, backfills and SLAs.
* **dbt** is the semantic layer, with tests and lineage.
* **Streamlit**, **R** and an optional API read from Gold.

## Pipeline Flow

```mermaid
graph TD
  MONGO[(Mongo lotus_retail<br>9 collections)] --> SRCCHK[Source checks<br>PLpgSQL]
  SRCCHK --> BRONZE[Bronze<br>PySpark Delta ingest]
  BRONZE --> GXB[Great Expectations<br>Bronze suite]
  GXB --> SILVER[Silver<br>clean, dedupe, SCD2]
  SILVER --> GXS[Great Expectations<br>Silver suite]
  GXS --> GOLD[Gold<br>star schema]
  GOLD --> GXG[Great Expectations<br>Gold suite]
  GXG --> PG[(Postgres Gold<br>star schema and marts)]
  PG --> GOLDCHK[Gold checks<br>PLpgSQL]
  GOLDCHK --> DBT[dbt run and test]
  DBT --> APP[Streamlit refresh]
  DBT --> R[R analysis]
  R --> PDF[LaTeX PDF report]
  APP --> IMG[Docker build]
  PDF --> IMG
  IMG --> PUSH[Push to registry]
  BRONZE -. log .-> OPS[(Postgres ops schema)]
  SILVER -. log .-> OPS
  GOLD -. log .-> OPS
  GXB -. results .-> OPS
  GXS -. results .-> OPS
  GXG -. results .-> OPS
  OPS --> OPSPAGE[Ops dashboard]
  OPS --> ALERT[Slack and PagerDuty]

  classDef source fill:#6a1b9a,stroke:#fff,stroke-width:2px,color:#fff
  classDef check fill:#37474f,stroke:#fff,stroke-width:2px,color:#fff
  classDef bronze fill:#cd7f32,stroke:#fff,stroke-width:2px,color:#fff
  classDef quality fill:#f9a825,stroke:#333,stroke-width:2px,color:#000
  classDef silver fill:#90a4ae,stroke:#333,stroke-width:2px,color:#000
  classDef gold fill:#ffd700,stroke:#333,stroke-width:2px,color:#000
  classDef serve fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  classDef semantic fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  classDef analyze fill:#276dc3,stroke:#fff,stroke-width:2px,color:#fff
  classDef report fill:#00897b,stroke:#fff,stroke-width:2px,color:#fff
  classDef app fill:#ff4b4b,stroke:#fff,stroke-width:2px,color:#fff
  classDef ship fill:#0db7ed,stroke:#fff,stroke-width:2px,color:#fff
  classDef ops fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff
  classDef watch fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  classDef alert fill:#c62828,stroke:#fff,stroke-width:2px,color:#fff

  class MONGO source
  class SRCCHK check
  class BRONZE bronze
  class GXB quality
  class SILVER silver
  class GXS quality
  class GOLD gold
  class GXG quality
  class PG serve
  class GOLDCHK check
  class DBT semantic
  class R analyze
  class PDF report
  class APP app
  class IMG,PUSH ship
  class OPS ops
  class OPSPAGE watch
  class ALERT alert
```

## Data Layers and Serving

```mermaid
graph LR
  B[BRONZE<br>9 Delta tables<br>mergeSchema on] --> S[SILVER<br>cleaned and typed<br>SCD2 on customers<br>and employees]
  S --> G[GOLD<br>dims and facts<br>Z ordered facts]
  G --> P[(POSTGRES GOLD<br>JDBC load)]
  P --> M[MARTS<br>dbt governed views]
  P --> V[MASKED VIEW<br>PII safe reader]
  M --> D[Streamlit dashboard]
  V --> D
  M --> API[Optional API]
  V --> API
  M --> RR[R report]
  P --> OPS[(OPS SCHEMA<br>runs, quality,<br>alerts, checkpoints)]

  classDef bronze fill:#cd7f32,stroke:#fff,stroke-width:2px,color:#fff
  classDef silver fill:#90a4ae,stroke:#333,stroke-width:2px,color:#000
  classDef gold fill:#ffd700,stroke:#333,stroke-width:2px,color:#000
  classDef serve fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
  classDef semantic fill:#ff694a,stroke:#fff,stroke-width:2px,color:#fff
  classDef safe fill:#2e7d32,stroke:#fff,stroke-width:2px,color:#fff
  classDef app fill:#ff4b4b,stroke:#fff,stroke-width:2px,color:#fff
  classDef ops fill:#455a64,stroke:#fff,stroke-width:2px,color:#fff

  class B bronze
  class S silver
  class G gold
  class P serve
  class M semantic
  class V safe
  class D,API,RR app
  class OPS ops
```

## Tech Stack

<div align="center">

Core runtimes, data, orchestration, serving and quality, pinned in `pyproject.toml`, the compose files and the CI workflows.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-4.1-E25A1C?logo=apachespark&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?logo=mongodb&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-3-017CEE?logo=apacheairflow&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.12-FF694A?logo=dbt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-0db7ed?logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-charts-7F56D9?logo=plotly&logoColor=white)
![uv](https://img.shields.io/badge/uv-sync-2E3440?logo=uv&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-lint-000000?logo=ruff&logoColor=white)
![GX](https://img.shields.io/badge/Great_Expectations-gates-F9A825?logo=great-expectations&logoColor=black)

<table>
  <thead>
    <tr>
      <th align="center">Layer</th>
      <th align="center">Technology</th>
      <th align="center">Version and notes</th>
    </tr>
  </thead>
  <tbody>
    <tr><td align="center"><b>Language</b></td><td align="center">Python</td><td align="center">3.13 (CI on 3.11, Docker on 3.12 slim)</td></tr>
    <tr><td align="center"><b>OS</b></td><td align="center">Ubuntu</td><td align="center">24.04 (CI on ubuntu-latest, Docker on bookworm)</td></tr>
    <tr><td align="center"><b>Compute</b></td><td align="center">PySpark</td><td align="center">4.1.x with OpenJDK 17</td></tr>
    <tr><td align="center"><b>Warehouse</b></td><td align="center">PostgreSQL</td><td align="center">16, serving and ops store</td></tr>
    <tr><td align="center"><b>Source</b></td><td align="center">MongoDB</td><td align="center">Operational source with an incremental <code>$gt</code> watermark</td></tr>
    <tr><td align="center"><b>Transform</b></td><td align="center">dbt core and dbt postgres</td><td align="center">1.12 and 1.11, 17 models, 100+ tests</td></tr>
    <tr><td align="center"><b>Orchestration</b></td><td align="center">Apache Airflow</td><td align="center">3.3.x on CeleryExecutor</td></tr>
    <tr><td align="center"><b>Quality</b></td><td align="center">Great Expectations</td><td align="center">1.21, Bronze, Silver and Gold suites</td></tr>
    <tr><td align="center"><b>BI</b></td><td align="center">Streamlit and Plotly</td><td align="center">1.62 and 7.0 on the Gold star schema</td></tr>
    <tr><td align="center"><b>Packaging</b></td><td align="center">uv</td><td align="center"><code>uv.lock</code> is the source of truth</td></tr>
    <tr><td align="center"><b>Lint and format</b></td><td align="center">Ruff, SQLFluff, pre-commit</td><td align="center"><code>ruff check</code>, <code>ruff format</code>, <code>sqlfluff lint</code></td></tr>
    <tr><td align="center"><b>Containers</b></td><td align="center">Docker and Compose</td><td align="center"><code>Dockerfile</code> and <code>Dockerfile.airflow</code></td></tr>
    <tr><td align="center"><b>CI</b></td><td align="center">GitHub Actions</td><td align="center">Lint, dashboard smoke, unit, DAG, Docker and integration jobs</td></tr>
  </tbody>
</table>

</div>

## Getting Started

The steps below take you from a fresh clone to a running pipeline. Each step shows a Windows (PowerShell) command first, then the Linux or macOS equivalent where it differs.

**1. Fork and clone**

```powershell
git clone https://github.com/<your-user>/lotus-retail-lakehouse.git
cd lotus-retail-lakehouse
```

**2. Install dependencies**

```powershell
uv sync
```

**3. Create the local env file**

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

**4. Start the infrastructure**

```powershell
powershell -File scripts/docker_up.ps1 up -d
```

```bash
bash scripts/docker_up.sh up --build
```

**5. Initialise the ops schema**

```powershell
$env:PYTHONPATH = "."
uv run python scripts/init_ops.py
```

```bash
PYTHONPATH=. uv run python scripts/init_ops.py
```

**6. Run the stages in order**

```powershell
powershell -File scripts/run_ingest.ps1
powershell -File scripts/run_silver.ps1
powershell -File scripts/run_gold.ps1
powershell -File scripts/run_publish.ps1
powershell -File scripts/run_quality_gate.ps1
powershell -File scripts/run_report.ps1
```

```bash
bash scripts/run_ingest.sh
bash scripts/run_silver.sh
bash scripts/run_gold.sh
bash scripts/run_publish.sh
bash scripts/run_quality_gate.sh
bash scripts/run_report.sh
```

**7. Build the marts and open the dashboard**

```powershell
$env:DBT_PROFILES_DIR = "./dbt"
uv run dbt run --project-dir dbt --target dev
uv run dbt test --project-dir dbt --target dev
uv run streamlit run dashboard/app.py
```

**8. Verify before every commit**

```powershell
uv run pytest tests/unit tests/smoke tests/dag tests/integration -q
uv run ruff check .
uv run ruff format --check src scripts tests dags dashboard
uv run sqlfluff lint sql/
```

> **Connection notes.** Gold writers use the pipeline role, which owns the Gold and marts schemas. The dashboard, R and the API read through the pooler with the app role, which sees the masked customer view and never the unmasked PII table. Staging and prod secrets resolve through a Vault style backend and Airflow connections, never through committed files. See [docs/SECURITY.md](docs/SECURITY.md) and [docs/ENVIRONMENTS.md](docs/ENVIRONMENTS.md) for detail.

## Project Layout

```text
src/         Pure transforms: input frame in, output frame out
scripts/     One runner per stage, with matching .ps1 and .sh twins
sql/         Ops DDL, roles, grants, masked view and PLpgSQL checks
dags/        Airflow control plane
dbt/         Governed marts
dashboard/   Retail view and ops page
r/           Analysis sources
dotnet-api/  Optional read only Gold serving API
tests/       Unit, smoke, DAG integrity and integration suites
docs/        Per area guides with flow charts
runbooks/    Restore procedure
docker/      Compose files and images
data/        Local only, gitignored seeds and backups
logs/        Per stage logs read by ops monitoring
```

## Quality Gates

Every Silver transform ships with a unit test. A failing test blocks the run, so never route around it. Use the one shot gate for a full local check:

```bash
bash scripts/run_tests.sh
```

Or run the suites individually:

```powershell
uv run pytest tests/unit -q
uv run pytest tests/smoke -q
```

See [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md) and [docs/TESTING.md](docs/TESTING.md) for thresholds and suite layout.

## Documentation

Start with the design docs, then go deeper by area. Guides live under `docs/`, plus the two root guides.

| Guide | What you will find |
|:---|:---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system design from landing to serving, with the major decisions |
| [AGENTS.md](AGENTS.md) | Working rules for code style, tests and git hygiene |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Stage order, entry points and rerun behaviour |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Table and column meanings across Bronze, Silver, Gold and marts |
| [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md) | Quality suites, thresholds and gate behaviour |
| [docs/DBT.md](docs/DBT.md) | Mart definitions, tests and lineage usage |
| [docs/SECURITY.md](docs/SECURITY.md) | Roles, masked views, secrets handling and least privilege |
| [docs/ENVIRONMENTS.md](docs/ENVIRONMENTS.md) | Dev, staging and prod separation and the promotion path |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker images, compose stack and publish flow |
| [docs/MONITORING.md](docs/MONITORING.md) | Ops tables, SLAs, alerts and dashboard usage |
| [docs/API.md](docs/API.md) | Optional reader API surface and auth model |
| [docs/TESTING.md](docs/TESTING.md) | Unit, smoke, DAG and integration suites, plus the gate script |
