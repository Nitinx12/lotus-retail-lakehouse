# versions type 2 dimensions from cleaned silver tables
from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn
from src.silver.scd2 import apply_scd2

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
    out = apply_scd2(current, frame, natural_key, tracked, sk_col, start)
    out.to_parquet(path, index=False)
    versions = int((~out["is_current"]).sum())
    cur.execute(
        "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out) VALUES (%s, %s, %s, %s, %s)",
        (run_id, f"scd2_{table}", "success", len(frame), len(out)),
    )
    log.info("scd2 %s rows=%s versions_closed=%s", table, len(out), versions)
    return out


# versions both type 2 dimensions
def main() -> None:
    run_id = str(uuid.uuid4())
    orders = pd.read_parquet(SILVER_DIR / "fact_orders.parquet")
    anchor_date = pd.to_datetime(orders["order_date"]).min().date().isoformat()
    change_date = datetime.now(UTC).date().isoformat()
    log.info("scd2 start run=%s anchor=%s", run_id, anchor_date)
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            customers = pd.read_parquet(SILVER_DIR / "dim_customers.parquet")
            version_dim(
                cur,
                run_id,
                customers,
                "dim_customers",
                "customer_id",
                ["region", "loyalty_tier", "city"],
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
                ["store_id", "role"],
                "employee_sk",
                anchor_date,
                change_date,
            )
            cur.execute(
                "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out) VALUES (%s, %s, %s, %s, %s)",
                (
                    run_id,
                    "scd2",
                    "success",
                    len(customers) + len(employees),
                    len(customers) + len(employees),
                ),
            )
    print(f"scd2 done run={run_id}")


if __name__ == "__main__":
    main()
