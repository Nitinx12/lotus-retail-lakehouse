# lands mongo collections into bronze parquet
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PYTHONPATH:-.}"
mkdir -p logs
uv run python scripts/run_plpgsql.py --suite source 2>&1 | tee logs/plpgsql_source.log
uv run python scripts/run_bronze.py 2>&1 | tee logs/bronze.log
