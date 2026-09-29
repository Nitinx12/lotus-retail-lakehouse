#!/usr/bin/env bash
# builds gold star schema and marts from silver
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
export PYTHONPATH="${PYTHONPATH:-.}"
mkdir -p logs
uv run python scripts/run_gold.py 2>&1 | tee logs/gold.log
