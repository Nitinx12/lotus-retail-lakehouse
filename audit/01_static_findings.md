# 01 Static findings

Method: four parallel read only audits plus targeted reverification of every P0 by reading the cited file. Linters run: `uv run ruff check src scripts tests dags dashboard` passes, `python -m compileall` on `src` plus `scripts` plus `main.py` passes, `shellcheck` not installed so script review is manual. No pipeline stage was executed for this file. Severity follows the mission triage scale.

## Ingest and Bronze

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S01 | Bronze | scripts/run_bronze.py:151 | drift | P1 | Full parquet overwrite per collection, no MERGE keyed on source key, so Section 4 MERGE claim is false and Delta time travel rollback cannot exist | `df.to_parquet(path, index=False)` |
| S02 | Bronze | scripts/run_bronze.py:99-105,152-155 | bug | P1 | `last_object_id` is written to `ops.extract_checkpoints` but never read back, resume decision uses row count only, so a mid collection death rereads everything | `read_checkpoint` selects only `rows_copied` |
| S03 | Bronze | scripts/run_bronze.py:83-88 | risk | P1 | Count equality skip misses content changes, a delete plus insert with equal count skips the load with no hash compare | `return live_count != checkpoint_rows` |
| S04 | Bronze | scripts/run_bronze.py:137-138 | bug | P2 | Unordered `find()` makes load order nondeterministic and the stored `last_object_id` meaningless | `docs = list(db[name].find())` then `docs[-1]` |
| S05 | Bronze | scripts/run_bronze.py:137 | risk | P2 | Whole collection pulled into driver memory through pandas, the local equivalent of a forbidden driver side collect | `docs = list(db[name].find())` |
| S06 | Bronze | scripts/run_bronze.py:92-95,141-149 | drift | P2 | Schema evolution keeps prior column order and logs added columns, but first loads log nothing and drops plus type changes are never logged | only `"add_column"` inserted, `if not prev: return []` |
| S07 | Bronze/Gold | src plus scripts, grep verified | drift | P2 | No Delta, mergeSchema, MERGE, OPTIMIZE, ZORDER, or catalog names anywhere in ETL code, Sections 4 and 5 describe a Databricks engine that does not exist here | grep for `Delta\|mergeSchema\|OPTIMIZE\|ZORDER` returns zero hits |

## Silver transforms

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S08 | Silver | src/silver/transforms.py:40-50 | bug | P1 | `clean_customers` raises KeyError on missing key or phone columns, phone cast unguarded | `out[out["customer_id"]...]`, `out["phone"].astype("string")` |
| S09 | Silver | src/silver/transforms.py:54-60 | bug | P2 | `split_product_name` stringifies NaN into `"nan"` strings and raises KeyError when the raw column is absent | `out[col].astype(str).str.split(...)` |
| S10 | Silver | src/silver/transforms.py:88-90 | bug | P1 | Cross file union is schema blind concat plus `keep="first"`, so 2022 2023 silently wins overlapping order ids with no collision log | `pd.concat([first, second])` then `dedupe` |
| S11 | Silver | src/silver/transforms.py:40-43, src/silver/scd2.py:35 | bug | P1 | Customer dedupe `keep="first"` runs before SCD2 and before the null key drop, destroying intra batch history and letting a junk first row evict a good row, while SCD2 itself keeps last | `dedupe(out, ["customer_id"])` precedes null filter |
| S12 | Silver | scripts/run_silver.py:87-98 | drift | P1 | Stores, employees, date, and order details are metadata strip only passthroughs with no dedupe, trim, case, null, or cast handling | loop body is `drop_extract_meta(pd.read_parquet(...))` |
| S13 | Silver | src/silver/transforms.py:73-84 | risk | P2 | Bad order dates coerce to NaT but the row is kept, downstream point in time join turns it into a null surrogate orphan | `errors="coerce"` with no drop |
| S14 | Silver | src/silver/transforms.py:27-36 | risk | P2 | Unknown genders intentionally pass through, so real data deterministically fails the gender domain gates | `mapped.fillna(stripped)` |

