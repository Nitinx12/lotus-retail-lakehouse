#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo "missing .env, copy it from .env.example first" >&2
  exit 2
fi
set -a
source .env
set +a
if [ "$#" -eq 0 ]; then
  set -- up --build
fi
exec docker compose -f docker/docker-compose.yml "$@"
