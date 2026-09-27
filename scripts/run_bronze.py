# copies mongo collections to local bronze parquet with evolution tracking
from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from pymongo import MongoClient

from src.bronze.ingest import (
    detect_new_columns,
    merge_columns,
    normalize_frame,
    schema_of,
)
from src.ops.db import build_dsn, with_batch

load_dotenv()

BRONZE_DIR = Path("data/bronze")
LOG_FILE = Path("logs/bronze.log")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("bronze")


# opens mongo using the environment uri
def mongo_client() -> MongoClient:
    return MongoClient(
        os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )


# opens the ops postgres store
def ops_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=build_dsn(
            os.getenv("POSTGRES_OPS_HOST", "localhost"),
            int(os.getenv("POSTGRES_OPS_PORT", "5432")),
            os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev"),
            os.getenv("POSTGRES_OPS_USER", "lotus_ops"),
            os.getenv("POSTGRES_OPS_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# reads prior parquet column names when a previous load exists
def prior_columns(path: Path) -> list[str]:
    import pyarrow.parquet as pq

    if not path.exists():
        return []
    return list(pq.read_schema(path).names)


# records one pipeline run row
def record_run(
    cur: object,
    run_id: str,
    task: str,
    status: str,
    rows_in: int,
    rows_out: int,
    err: str | None,
) -> None:
    cur.execute(
        "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out, error_message) VALUES (%s, %s, %s, %s, %s, %s)",
        (run_id, task, status, rows_in, rows_out, err),
    )


# lands every mongo collection into bronze parquet
def main() -> None:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    db_name = os.getenv("MONGO_DATABASE") or os.getenv("MONGO_DB", "lotus_retail")
    client = mongo_client()
    db = client[db_name]
    collections = sorted(db.list_collection_names())
    run_id = str(uuid.uuid4())
    started = datetime.now(UTC)
    log.info("bronze start db=%s collections=%s", db_name, collections)
    total = 0
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for name in collections:
                docs = list(db[name].find())
                df = normalize_frame(pd.DataFrame(docs))
                rows_in = len(df)
                path = BRONZE_DIR / f"{name}.parquet"
                prev = prior_columns(path)
                curr_schema = schema_of(df)
                for col in detect_new_columns({c: "" for c in prev}, curr_schema):
                    cur.execute(
                        "INSERT INTO ops.schema_changes (table_name, column_name, change_type) VALUES (%s, %s, %s)",
                        (f"bronze.{name}", col, "add_column"),
                    )
                if prev:
                    df = df.reindex(columns=merge_columns(prev, list(df.columns)))
                df = with_batch(df, run_id)
                df.to_parquet(path, index=False)
                cur.execute(
                    "INSERT INTO ops.extract_checkpoints (source_collection, last_loaded_at, rows_copied, updated_at) VALUES (%s, %s, %s, now()) ON CONFLICT (source_collection) DO UPDATE SET last_loaded_at = EXCLUDED.last_loaded_at, rows_copied = EXCLUDED.rows_copied, updated_at = now()",
                    (name, started, rows_in),
                )
                record_run(
                    cur, run_id, f"bronze_{name}", "success", rows_in, rows_in, None
                )
                total += rows_in
                log.info("bronze %s rows=%s", name, rows_in)
            record_run(cur, run_id, "bronze", "success", total, total, None)
    log.info("bronze done total=%s run=%s", total, run_id)
    print(f"bronze done total={total} run={run_id}")


if __name__ == "__main__":
    main()