## SCD Type 2

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S15 | SCD2 | src/silver/scd2.py:16-23 | bug | P2 | Hash conflates NULL with empty string, ignores untracked column drift by design, raises KeyError on a missing tracked column | `.astype("string").fillna("")` then md5 |
| S16 | SCD2 | src/silver/scd2.py:61 | bug | P1 | Corrupted dimension with two current rows crashes with ValueError instead of healing or blocking | `elif cur.loc[key, HASH_COL] != row[HASH_COL]:` yields a Series |
| S17 | SCD2 | scripts/run_scd2.py:74-77,58 | bug | P0 | Every change in a run is stamped with the global max order date, so backdated and late arriving changes get wrong validity windows and same day intermediates collapse to keep last | `change_date = parsed.max().date().isoformat()` |
| S18 | SCD2 | src/silver/scd2.py:39,45 | risk | P1 | First load surrogate keys follow nondeterministic input order, incremental max plus one has no locking | `range(1, len(out)+1)`, `max_sk = int(table[sk_col].max())` |
| S19 | SCD2 | src/silver/scd2.py:96-108 | risk | P1 | Point in time join preserves orphans with null keys but fans out facts when overlapping versions exist, with no overlap guard | `facts.merge(dim, on=natural_key, how="left")`, no uniqueness check |
| S20 | Gold | src/gold/build.py:28 | bug | P1 | Employee point in time match admits rows through the null key path, letting customer orphans bypass the employee date filter | `matched = merged[active \| merged["employee_sk"].isna()]` |
| S21 | Gold | src/gold/build.py:39-42,51-54,96-99 | drift | P1 | Every Gold builder strips `_batch_id`, violating the Section 4 run identifiable and rollback requirement | drop of columns starting with `_batch_id`, three sites |

## Gold, marts, dbt

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S22 | Gold | src plus scripts, grep verified | bug | P1 | Money is float64 throughout Python and `to_sql` inference, dbt NUMERIC only masks the issue at mart read time | no `Decimal` import in src or scripts |
| S23 | Gold | src/gold/build.py:60,79,88 | risk | P2 | Marts group nullable keys with no null key exclusion, missing date ids form stray groups | `groupby(["store_id","month"])` after left joins |
| S24 | Mart | dbt/models/marts/revenue_by_store_month.sql:5-6 | risk | P1 | Revenue is gross shipped revenue with no netting of returns and no defined discount, tax, or currency treatment | `sum(total_revenue::NUMERIC) AS revenue` |
| S25 | Mart | dbt/models/marts/return_rate_by_product.sql:9-11 | bug | P1 | Order level return flag is applied to every detail line, inflating rates on multi item orders | `sum(CASE WHEN r.order_id IS NULL THEN 0 ELSE 1 END)` over `count(*)` lines |
| S26 | Mart | dbt/models/marts/ramadan_seasonality.sql:8 | drift | P1 | dbt trusts `dim_date.is_ramadan` from upstream while dashboard and R retag months from hardcoded ranges, two Ramadan definitions | `LEFT JOIN ... dim_date` vs `RAMADAN_RANGES` in dashboard/lib/db.py:20-24 |
| S27 | Mart | src plus scripts, verified | risk | P1 | No code anywhere sets `is_ramadan`, the flag passes through from Mongo Bronze untouched with no generator or validator | `dim_date` is `drop_extract_meta` only |
| S28 | Mart | ARCHITECTURE.md:138 vs :146-153 | drift | P2 | Section 8 mart names carry the `mart_` prefix while Section 9 dbt filenames do not | `mart_revenue_by_store_month` vs `revenue_by_store_month.sql` |
| S29 | Mart | src/gold/build.py:58,74,87 vs dbt/models/marts | bug | P1 | Same three metrics are built by both Spark path and dbt with no single source of truth statement | `def mart_revenue_by_store_month` vs `sum(total_revenue::NUMERIC)` |
| S30 | Publish | scripts/run_publish.py:31-40 | bug | P1 | Spark `mart_*` parquet files are never published to Postgres, dbt is the only serving mart builder | `TABLES` lists base tables only, no marts |
| S31 | Quality | scripts/run_quality.py:117,105-107 | drift | P1 | Gold quality reconciles the Spark parquet mart while dashboard and R read the dbt mart | `read_parquet(GOLD_DIR / "mart_revenue_by_store_month.parquet")` |
| S32 | dbt | dbt/models/schema.yml:4-41 | risk | P2 | No composite store plus month uniqueness, no grain test on the Ramadan mart, cost and order counts untested | `unique` only on `return_rate_by_product.product_id` |
| S33 | dbt | dbt/tests | improvement | P2 | Revenue has reconcile plus grain tests, returns and Ramadan have no dbt test | only `ref('revenue_by_store_month')` tested |

