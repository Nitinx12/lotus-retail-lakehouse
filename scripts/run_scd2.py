# versions type 2 dimensions from cleaned silver tables
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn, finish_run, start_run, with_batch
from src.silver.scd2 import CUSTOMER_TRACKED, EMPLOYEE_TRACKED, apply_scd2

load_dotenv()

SILVER_DIR = Path("data/silver")
LOG_FILE = Path("logs/scd2.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("scd2")


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


# versions one dimension and records its run row
def version_dim(
    cur: object,
    run_id: str,
    frame: pd.DataFrame,
    table: str,
    natural_key: str,
    tracked: list[str],
    sk_col: str,
    anchor_date: str,
    change_date: str,
) -> pd.DataFrame:
    path = SILVER_DIR / f"{table}_scd2.parquet"
    current = pd.read_parquet(path) if path.exists() else None
    start = anchor_date if current is None else change_date
    task = f"scd2_{table}"
    start_run(cur, run_id, task)
    out = apply_scd2(
        current, with_batch(frame, run_id), natural_key, tracked, sk_col, start
    )
    out.to_parquet(path, index=False)
    versions = int((~out["is_current"]).sum())
    finish_run(cur, run_id, task, "success", len(frame), len(out))
    log.info("scd2 %s rows=%s versions_closed=%s", table, len(out), versions)
    return out


# versions both type 2 dimensions
def main() -> None:
    run_id = str(uuid.uuid4())
    orders = pd.read_parquet(SILVER_DIR / "fact_orders.parquet")
    parsed = pd.to_datetime(orders["order_date"])
    anchor_date = parsed.min().date().isoformat()
    change_date = parsed.max().date().isoformat()
    log.info("scd2 start run=%s anchor=%s", run_id, anchor_date)
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "scd2")
            try:
                customers = pd.read_parquet(SILVER_DIR / "dim_customers.parquet")
                version_dim(
                    cur,
                    run_id,
                    customers,
                    "dim_customers",
                    "customer_id",
                    CUSTOMER_TRACKED,
                    "customer_sk",
                    anchor_date,
                    change_date,
                )
                employees = pd.read_parquet(SILVER_DIR / "dim_employees.parquet")
                version_dim(
                    cur,
                    run_id,
                    employees,
                    "dim_employees",
                    "employee_id",
                    EMPLOYEE_TRACKED,
                    "employee_sk",
                    anchor_date,
                    change_date,
                )
                finish_run(
                    cur,
                    run_id,
                    "scd2",
                    "success",
                    len(customers) + len(employees),
                    len(customers) + len(employees),
                )
            except Exception as exc:
                finish_run(cur, run_id, "scd2", "failed", 0, 0, str(exc))
                conn.commit()
                raise
    print(f"scd2 done run={run_id}")


if __name__ == "__main__":
    main()
