#!/usr/bin/env bash
# runs the full local gate: pytest suites plus ruff plus sqlfluff
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
if ! command -v uv >/dev/null 2>&1 && command -v uv.exe >/dev/null 2>&1; then
  uv() { uv.exe "$@"; }
fi
{
  uv run pytest tests/unit tests/smoke tests/dag -q
  uv run ruff check .
  uv run ruff format --check src scripts tests dags dashboard
  uv run sqlfluff lint sql/
  echo "local gate green"
} 2>&1 | tee logs/gate.log
