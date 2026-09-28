#!/usr/bin/env bash
set -euo pipefail

# Print a UTC timestamped message to stderr.
log() {
  printf '%s [entrypoint] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2
}

# Exit 64 when any variable named in REQUIRED_ENV is unset or empty.
check_required_env() {
  local name missing=0
  for name in ${REQUIRED_ENV:-}; do
    if [ -z "${!name:-}" ]; then
      log "missing required env var ${name}"
      missing=1
    fi
  done
  if [ "${missing}" -ne 0 ]; then
    exit 64
  fi
}

# Block until host:port accepts TCP connections, exit 69 after WAIT_TIMEOUT seconds.
wait_for_tcp() {
  local target=$1 host port waited=0
  host=${target%%:*}
  port=${target##*:}
  until (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; do
    if [ "${waited}" -ge "${WAIT_TIMEOUT:-90}" ]; then
      log "timed out waiting for ${target}"
      exit 69
    fi
    sleep 2
    waited=$((waited + 2))
  done
  log "${target} is reachable"
}

# Confirm the libpq PG* login works, which proves the init scripts created the role.
check_postgres() {
  if ! psql -Atqc 'select 1' >/dev/null 2>&1; then
    log "postgres login failed for ${PGUSER:-unknown}@${PGHOST:-unknown}:${PGPORT:-5432}/${PGDATABASE:-unknown}"
    exit 70
  fi
  log "postgres login ok as ${PGUSER}"
}

# Export a stage scoped, dated LOG_FILE for the application to write to.
setup_logging() {
  local dir=${LOG_DIR:-/app/logs} stage=${PIPELINE_STAGE:-pipeline}
  mkdir -p "${dir}"
  export LOG_FILE="${dir}/${stage}_$(date -u +%Y%m%d).log"
  log "log file ${LOG_FILE}"
}

# Run checks then hand PID 1 to the requested command.
main() {
  if [ "${1:-}" = "bash" ] || [ "${1:-}" = "sh" ]; then
    exec "$@"
  fi
  check_required_env
  for target in ${WAIT_FOR:-}; do
    wait_for_tcp "${target}"
  done
  if [ "${CHECK_POSTGRES:-0}" = "1" ]; then
    check_postgres
  fi
  setup_logging
  log "starting: $*"
  exec "$@"
}

main "$@"
