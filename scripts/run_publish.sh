#!/usr/bin/env bash
# publishes gold parquet into the postgres serving schema
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PYTHONPATH:-.}"
mkdir -p logs
uv run python scripts/run_publish.py 2>&1 | tee logs/publish.log
uv run python scripts/run_plpgsql.py --suite gold 2>&1 | tee logs/plpgsql_gold.log
