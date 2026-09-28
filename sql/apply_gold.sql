-- applies gold database objects in dependency order
\ir index/02_gold_indexes.sql
\ir functions/02_gold_guards.sql
\ir functions/03_reconcile_marts.sql
\ir triggers/02_gold_triggers.sql
\ir security/masked_views.sql
\ir security/grants.sql
