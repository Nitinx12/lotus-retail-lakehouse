#!/usr/bin/env bash
# dumps gold and ops databases to timestamped files under data/backups
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi
mkdir -p logs data/backups

KEEP="${BACKUP_KEEP:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"

# dumps one database, prefers the compose postgres when it runs
dump_one() {
  local db="$1" user="$2" password="$3" out="$4"
  if docker compose -f docker/docker-compose.yml ps -q postgres 2>/dev/null | grep -q .; then
    PGPASSWORD="$password" docker compose -f docker/docker-compose.yml exec -T postgres \
      pg_dump -U "$user" -d "$db" -Fc >"$out"
  else
    PGHOST="${POSTGRES_GOLD_HOST:-localhost}" PGPORT="${POSTGRES_GOLD_PORT:-5432}" \
      PGUSER="$user" PGPASSWORD="$password" pg_dump -d "$db" -Fc >"$out"
  fi
  echo "wrote $out"
}

# prunes dumps beyond the retention count for one database
prune() {
  local db="$1" extra
  extra="$(ls -t data/backups/"$db"_*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" || true)"
  if [[ -n "$extra" ]]; then
    echo "$extra" | xargs rm -f
    echo "pruned old $db dumps, keeping $KEEP"
  fi
}

{
  dump_one "${POSTGRES_GOLD_DB:-lotus_gold_dev}" "${POSTGRES_SUPERUSER:-postgres}" \
    "${POSTGRES_SUPERUSER_PASSWORD:-}" "data/backups/gold_${STAMP}.dump"
  if [[ "${POSTGRES_OPS_DB:-}" != "${POSTGRES_GOLD_DB:-lotus_gold_dev}" && -n "${POSTGRES_OPS_DB:-}" ]]; then
    dump_one "$POSTGRES_OPS_DB" "${POSTGRES_SUPERUSER:-postgres}" \
      "${POSTGRES_SUPERUSER_PASSWORD:-}" "data/backups/ops_${STAMP}.dump"
  fi
  prune gold
  prune ops
} 2>&1 | tee logs/backup.log
