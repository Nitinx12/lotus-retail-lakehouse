#!/usr/bin/env bash
set -euo pipefail
mongosh --quiet --eval '
const dbName = "'"${MONGO_DB:-lotus_retail}"'";
db.getSiblingDB(dbName).createUser({
  user: "'"${MONGO_READER_USER:-lotus_reader}"'",
  pwd: "'"${MONGO_READER_PASSWORD:?set MONGO_READER_PASSWORD}"'",
  roles: [{ role: "read", db: dbName }],
});'
