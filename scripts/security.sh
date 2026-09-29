#!/usr/bin/env bash
# scans for leaked secrets then delegates to python for pattern checks
set -euo pipefail
if [[ -z "${LOTUS_SECURITY_LOGGED:-}" ]]; then
  export LOTUS_SECURITY_LOGGED=1
  mkdir -p "$(dirname "$0")/../logs"
  bash "$0" ${@+"$@"} 2>&1 | tee "$(dirname "$0")/../logs/security.log"
  exit "${PIPESTATUS[0]}"
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi

BOLD="$(tput bold 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
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

echo "${BOLD}── Security check ──${RESET}"

shim_windows_tools

if command -v gitleaks >/dev/null 2>&1; then
  echo "Running gitleaks..."
  if leak_out=$(gitleaks detect --no-git -v 2>&1); then
    printf '%s\n' "$leak_out" | tail -n 20
    echo "${GREEN}gitleaks: no leaks detected${RESET}"
  else
    printf '%s\n' "$leak_out" | tail -n 20 >&2
    echo "${RED}gitleaks found potential leaks, see above${RESET}" >&2
    exit 1
  fi
else
  echo "${YELLOW}gitleaks not installed, skipping${RESET}"
fi

if git ls-files --cached | grep -qxF ".env" 2>/dev/null; then
  echo "${RED}.env is tracked by git, should be ignored!${RESET}" >&2
  exit 1
else
  echo "${GREEN}.env not tracked${RESET}"
fi

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export WSLENV="PYTHONPATH/p${WSLENV:+:$WSLENV}"
if [[ -f scripts/python/security_check.py ]]; then
  exec uv run python scripts/python/security_check.py
else
  echo "${YELLOW}companion scripts/python/security_check.py not found, shell checks only${RESET}" >&2
fi
