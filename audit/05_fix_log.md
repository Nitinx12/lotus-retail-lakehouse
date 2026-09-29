# 05 Fix log

One logical fix per commit on `audit/20260929`. Each entry records verification. Human decision items H1 to H9 from `04` were not changed in code.

## Commits

1. `5a39ec2` docker test stage copies `scripts` and `dashboard`. Before: container run gave 4 collection errors. After: `54 passed`. Matches F05.
2. `5b2ff3e` security revokes on unmasked customers plus publish reissue. Before: app role selected unmasked PII live. After: denied on base, allowed on masked view; unit 54 pass; sqlfluff clean. Matches F03 and F13.
3. `2e90784` ops durations via statement timestamps plus `ended_at` on insert. Before: all durations zero, failures NULL. After: probe shows 1.08 s and 2.08 s child durations; unit 54 pass. Matches F06.
4. `aaa2fd5` bronze reads sort by document id. Bronze rerun still skips cleanly at 42,877; unit bronze 6 pass. Matches S04.
5. `5e444e0` silver null drop before dedupe keeping last, plus a unit test for junk first and last wins. Counts unchanged (42,877 in, 42,827 out), quality 100 percent, unit plus smoke 56 pass. Matches F10.
6. `fbb799a` SCD2 duplicate current rows raise a naming error, plus a unit test. SCD2 file 9 pass, ruff clean. Matches F11.
7. `a46c0fa` dbt not null tests on cost, orders, and return counts. `dbt test` 17 of 17 pass. Matches S32.
8. `10ba750` writers default to the pipeline role. Before: sql gold, publish, and dbt run failed live under the app role. After: all pass with no overrides; app grant gone after publish; unit 56 pass. Matches F07.
9. `f57b815` init converges bootstrap roles and fixes the gold DSN host. `init_ops.py` reruns cleanly end to end; revokes intact; unit 56 pass. Matches F02 and S30.
10. `6114754` GX suites inside `main.py all`. Full run exits 0 end to end. Matches F08.
11. `8bbe75c` bronze total against checkpoints. Quality 100 percent; gates 6 pass. Matches F09.
12. `03f6264` served mart cross check in quality. Quality 100 percent with the new check green; gates pass; ruff clean after narrowing to `psycopg2.Error`. Matches F12.
13. `ebac735` R refuses demo data without opt in. Render without creds fails with the refusal message; render with pool creds succeeds on live data. Matches F18.
14. `f62a9a6` R reader resolution through pool vars first plus example entries. Covered by the same renders. Part of F07.
15. `9faf857` report outputs under `reports/` plus the DAG pdf gate. Wrapper run exits 0 with fresh analysis HTML and report PDF; gate passes. Matches S72 and S74.
16. `8d16b36` DAG drops git push and shapes SLA alerts. Stub import holds, DAG tests 6 pass 1 skip. Matches F19 and S66.
17. `11f9e47` shebangs on five wrappers. `bash -n` passes on all five; full wrapper execution is impossible in this Git Bash (no uv or python on PATH), recorded as a limit. Matches S70.
18. `7decbc1` API drops the unmasked customer entity. `dotnet build` 0 errors, `dotnet test` 2 of 2 pass. Matches F04. Amended once to include the context edit in the same commit; nothing pushed.
19. `ef2d931` CI docker job builds airflow and API images. All five image builds were run locally already. Matches S79.
20. `68b612f` docs corrections plus README roles plus CHANGELOG. Matches S28 S64 S71 S77.

## Corrections during verification

S50 missing pgcrypto is invalid: `sha256(bytea)` is a Postgres 17 built in and the masked view returns rows. S20 employee point in time bypass is not a bug: null key rows match no version, keeping them is the orphan policy. S81 Streamlit error swallow is overstated: the query helper logs the exception and shows an error. S89 and S90 C# type findings are invalid: Postgres holds bigint for the Ramadan flag and integer prices, so `long?` is correct. F13 needed no extra commit, it rode with the security commit.

## Reverted mishap

A PowerShell rewrite of the five shell wrappers corrupted their encoding; reverted via git within the same session and reapplied byte exact with Python. Local `.env` picked up CRLF twice from PowerShell writes; converted back to LF twice and verified parsing plus connections. No repo file carries the damage; `.env` is gitignored.

## Open

H1 SCD2 date anchor, H2 hash conflation, H3 gold batch lineage, H4 revenue and return semantics, H5 Ramadan source and the 2024 end day, H6 schedule and SLA numbers, H7 engine narrative, H8 backfill parameterization, H9 dashboard auth and R lockfile. New finding F21: `gold.fact_orders` carries customer PII columns (name, phone, mail) readable by the app role, needs the same masking decision as the dimension.