## Data quality suites

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S34 | Quality | src/quality/gx_suites.py:37-41 | improvement | P1 | Bronze GX is trivially passing, row count plus column exists only, garbage rows pass | `ExpectTableRowCountToBeBetween(min_value=1)` |
| S35 | Quality | scripts/run_quality.py:62 | bug | P1 | Bronze suite hardcodes the source total 42877, legitimate data growth fails forever | `0 if total == 42877 else abs(total - 42877)` |
| S36 | Quality | src/quality/gates.py:25-26 | risk | P2 | Gate domain checks drop nulls while strict GX InSet may fail them, two suites disagree on the same data | `set(df[col].dropna().astype(str)) - allowed` |
| S37 | Quality | scripts/run_plpgsql.py:87-93 | risk | P2 | PL/pgSQL runner records full pass without inspecting procedure outputs, a swallowing procedure reads as silent pass | `VALUES (%s,%s,100.0,0)` unconditional |
| S38 | Quality | scripts/run_sql.py:81-101 | risk | P2 | Mart reconcile records results but never blocks on mismatch | no blocked flag on reconcile path |
| S39 | Orchestration | main.py:28-42 | bug | P2 | `all` expansion excludes GX suites and extract, the default full run never executes GX gates | `EXPANSIONS["all"]` lists ten stages, no `gx` |

## Postgres and security

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S40 | Ops | sql/ops_schema.sql:13 plus src/ops/db.py:33-40 | bug | P1 | Primary key on run plus task with upsert on conflict overwrites retries, attempt history is lost | `PRIMARY KEY (run_id, task_name)`, `ON CONFLICT ... DO UPDATE SET` |
| S41 | Ops | sql plus procedures, grep verified | bug | P2 | No attempt column anywhere, retry and SLA claims are unenforceable in the store | grep `attempt` in sql returns zero hits |
| S42 | Ops | sql/ops_schema.sql:33-38 | risk | P2 | `schema_changes` has no key and no indexed lookup, duplicates possible | table defined with no PK |
| S43 | Ops | sql/index/01_ops_indexes.sql:2-3 | risk | P2 | Stuck run scanner filters on status plus started at but the only index leads with task name | `WHERE status = 'running' AND started_at < now()` |
| S44 | Checks | sql/plpgsql_checks/source_checks.sql:9 | risk | P2 | Source check excludes its own task name, concurrent source suites miss each other | `AND task_name <> 'plpgsql_source'` |
| S45 | Checks | sql/plpgsql_checks/gold_checks.sql:17-22 | risk | P2 | Orphan returns check joins on order id only, ignoring product grain | `WHERE NOT EXISTS (... fact_order_details ... d.order_id` |
| S46 | Security | docker/postgres/init/01_roles_and_schemas.sh:11-14 vs sql/security/roles.sql:4-14 | bug | P0 | Two disjoint role sets, docker creates pipeline, app, api reader, pii reader while SQL expects ops, app, pii reader with lotus prefix, grants target nonexistent roles depending on path | `CREATE ROLE pii_reader` vs `rolname = 'lotus_pii_reader'` |
| S47 | Security | docker/postgres/init/03_grants.sql:12 plus sql/security/grants.sql:8 | bug | P0 | Dashboard role keeps select on unmasked `gold.dim_customers`, revoke strips public only, only the API reader is revoked | `GRANT SELECT ON ALL TABLES IN SCHEMA gold TO lotus_app` |
| S48 | Security | docker/postgres/init/03_grants.sql:24-25 | risk | P1 | Default privileges regrant all future gold tables to the API reader with no unmasked customer exception | `ALTER DEFAULT PRIVILEGES ... IN SCHEMA gold GRANT SELECT ... TO lotus_api_reader` |
| S49 | Security | sql/security/grants.sql:4-12 plus scripts/run_publish.py:129-135 | bug | P1 | Grants and masked view silently no op when `dim_customers` is absent, publish never reapplies them, fresh databases stay unprotected | `IF EXISTS (... dim_customers) THEN EXECUTE` else nothing |
| S50 | Security | sql/security/masked_views.sql:15 | bug | P1 | View calls `sha256` with no `CREATE EXTENSION pgcrypto` anywhere, queries fail when the extension is missing | `encode(sha256(email::VARCHAR::bytea), 'hex')` |
| S51 | Security | sql/security/roles.sql:20 | risk | P1 | App role inherits the BI role and holds full gold plus marts plus ops select, not least privilege | `GRANT lotus_bi TO lotus_app` |
| S52 | Publish | scripts/run_publish.py:83-105,119-128 | bug | P1 | Delete plus append runs per table in separate transactions, a failure or a concurrent reader sees split versions across eight commits | `DELETE FROM ...` plus `engine.begin()` inside the table loop |
| S53 | Publish | scripts/run_publish.py:95-104 | risk | P2 | Delete instead of truncate with no staging swap, first append creates tables with no keys or constraints | `if_exists="append"`, indexes readded later |
| S54 | Publish | docker/postgres/init/03_grants.sql:11-15 | bug | P1 | Publish connects as the app role but grants show select only, with no insert, delete, or create rights | `GRANT SELECT ON ALL TABLES IN SCHEMA gold TO lotus_app` |
| S55 | Reconcile | sql/functions/03_reconcile_marts.sql:16-17 | bug | P1 | Mart reconciler has no existence guard, dynamic SQL errors when dbt marts are not built yet | `SELECT coalesce(sum(revenue...) FROM marts.revenue_by_store_month` |
| S56 | Triggers | sql/triggers/01_ops_triggers.sql:14-17 vs :8-11 | bug | P2 | Quality alert fires on insert only while run alert fires on insert or update, a score update that lowers a suite never alerts | `AFTER INSERT ON ops.quality_results` |
| S57 | Runners | sql/apply_ops.sql:2-6, sql/apply_gold.sql:2-7 | drift | P2 | Apply files use psql `\ir` which psycopg2 cannot execute, runners use separate step lists, the files are dead | `\ir ops_schema.sql` |
| S58 | Runners | scripts/run_sql.py:36-44 | risk | P1 | SQL runner applies role creation over an app role connection, role creation needs superuser rights and belongs in docker init only | `CREATE ROLE lotus_app WITH LOGIN` via warehouse conn |
| S59 | Config | scripts/run_sql.py:48-50 vs docker init | bug | P1 | Scripts default to the `lotus_ops` user while docker creates only `lotus_pipeline`, same split for the PII reader name | `default_user = "lotus_ops"` vs `CREATE ROLE lotus_pipeline` |
| S60 | Grants | grant files, absence verified | risk | P2 | No execute grants on ops and guard functions or on the maintenance procedures, cross role calls fail when the owner differs | no `GRANT EXECUTE` hits in grant files |

