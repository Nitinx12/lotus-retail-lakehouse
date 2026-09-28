# SQL Layer Run Order

All files are idempotent, reruns are safe. Two databases are in play:
`ops` holds monitoring state, `gold` holds serving tables. Apply ops
first, then gold. `plpgsql_checks` run per suite through
`scripts/run_plpgsql.py`, `analysis` holds ad hoc reads for analysts.

## Ops database

Run with `psql -f sql/apply_ops.sql` or `uv run python main.py sql-ops`:

| Order | File | Purpose |
|---|---|---|
| 1 | `ops_schema.sql` | Schemas plus `pipeline_runs`, `quality_results`, `extract_checkpoints`, `schema_changes`, `alerts` |
| 2 | `index/01_ops_indexes.sql` | Lookup indexes for the ops page queries |
| 3 | `functions/01_ops_functions.sql` | Alert writer, timestamp stamper, failure and drop trigger functions |
| 4 | `procedures/01_ops_procedures.sql` | Stuck run closer and history purger with loops |
| 5 | `triggers/01_ops_triggers.sql` | Alert and timestamp triggers, need the functions first |

## Gold database

Run with `psql -f sql/apply_gold.sql` or `uv run python main.py sql-gold`:

| Order | File | Purpose |
|---|---|---|
| 1 | `index/02_gold_indexes.sql` | Serving indexes, skips tables not yet published |
| 2 | `functions/02_gold_guards.sql` | Row guards rejecting future dates and negative amounts |
| 3 | `functions/03_reconcile_marts.sql` | Mart versus base reconciliation looping over checks |
| 4 | `triggers/02_gold_triggers.sql` | Guard triggers, need the guard functions first |
| 5 | `security/masked_views.sql` | Masked customer view for general BI roles |
| 6 | `security/roles.sql` | Least privilege roles, created only when missing |
| 7 | `security/grants.sql` | PII grants, need the roles and the view first |

`security/roles.sql` also runs once from `scripts/init_ops.py` against the
maintenance database since roles are cluster wide.

`scripts/run_publish.py` re applies the gold indexes and guard triggers
after every publish, so serving objects attach even when `sql-gold` ran
before the first publish created the tables.
