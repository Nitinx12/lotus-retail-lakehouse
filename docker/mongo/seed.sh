#!/usr/bin/env bash
set -euo pipefail

# Import one CSV into a collection named after the file unless it already has documents.
seed_collection() {
  local file=$1 name count drop_flag=""
  name=$(basename "${file}" .csv)
  if [ "${SEED_DROP:-0}" = "1" ]; then
    drop_flag="--drop"
  fi
  count=$(mongosh "${MONGO_URI}" --quiet --eval "db.getCollection('${name}').estimatedDocumentCount()")
  if [ "${count}" -gt 0 ] && [ -z "${drop_flag}" ]; then
    echo "skip ${name}: ${count} documents already loaded"
    return 0
  fi
  mongoimport --uri "${MONGO_URI}" --collection "${name}" \
    --type csv --headerline ${drop_flag} --file "${file}"
}

# Seed every CSV found in /seed and fail loudly when the folder is empty.
main() {
  shopt -s nullglob
  local files=(/seed/*.csv)
  if [ "${#files[@]}" -eq 0 ]; then
    echo "no CSV files found in /seed" >&2
    exit 1
  fi
  for file in "${files[@]}"; do
    seed_collection "${file}"
  done
  echo "seeded ${#files[@]} files"
}

main "$@"
