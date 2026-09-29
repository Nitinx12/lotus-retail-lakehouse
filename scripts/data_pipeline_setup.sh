#!/usr/bin/env bash
# bootstraps a fresh machine from clone to runnable pipeline
set -euo pipefail
if [[ -z "${LOTUS_SETUP_LOGGED:-}" ]]; then
  export LOTUS_SETUP_LOGGED=1
  mkdir -p "$(dirname "$0")/../logs"
  bash "$0" ${@+"$@"} 2>&1 | tee "$(dirname "$0")/../logs/setup.log"
  exit "${PIPESTATUS[0]}"
fi
cd "$(dirname "$0")/.."

SKIP_DOCKER=0
WITH_PIPELINE=0

usage() {
  cat <<'EOF'
Usage: scripts/data_pipeline_setup.sh [options]

Options:
  --skip-docker     install deps and env only, do not start containers
  --with-pipeline   run the full pipeline after setup finishes
  -h | --help       show this help
EOF
}

for arg in ${@+"$@"}; do
  case "$arg" in
    --skip-docker) SKIP_DOCKER=1 ;;
    --with-pipeline) WITH_PIPELINE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 1 ;;
  esac
done

# maps windows exe tools onto plain names when running under WSL
shim_windows_tools() {
  local tool exe
  for tool in uv docker git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      exe="$(command -v "$tool.exe" 2>/dev/null || true)"
      if [[ -n "$exe" ]]; then
        eval "$tool() { \"$exe\" \"\$@\"; }"
      fi
    fi
  done
}

# fails fast with a clear message when a required tool is missing
require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required tool: $1" >&2
    exit 2
  fi
}

# waits until a compose service reports healthy or the timeout hits
wait_healthy() {
  local service="$1" timeout="${2:-180}" waited=0 cid status
  while (( waited < timeout )); do
    cid="$(docker compose -f docker/docker-compose.yml ps -q "$service" 2>/dev/null || true)"
    status="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
    if [[ "$status" == "healthy" ]]; then
      echo "$service is healthy"
      return 0
    fi
    sleep 5
    waited=$((waited + 5))
  done
  echo "timed out waiting for $service to turn healthy" >&2
  return 1
}

shim_windows_tools
require uv
require git
if (( ! SKIP_DOCKER )); then
  require docker
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "created .env from .env.example, review values before continuing"
else
  echo ".env already present, leaving it untouched"
fi

echo "installing python dependencies"
uv sync

if [[ -d .githooks ]]; then
  git config core.hooksPath .githooks
  echo "git hooks wired to .githooks"
fi

mkdir -p logs data/raw reports

if (( ! SKIP_DOCKER )); then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  echo "starting postgres, mongo, and the pooler"
  docker compose -f docker/docker-compose.yml up -d postgres mongo pgbouncer
  wait_healthy postgres
  wait_healthy mongo
  wait_healthy pgbouncer
fi

echo "bootstrapping postgres roles and the ops schema"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export WSLENV="PYTHONPATH/p${WSLENV:+:$WSLENV}"
uv run python scripts/init_ops.py

if (( WITH_PIPELINE )); then
  echo "running the full pipeline"
  uv run python main.py all
else
  echo "setup done, next: uv run python main.py all"
fi
