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
from src.ops.db import build_dsn, finish_run, start_run, with_batch

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
    finish_run(cur, run_id, task, status, rows_in, rows_out, err)


# decides whether a collection needs a fresh read from mongo
def needs_reload(
    checkpoint_rows: int | None, live_count: int, have_parquet: bool
) -> bool:
    if checkpoint_rows is None or not have_parquet:
        return True
    return live_count != checkpoint_rows


# lists added columns only when a previous load exists to compare against
def columns_to_log(prev: list[str], curr_schema: dict[str, str]) -> list[str]:
    if not prev:
        return []
    return detect_new_columns({c: "" for c in prev}, curr_schema)


# reads the stored row count for one collection if a checkpoint exists
def read_checkpoint(cur: object, name: str) -> int | None:
    cur.execute(
        "SELECT rows_copied FROM ops.extract_checkpoints WHERE source_collection = %s",
        (name,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


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
            start_run(cur, run_id, "bronze")
            try:
                for name in collections:
                    task = f"bronze_{name}"
                    path = BRONZE_DIR / f"{name}.parquet"
                    live = db[name].count_documents({})
                    if not needs_reload(
                        read_checkpoint(cur, name), live, path.exists()
                    ):
                        record_run(cur, run_id, task, "skipped", live, live, None)
                        total += live
                        log.info("bronze %s skipped rows=%s", name, live)
                        continue
                    start_run(cur, run_id, task)
                    docs = list(db[name].find())
                    last_id = str(docs[-1].get("_id")) if docs else None
                    df = normalize_frame(pd.DataFrame(docs))
                    rows_in = len(df)
                    prev = prior_columns(path)
                    curr_schema = schema_of(df)
                    for col in columns_to_log(prev, curr_schema):
                        cur.execute(
                            "INSERT INTO ops.schema_changes (table_name, column_name, change_type) VALUES (%s, %s, %s)",
                            (f"bronze.{name}", col, "add_column"),
                        )
                    if prev:
                        df = df.reindex(columns=merge_columns(prev, list(df.columns)))
                    df = with_batch(df, run_id)
                    df.to_parquet(path, index=False)
                    cur.execute(
                        "INSERT INTO ops.extract_checkpoints (source_collection, last_object_id, last_loaded_at, rows_copied, updated_at) VALUES (%s, %s, %s, %s, now()) ON CONFLICT (source_collection) DO UPDATE SET last_object_id = EXCLUDED.last_object_id, last_loaded_at = EXCLUDED.last_loaded_at, rows_copied = EXCLUDED.rows_copied, updated_at = now()",
                        (name, last_id, started, rows_in),
                    )
                    record_run(cur, run_id, task, "success", rows_in, rows_in, None)
                    total += rows_in
                    log.info("bronze %s rows=%s", name, rows_in)
                record_run(cur, run_id, "bronze", "success", total, total, None)
            except Exception as exc:
                record_run(cur, run_id, "bronze", "failed", total, total, str(exc))
                conn.commit()
                raise
    log.info("bronze done total=%s run=%s", total, run_id)
    print(f"bronze done total={total} run={run_id}")


if __name__ == "__main__":
    main()
