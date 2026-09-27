# builds cleaned silver parquet from bronze
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PYTHONPATH:-.}"
mkdir -p logs
uv run python scripts/run_silver.py 2>&1 | tee logs/silver.log
uv run python scripts/run_scd2.py 2>&1 | tee logs/scd2.log
