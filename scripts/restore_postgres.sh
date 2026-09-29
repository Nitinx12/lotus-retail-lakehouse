#!/usr/bin/env bash
# restores one custom format dump into postgres, see runbooks/restore.md
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi
mkdir -p logs

usage() {
  cat <<'EOF'
Usage: scripts/restore_postgres.sh <dumpfile> [dbname]

Restores a data/backups dump with --clean --if-exists, dropping objects
before recreating them. Defaults to POSTGRES_GOLD_DB from .env.
EOF
}

if [[ $# -lt 1 ]]; then usage; exit 2; fi
DUMP="$1"
DB="${2:-${POSTGRES_GOLD_DB:-lotus_gold_dev}}"
USER="${POSTGRES_SUPERUSER:-postgres}"
PASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-}"
if [[ ! -f "$DUMP" ]]; then echo "dump not found: $DUMP" >&2; exit 2; fi

{
  echo "restoring $DUMP into $DB"
  if docker compose -f docker/docker-compose.yml ps -q postgres 2>/dev/null | grep -q .; then
    PGPASSWORD="$PASSWORD" docker compose -f docker/docker-compose.yml exec -T postgres \
      pg_restore -U "$USER" -d "$DB" --clean --if-exists <"$DUMP"
  else
    PGHOST="${POSTGRES_GOLD_HOST:-localhost}" PGPORT="${POSTGRES_GOLD_PORT:-5432}" \
      PGUSER="$USER" PGPASSWORD="$PASSWORD" pg_restore -d "$DB" --clean --if-exists "$DUMP"
  fi
  echo "restore done"
} 2>&1 | tee logs/restore.log
