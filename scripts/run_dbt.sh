#!/usr/bin/env bash
# builds and tests the governed dbt marts on postgres gold
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi
mkdir -p logs
export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-./dbt}"
TARGET="${DBT_TARGET:-dev}"
if ! command -v uv >/dev/null 2>&1 && command -v uv.exe >/dev/null 2>&1; then
  uv() { uv.exe "$@"; }
fi
{
  uv run dbt run --project-dir dbt --target "$TARGET"
  uv run dbt test --project-dir dbt --target "$TARGET"
} 2>&1 | tee logs/dbt.log
