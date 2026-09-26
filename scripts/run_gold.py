# builds gold star schema and marts from silver
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.gold.build import (
    build_fact_orders,
    build_fact_returns,
    mart_ramadan_seasonality,
    mart_return_rate_by_product,
    mart_revenue_by_store_month,
)
from src.ops.db import build_dsn

load_dotenv()

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")
LOG_FILE = Path("logs/gold.log")
GOLD_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("gold")


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


# writes one frame and records its run row
def land(cur: object, run_id: str, name: str, df: pd.DataFrame, rows_in: int) -> None:
    path = GOLD_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    cur.execute(
        "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out) VALUES (%s, %s, %s, %s, %s)",
        (run_id, f"gold_{name}", "success", rows_in, len(df)),
    )
    log.info("gold %s rows=%s", name, len(df))


# builds every gold table and mart
def main() -> None:
    run_id = str(uuid.uuid4())
    log.info("gold start run=%s", run_id)
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for name in ("dim_date", "dim_stores", "dim_products"):
                df = pd.read_parquet(SILVER_DIR / f"{name}.parquet")
                land(cur, run_id, name, df, len(df))
            for name in ("dim_customers", "dim_employees"):
                df = pd.read_parquet(SILVER_DIR / f"{name}_scd2.parquet")
                land(cur, run_id, name, df, len(df))
            orders = pd.read_parquet(SILVER_DIR / "fact_orders.parquet")
            customers = pd.read_parquet(GOLD_DIR / "dim_customers.parquet")
            employees = pd.read_parquet(GOLD_DIR / "dim_employees.parquet")
            facts = build_fact_orders(orders, customers, employees)
            land(cur, run_id, "fact_orders", facts, len(orders))
            returns = pd.read_parquet(SILVER_DIR / "fact_returns.parquet")
            fact_returns = build_fact_returns(returns, facts)
            land(cur, run_id, "fact_returns", fact_returns, len(returns))
            details = pd.read_parquet(SILVER_DIR / "fact_order_details.parquet")
            land(cur, run_id, "fact_order_details", details, len(details))
            revenue = mart_revenue_by_store_month(facts)
            land(cur, run_id, "mart_revenue_by_store_month", revenue, len(facts))
            rates = mart_return_rate_by_product(details, fact_returns["order_id"])
            land(cur, run_id, "mart_return_rate_by_product", rates, len(details))
            ramadan = mart_ramadan_seasonality(
                facts, pd.read_parquet(GOLD_DIR / "dim_date.parquet")
            )
            land(cur, run_id, "mart_ramadan_seasonality", ramadan, len(facts))
            cur.execute(
                "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out) VALUES (%s, %s, %s, %s, %s)",
                (run_id, "gold", "success", len(orders), len(facts)),
            )
    print(f"gold done run={run_id}")


if __name__ == "__main__":
    main()
