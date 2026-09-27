# runs plpgsql quality loops and records the outcome in ops
from __future__ import annotations

import argparse
import logging
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn, finish_run, read_sql, start_run

load_dotenv()

SQL_DIR = Path("sql/plpgsql_checks")
LOG_FILE = Path("logs/plpgsql.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("plpgsql")


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


# opens the gold serving warehouse
def gold_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=build_dsn(
            os.getenv("POSTGRES_GOLD_HOST", "localhost"),
            int(os.getenv("POSTGRES_GOLD_PORT", "5432")),
            os.getenv("POSTGRES_GOLD_DB", "lotus_gold_dev"),
            os.getenv("POSTGRES_GOLD_USER", "lotus_app"),
            os.getenv("POSTGRES_GOLD_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# runs the pre ingest readiness loop against ops
def run_source(cur: object) -> None:
    cur.execute(read_sql(SQL_DIR / "source_checks.sql"))


# runs the post publish gold loop against the serving schema
def run_gold() -> None:
    with gold_conn() as gold:
        gold.autocommit = True
        with gold.cursor() as cur:
            cur.execute(read_sql(SQL_DIR / "gold_checks.sql"))


# runs one suite and records quality and run rows
def main() -> None:
    parser = argparse.ArgumentParser(description="plpgsql quality loop runner")
    parser.add_argument("--suite", choices=["source", "gold"], required=True)
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    task = f"plpgsql_{args.suite}"
    log.info("plpgsql start suite=%s run=%s", args.suite, run_id)
    with ops_conn() as ops:
        ops.autocommit = True
        with ops.cursor() as cur:
            start_run(cur, run_id, task)
            try:
                if args.suite == "source":
                    run_source(cur)
                else:
                    run_gold()
                cur.execute(
                    "INSERT INTO ops.quality_results "
                    "(run_id, suite_name, success_percent, failed_expectations) "
                    "VALUES (%s, %s, %s, %s)",
                    (run_id, task, 100.0, 0),
                )
                finish_run(cur, run_id, task, "success", 0, 0)
            except Exception as exc:
                ops.rollback()
                cur.execute(
                    "INSERT INTO ops.quality_results "
                    "(run_id, suite_name, success_percent, failed_expectations) "
                    "VALUES (%s, %s, %s, %s)",
                    (run_id, task, 0.0, 1),
                )
                finish_run(cur, run_id, task, "failed", 0, 1, str(exc))
                ops.commit()
                raise
    log.info("plpgsql done suite=%s run=%s", args.suite, run_id)
    print(f"plpgsql done suite={args.suite} run={run_id}")


if __name__ == "__main__":
    main()
