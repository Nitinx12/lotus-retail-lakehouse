# 06 Final report

Branch `audit/20260929`, 20 fix commits on top of `main` at `296a7f8`. One pre existing uncommitted edit (`.dockerignore` plus one ignore line) was left untouched. All work used local Docker Postgres and Mongo plus local parquet; no cloud, Vault, Slack, PagerDuty, or registry was touched. Two full clean rebuilds were run, the second from wiped volumes with Mongo restored from a dump backup.

## 1. Executive summary

The pipeline runs green end to end and reconciles exactly across every layer, but the audit found one exposed PII path, one red CI image, broken local defaults for every writer, zeroed monitoring durations, and Gates that never ran in the default flow. All of that is fixed and verified live, including a from scratch volume wipe rebuild. What remains open is almost entirely business decisions: revenue and return rate semantics, Ramadan sourcing, SCD2 dating anchors, the schedule and SLA numbers, and whether Gold facts should carry customer PII. Four static suspicions were disproved by live evidence and are recorded as such rather than fixed.

## 2. Scorecard

| Area | Status | Note |
|---|---|---|
| Ingest | PASS | Deterministic order added; checkpoint limits documented |
| Silver | PASS | Dedupe order fixed with test; counts unchanged |
| SCD2 | PARTIAL | Happy path verified; anchor and hash semantics need a human ruling |
| Gold | PASS | Reconciles exactly; batch lineage deferred as a migration decision |
| dbt | PASS | 17 of 17 tests; served mart cross checked by the quality gate |
| Postgres | PASS | Revokes verified; fresh init converges; roles out of the per run path |
| DAG | PARTIAL | Push and SLA callback fixed; schedule and templating need rulings; no runtime here |
| Quality | PASS | Gates run in the default flow; totals checkpoint relative |
| Monitoring | PARTIAL | Durations real now; freshness SLA mismatch needs a ruling |
| Security | PARTIAL | App PII closed live; fact level PII columns need a masking decision |
| Docker and CI | PASS | All five images build; test stage fixed; job extended |
| R and LaTeX | PASS | Demo gate plus live render verified; wrappers aligned |
| Streamlit | PASS | Healthy; queries parameterized; error path already logged |
| C# API | PASS | PII entity removed; build and tests green |

## 3. Findings disposition

FIXED with commit: F05 test stage, F03 and F13 app PII plus publish revokes, F06 durations, S04 read order, F10 dedupe order, F11 SCD2 corruption error, S32 dbt tests, F07 writer defaults, F02 role convergence plus gold DSN, F08 gates in `all`, F09 checkpoint totals, F12 served mart check, F18 demo gate plus pool resolution, S72 and S74 report layout plus pdf gate, F19 push task, S66 SLA callback, S70 shebangs, F04 API PII entity, S79 CI images, S28 S64 S71 S77 docs, S49 masked view convergence found during final verification.

INVALID after live evidence: S50 pgcrypto, S20 employee bypass, S81 error swallow, S89 and S90 C# types.

NEEDS HUMAN DECISION: H1 SCD2 anchor, H2 hash conflation, H3 gold batch lineage, H4 revenue and return semantics, H5 Ramadan source and 2024 end day, H6 schedule and SLA, H7 engine narrative, H8 backfill semantics, H9 dashboard auth and R lockfile, F21 fact level PII columns.

WONTFIX with reason: PostgresOperator import (works, change unverifiable here), action SHA pinning (churn, warning only), publish matrix release scope (release decision), R default output (covered by env).

## 4. Unverified and what would verify it

Airflow runtime (no scheduler here): needs the compose airflow profile with metadata DB to run `tasks test` and `dags test`, plus real Connections for the writer roles. Alert delivery beyond the database: needs a Slack webhook and PagerDuty key in staging. Registry push: needs Docker Hub and GHCR tokens. Databricks semantics (MERGE, OPTIMIZE, Unity Catalog): needs a workspace and the job definitions, which are absent from the repo. Schema evolution detection: needs a writable source role. R lockfile: needs R tooling on PATH.

## 5. Before and after evidence

Idempotency: before, reruns rewrote every file; after analysis, business content is byte identical across reruns excluding run tags (three consecutive runs compared, plus a fresh database pair with zero diff).

Reconciliation: bronze 42,877 in, silver 42,827 out, gold facts 12,000 orders at revenue 45,350,979.0, dbt mart 540 rows at the same revenue to the decimal, orphans zero on all paths, before and after the fixes.

SCD2 scenario: controlled region change closes exactly one row and opens exactly one row, one current row per key, 12,000 facts join to 12,000 rows with zero duplicates and zero null keys, rerun adds zero rows.

Security: before, the app role read unmasked customers; after, denied on the base table and allowed on the masked view, on both the old and the rebuilt database. API reader denied writes and unmasked reads throughout.

Durations: before, every ops duration read 0.0 with NULL on failures; after, publish rows read 16.4 s and 18.5 s on the clean database.

Writers: before, sql gold, publish, and dbt run failed under default local roles; after, all pass with no overrides, twice, including from wiped volumes.

## 6. Remaining risks in priority order

1. Decide F21 fact PII before the next data share; the dimension fix alone leaves name, phone, and mail readable through facts.
2. Settle H4 and H5 metric definitions; two builders still agree by hand, now watched by the served mart check.
3. Settle H6 schedule and SLA; the DAG cannot meet 7 AM IST as configured.
4. Settle H1 SCD2 anchor and record it next to the code; backdated changes stay approximate.
5. Wire Airflow container credentials for the writer roles or the scheduled DAG repeats the failures fixed locally.
6. Add dashboard auth (H9) if the URL leaves the team.
7. Resolve H7 engine narrative so Databricks expectations match a runnable definition.
