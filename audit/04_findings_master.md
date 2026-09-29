# 04 Findings master and fix plan

Deduped merge of `01`, `02`, `03`. Two static items are corrected by live evidence: S50 (pgcrypto) is invalid because `sha256(bytea)` is a Postgres 17 built in and the masked view returns rows; S20 (employee point in time bypass) is not a bug because null key rows can match no version and keeping them is the documented orphan policy. The `needs_reload` file presence check also softens the retry finding: missing files recover, mid stream resume still does not exist.

## P0, fix or decide now

| ID | Description | Disposition |
|---|---|---|
| F01 | SCD2 stamps every change with the global max order date, backdated changes get wrong windows, same day changes collapse | NEEDS HUMAN DECISION, options in plan item 6 |
| F02 | Two disjoint Postgres role sets (docker vs SQL files); live DB carries both, either path alone breaks | Fix in plan item 3 |
| F03 | `lotus_app` reads unmasked `gold.dim_customers`, confirmed live | Fix in plan item 2 |
| F04 | C# maps the unmasked customer entity, protection is role only | Fix in plan item 12 if tests allow |
| F05 | Docker pipeline test stage cannot import `scripts` or `dashboard`, CI docker job is red, confirmed live | Fix in plan item 1 |

## P1, fix in dependency order

F06 durations always zero plus NULL `ended_at` on failures, mechanism proven (`with` block freezes `now()`). Fix `src/ops/db.py` with `clock_timestamp()` and add `ended_at` to the finish insert.
F07 publish, sql gold apply, and dbt fail under default local roles, confirmed live three times. Point writers at the pipeline role by default plus docs.
F08 `main.py all` never runs GX gates. Add the three GX stages in spec order.
F09 bronze quality hardcodes 42877. Compare against checkpoint sums instead.
F10 silver dedupe keeps first before the null drop while SCD2 keeps last. Null drop first, keep last.
F11 SCD2 duplicate current rows crash with ValueError. Raise a clear corruption error naming the key.
F12 Spark marts never published while quality checks that copy. Point the gold gate at the same question dbt answers, or publish the Spark marts; decision in plan item 7.
F13 default privileges regrant future gold tables to the API reader with no customer exception. Reissue the revoke from the publish path each run.
F14 return rate flags whole orders onto every line. Metric meaning change, human decision.
F15 revenue is gross with no returns netting or discount and tax treatment. Business definition, human decision.
F16 Ramadan has two provenances plus a one day 2024 boundary question. Human decision.
F17 Mongo reader role is read only, so schema evolution detection is unverifiable live, and same count drift would skip reload by code reading. Human decision on detection strategy.
F18 R renders random demo data when the warehouse password is absent. Gate demo mode behind an explicit flag, fail loudly by default.
F19 DAG push task runs `git push` daily from the scheduler and `.git` is not mounted. Drop the git half.
F20 C# has no auth, connection role unverified, only one mart endpoint. Auth is a feature decision; endpoint gap documented.

## P2 and P3

Deterministic Mongo read order; composite dbt tests for cost and orders columns; SLA callback argument shape; shebangs on five shell scripts; report wrapper output dir alignment with `reports/`; sqlglot of dead apply files (document, do not execute through psycopg2); retry attempt history (document, schema change needs a decision); Delta and Databricks narrative against the pandas reality (decision, see below); action SHA pinning (documented, not done); renv lock (documented, R offline here for lock generation through PATH but quarto renders).

## NEEDS HUMAN DECISION list

H1 SCD2 effective dating anchor: keep max order date, stamp run date, or add source change timestamps. Recommendation: keep max order date (current) because run date postdates the data by years and would open validity gaps; record the limitation.
H2 SCD2 hash null versus empty conflation: changing it re versions every customer on the next run. Recommendation: leave hashes stable, document the conflation.
H3 gold `_batch_id`: restoring it changes the gold schema and breaks `to_sql` append until tables are recreated. Recommendation: defer to a migration runbook, document the gap.
H4 revenue and return rate semantics. Recommendation: product decision, not engineering.
H5 Ramadan single source plus the 2024 end day. Recommendation: centralize the existing ranges, confirm 04-08 vs 04-09 with the business.
H6 schedule and SLA: 7 AM IST and 30 minutes against a 215 minute serial path. Recommendation: scheduling decision, engineering implements.
H7 engine narrative: DAG submits to Databricks but the repo holds no notebooks or job definitions and local runs are pandas. Recommendation: confirm where the Databricks jobs live or reword the spec to pandas first with Databricks as a deployment target.
H8 backfill parameterization and parse time Variable reads. Recommendation: accept current rerun semantics explicitly or schedule the refactor.
H9 dashboard auth and R renv. Recommendation:/Minimal auth story plus lockfile when R tooling is on PATH.

## Fix plan in strict dependency order

1. Dockerfile.pipeline test stage: copy `scripts`, `dashboard`, `dags`. Rebuild test target, run container tests.
2. Security: revoke app on unmasked customers in both grant paths, reissue revokes from publish, remove the unmasked C# DbSet if tests pass without it.
3. Ops store: `clock_timestamp()` plus `ended_at` in the finish insert, converge role creation onto the docker init plus pipeline owned apply.
4. Bronze: sort Mongo reads by `_id`.
5. Silver: null drop before dedupe, keep last, plus a unit test for the order.
6. SCD2: explicit corruption error plus a unit test; log H1 and H2.
7. Gold and marts: extra dbt column tests; decision records for H3, H4, H5; quality gate pointed at served marts where cheap.
8. Publish and dbt writer defaults plus DAG task env for the same; `.env.example` and README updated.
9. Quality: GX stages inside `main.py all`; checkpoint relative bronze total; demo mode flag in R.
10. DAG: drop `git push`, fix SLA callback signature, shebangs, report dir alignment, spec diagram docs for the extra task.
11. Monitoring: durations verified nonzero; freshness SLA documented against H6.
12. Downstream: C# type fixes verifiable by `dotnet test`; Streamlit exception logging.
13. CI: extend the docker job to airflow and API images (both build locally already).
14. Docs: ARCHITECTURE corrections (two tables statement, cross references, layout row for `Dockerfile.api`, Mermaid node, mart names, missing scripts, qmd names, schema.yml path), README local role note, CHANGELOG entry.