## DAG, scripts, Docker, CI, secrets

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S61 | DAG | dags/lotus_pipeline_dag.py:107-108 | bug | P1 | Naive start date with midnight UTC schedule leaves about 90 minutes to the 7 AM IST Gold SLA while the serial path needs about 215 minutes | `schedule="@daily"`, naive `datetime(2024, 1, 1)` |
| S62 | DAG | dags/lotus_pipeline_dag.py:125-208 | bug | P1 | Thirty minute end to end SLA is unenforceable, per task SLAs sum past 215 minutes with no DAG level budget and retries add 15 minutes per failing task | `sla=timedelta(minutes=20)` five times |
| S63 | DAG | dags/lotus_pipeline_dag.py:218-224 | bug | P1 | Push task runs docker push plus git push on every daily run, and `.git` is not mounted in the airflow service | `bash_command="... && git push origin HEAD"` |
| S64 | DAG | dags/lotus_pipeline_dag.py:176-181,226-237 | drift | P2 | Extra gold checks task between A8 and A9 is absent from the spec diagram, and the DAG test locks the drift in | `>> jdbc_to_postgres >> plpgsql_gold_checks >> dbt` |
| S65 | DAG | dags/lotus_pipeline_dag.py:60,85 | risk | P2 | Environment, connection ids, tags, and commands bind at parse time with a metadata DB read on every scheduler parse | `LOTUS_ENV = resolve_env()`, `CFG = ENV_CONFIG[LOTUS_ENV]` |
| S66 | DAG | dags/lotus_pipeline_dag.py:27-48,118 | bug | P2 | SLA miss callback reuses the failure handler, the SLA path emits a near empty alert | `f"lotus sla miss: {getattr(context, 'dag_id', context)}"` |
| S67 | DAG | whole DAG file, AST verified | drift | P2 | No logical date templating, so date range backfills rerun identical logic | no `{{ ds }}` or `logical_date` references |
| S68 | DAG | dags/lotus_pipeline_dag.py:15 | risk | P2 | Legacy PostgresOperator import is a deprecated alias under the pinned provider range | `from airflow.providers.postgres.operators.postgres import PostgresOperator` |
| S69 | DAG | dags/lotus_pipeline_dag.py:210-216 | drift | P2 | Docker build covers the pipeline image only, not dashboard, report, or API | `docker build -f docker/Dockerfile.pipeline` |
| S70 | Scripts | five `.sh` files line 1 | bug | P2 | Missing shebang, first line is a comment, direct execution fails and only `bash scripts/...` works | line 1 is `#` comment in run_ingest, run_silver, run_gold, run_publish, run_quality_gate |
| S71 | Scripts | ARCHITECTURE.md:59 | drift | P2 | `run_all.sh` is referenced but absent | `Test-Path scripts/run_all.sh` is false |
| S72 | Scripts | scripts/run_report.sh:4-11 | bug | P2 | Report outputs to repo `output/` instead of `reports/` and writes no stage log | `REPORT_OUTPUT_DIR=.../output/...`, no tee |
| S73 | Scripts | scripts/run_report.ps1:14-17 | bug | P2 | Windows report wrapper exits zero when quarto is missing, masking a failure the shell script surfaces | `quarto not found, skipping report ... exit 0` |
| S74 | Scripts | dags/lotus_pipeline_dag.py:192-202 | bug | P2 | Double report build, quarto render then latexmk on a tex file the quarto flow never produces | `quarto render report.qmd` vs `latexmk ... reports/report.tex` |
| S75 | Docker | docker/Dockerfile.airflow:5-10 | risk | P2 | Providers only upper bounded and dbt postgres fully unpinned, drifts from local floors | `"apache-airflow-providers-databricks<8"`, bare `dbt-postgres` |
| S76 | Docker | docker/docker-compose.yml:108,149,206-208 | risk | P2 | Passwords inline in environment and connection strings, visible through inspect, runtime only not baked | `DATABASE_URL: postgresql://...:${LOTUS_PIPELINE_PASSWORD}@...` |
| S77 | Docker | docker/Dockerfile.api vs ARCHITECTURE.md:292-298 | drift | P3 | API Dockerfile exists and is CI built but missing from the Section 17 layout | layout lists four images, file is the fifth |
| S78 | CI | .github/workflows | improvement | P3 | Eight actions float on major tags and `ci.yml` lacks permission scoping | `actions/checkout@v4`, `setup-uv@v5` |
| S79 | CI | .github/workflows/docker-publish.yml:19-25 | drift | P2 | Publish matrix and docker job skip the airflow and API images, no R or latex validation job | matrix holds three of five images |
| S80 | Secrets | .env:10,75-76, file and line only | risk | P2 | Local git ignored `.env` holds keys absent from the example plus values outside the placeholder convention, rotate if ever copied elsewhere | `git ls-files .env` is empty, values withheld |

