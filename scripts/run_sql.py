# applies versioned sql objects to ops and gold in run order
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

SQL_DIR = Path("sql")
LOG_FILE = Path("logs/sql.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("sql")

STEPS_OPS = [
    "ops_schema.sql",
    "index/01_ops_indexes.sql",
    "functions/01_ops_functions.sql",
    "procedures/01_ops_procedures.sql",
    "triggers/01_ops_triggers.sql",
]

STEPS_GOLD = [
    "index/02_gold_indexes.sql",
    "functions/02_gold_guards.sql",
    "functions/03_reconcile_marts.sql",
    "triggers/02_gold_triggers.sql",
    "security/masked_views.sql",
    "security/grants.sql",
]


# opens a warehouse connection for the given prefix
def warehouse_conn(prefix: str) -> psycopg2.extensions.connection:
    short = prefix.split("_")[-1].lower()
    default_user = "lotus_ops" if short == "ops" else "lotus_pipeline"
    return psycopg2.connect(
        dsn=build_dsn(
            os.getenv(f"{prefix}_HOST", "localhost"),
            int(os.getenv(f"{prefix}_PORT", "5432")),
            os.getenv(f"{prefix}_DB", f"lotus_{short}_dev"),
            os.getenv(f"{prefix}_USER", default_user),
            os.getenv(f"{prefix}_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# applies one sql file inside the open transaction
def apply_file(cur: object, name: str) -> None:
    cur.execute(read_sql(SQL_DIR / name))
    log.info("sql applied %s", name)


# true when the gold serving tables exist for reconciliation
def gold_ready(cur: object) -> bool:
    cur.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'gold' AND table_name IN "
        "('fact_orders', 'fact_returns', 'fact_order_details')"
    )
    row = cur.fetchone()
    return row is not None and row[0] == 3


# runs mart reconciliation recording each check in ops
def reconcile(ops_cur: object, run_id: str) -> None:
    with warehouse_conn("POSTGRES_GOLD") as gold:
        gold.autocommit = True
        with gold.cursor() as cur:
            if not gold_ready(cur):
                log.info("sql reconcile skipped, gold tables not published yet")
                return
            cur.execute("SELECT * FROM gold.reconcile_marts()")
            for check_name, success_percent, failed in cur.fetchall():
                ops_cur.execute(
                    "INSERT INTO ops.quality_results "
                    "(run_id, suite_name, success_percent, failed_expectations) "
                    "VALUES (%s, %s, %s, %s)",
                    (run_id, f"mart_{check_name}", float(success_percent), int(failed)),
                )
                log.info(
                    "sql reconcile %s success=%s failed=%s",
                    check_name,
                    success_percent,
                    failed,
                )


# applies the ordered steps for one database
def main() -> None:
    parser = argparse.ArgumentParser(description="versioned sql apply runner")
    parser.add_argument("--db", choices=["ops", "gold", "all"], default="all")
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    log.info("sql start db=%s run=%s", args.db, run_id)
    with warehouse_conn("POSTGRES_OPS") as ops:
        ops.autocommit = True
        with ops.cursor() as cur:
            apply_file(cur, "ops_schema.sql")
            start_run(cur, run_id, "sql_apply")
            try:
                if args.db in ("ops", "all"):
                    for name in STEPS_OPS[1:]:
                        apply_file(cur, name)
                if args.db in ("gold", "all"):
                    with warehouse_conn("POSTGRES_GOLD") as gold:
                        gold.autocommit = True
                        with gold.cursor() as gcur:
                            for name in STEPS_GOLD:
                                apply_file(gcur, name)
                    reconcile(cur, run_id)
                finish_run(cur, run_id, "sql_apply", "success", 0, 0)
            except Exception as exc:
                ops.rollback()
                finish_run(cur, run_id, "sql_apply", "failed", 0, 0, str(exc))
                ops.commit()
                raise
    log.info("sql done db=%s run=%s", args.db, run_id)
    print(f"sql done db={args.db} run={run_id}")


if __name__ == "__main__":
    main()
