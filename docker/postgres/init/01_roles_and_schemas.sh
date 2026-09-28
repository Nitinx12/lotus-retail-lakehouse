#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v dbname="$POSTGRES_DB" \
  -v app_pw="$LOTUS_APP_PASSWORD" \
  -v pipeline_pw="$LOTUS_PIPELINE_PASSWORD" \
  -v api_pw="$LOTUS_API_READER_PASSWORD" \
  -v airflow_pw="$AIRFLOW_DB_PASSWORD" <<'SQL'
CREATE ROLE lotus_pipeline LOGIN PASSWORD :'pipeline_pw';
CREATE ROLE lotus_app LOGIN PASSWORD :'app_pw';
CREATE ROLE lotus_api_reader LOGIN PASSWORD :'api_pw';
CREATE ROLE pii_reader NOLOGIN;
CREATE ROLE airflow_meta LOGIN PASSWORD :'airflow_pw';

REVOKE CONNECT ON DATABASE :"dbname" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"dbname" TO lotus_pipeline, lotus_app, lotus_api_reader, pii_reader;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA IF NOT EXISTS gold AUTHORIZATION lotus_pipeline;
CREATE SCHEMA IF NOT EXISTS marts AUTHORIZATION lotus_pipeline;
CREATE SCHEMA IF NOT EXISTS ops AUTHORIZATION lotus_pipeline;

GRANT USAGE ON SCHEMA gold, marts, ops TO lotus_app;
GRANT USAGE ON SCHEMA gold, marts TO lotus_api_reader;
GRANT CREATE ON DATABASE :"dbname" TO lotus_pipeline;
GRANT USAGE ON SCHEMA gold TO pii_reader;
ALTER ROLE lotus_pipeline SET search_path = gold, marts, ops, public;

CREATE DATABASE airflow OWNER airflow_meta;
SQL
