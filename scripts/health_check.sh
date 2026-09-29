#!/usr/bin/env bash
# runs shell level health checks then delegates to python for db checks
set -euo pipefail
if [[ -z "${LOTUS_HEALTH_LOGGED:-}" ]]; then
  export LOTUS_HEALTH_LOGGED=1
  mkdir -p "$(dirname "$0")/../logs"
  bash "$0" ${@+"$@"} 2>&1 | tee "$(dirname "$0")/../logs/health.log"
  exit "${PIPESTATUS[0]}"
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi

BOLD="$(tput bold 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"

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

usage() {
  cat <<'EOF'
Usage: scripts/health_check.sh [--quick]

--quick   skip heavy checks (Spark session creation, docker ps)
EOF
}

QUICK=""
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --quick) QUICK="--quick" ;;
  "") ;;
  *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
esac
if (($# > 1)); then echo "Too many arguments" >&2; usage; exit 1; fi

echo "${BOLD}── Health check (shell + python) ──${RESET}"

shim_windows_tools

echo "Disk usage:"
df -h . | tail -n 1 | awk '{print "  " $1 " " $3 "/" $2 " (" $5 " used)"}'
USE_PCT="$(df -h . | tail -n 1 | awk '{print $5}' | tr -d '%')"
if [[ "$USE_PCT" =~ ^[0-9]+$ ]] && (( USE_PCT > 85 )); then
  echo "${YELLOW}Disk usage ${USE_PCT}% >85%${RESET}" >&2
fi

for port in 5432 27017 8080; do
  if command -v ss >/dev/null 2>&1; then
    ss -tlnH 2>/dev/null | grep -q ":$port " && echo "Port $port: ${GREEN}listening${RESET}" || echo "Port $port: not listening"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -tln 2>/dev/null | grep -q ":$port " && echo "Port $port: ${GREEN}listening${RESET}" || echo "Port $port: not listening"
  fi
done

echo ""
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export WSLENV="PYTHONPATH/p${WSLENV:+:$WSLENV}"
if [[ -f scripts/python/health_check.py ]]; then
  if [[ -n "$QUICK" ]]; then
    exec uv run python scripts/python/health_check.py --quick
  else
    exec uv run python scripts/python/health_check.py
  fi
else
  echo "${YELLOW}companion scripts/python/health_check.py not found, shell checks only${RESET}" >&2
fi