## Streamlit, R, C# API

| # | Area | File:Line | Type | Severity | Description | Evidence |
|---|---|---|---|---|---|---|
| S81 | Streamlit | dashboard/lib/db.py:68-80 | risk | P2 | Every query failure is swallowed into an empty frame, pages show a generic warning and hide the real error | `except Exception: ... return pd.DataFrame()` |
| S82 | Streamlit | dashboard/lib/config.py:47 | risk | P1 | Masked view is used but role gating is unenforced and the dashboard ships with no auth | `Nothing here gates access yet` in dashboard README |
| S83 | Streamlit | dashboard/lib/config.py:36 vs ARCHITECTURE.md:202 | drift | P2 | Code freshness window is 24 hours sliding, spec promises 7 AM IST | `GOLD_FRESHNESS_SLA_HOURS = 24` |
| S84 | R | r directory listing | risk | P2 | No renv lock or description, package versions are unpinned and unreproducible | no lock file present |
| S85 | R | r/R/01_load_data.R:31-44,99-101 | bug | P1 | Missing password silently renders random demo data as if real, the knit always succeeds | `if (!is.null(con))` else seeded random frames |
| S86 | C# | dotnet-api/LotusApi/Data/LotusGoldContext.cs:17,70-96 | bug | P0 | Unmasked customer entity with mail, name, and phone is mapped, protection depends entirely on the DB role | `DbSet<DimCustomer> DimCustomers` |
| S87 | C# | dotnet-api/LotusApi/Program.cs:1-32 | risk | P1 | No authentication or authorization middleware or attributes | no `UseAuthentication`, no `Authorize` |
| S88 | C# | dotnet-api/LotusApi/Controllers/MartsController.cs:15-23 | drift | P2 | Only the revenue endpoint is shipped, return and Ramadan models are dead | `revenue-by-store-month` only |
| S89 | C# | dotnet-api/LotusApi/Models/RamadanSeasonality.cs:10 | bug | P2 | Ramadan flag typed as long nullable against a Postgres boolean | `public long? IsRamadan` |
| S90 | C# | dotnet-api/LotusApi/Models/FactOrderDetail.cs:16-18 | bug | P2 | Unit price and discount percent typed as long nullable, fractions are lost | `public long? DiscountPct` |

Passing patterns kept as is: parameterized Streamlit queries, pooler first dashboard and R connections, fixed R output paths, single library block in R config, non root API image with healthcheck, real row counts on the ops page, compliant `::TYPE` casts across SQL.
