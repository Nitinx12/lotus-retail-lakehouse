# runs bronze silver and gold quality suites into ops
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PYTHONPATH:-.}"
mkdir -p logs
uv run python scripts/run_quality.py 2>&1 | tee logs/quality.log
