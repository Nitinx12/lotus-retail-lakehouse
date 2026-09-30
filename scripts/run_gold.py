# builds gold star schema and marts from silver
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pyspark import StorageLevel
from pyspark.sql import DataFrame

from src.gold.build import (
    build_fact_orders,
    build_fact_returns,
    mart_ramadan_seasonality,
    mart_return_rate_by_product,
    mart_revenue_by_store_month,
)
from src.ops.db import build_dsn, finish_run, start_run, with_batch
from src.spark.session import get_spark

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
def land(cur: object, run_id: str, name: str, df: DataFrame, rows_in: int) -> int:
    task = f"gold_{name}"
    start_run(cur, run_id, task)
    path = str(GOLD_DIR / f"{name}.parquet")
    stamped = with_batch(df, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    rows_out = stamped.count()
    stamped.write.mode("overwrite").parquet(path)
    stamped.unpersist()
    finish_run(cur, run_id, task, "success", rows_in, rows_out)
    log.info("gold %s rows=%s", name, rows_out)
    return rows_out


# builds every gold table and mart
def main() -> None:
    run_id = str(uuid.uuid4())
    log.info("gold start run=%s", run_id)
    spark = get_spark("lotus-gold")
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "gold")
            try:
                for name in ("dim_date", "dim_stores", "dim_products"):
                    df = spark.read.parquet(str(SILVER_DIR / f"{name}.parquet"))
                    land(cur, run_id, name, df, df.count())
                for name in ("dim_customers", "dim_employees"):
                    df = spark.read.parquet(str(SILVER_DIR / f"{name}_scd2.parquet"))
                    land(cur, run_id, name, df, df.count())
                orders = spark.read.parquet(str(SILVER_DIR / "fact_orders.parquet"))
                n_orders = orders.count()
                customers = spark.read.parquet(str(GOLD_DIR / "dim_customers.parquet"))
                employees = spark.read.parquet(str(GOLD_DIR / "dim_employees.parquet"))
                facts = build_fact_orders(orders, customers, employees).persist(
                    StorageLevel.MEMORY_AND_DISK
                )
                n_facts = land(cur, run_id, "fact_orders", facts, n_orders)
                returns = spark.read.parquet(str(SILVER_DIR / "fact_returns.parquet"))
                n_returns = returns.count()
                fact_returns = build_fact_returns(returns, facts).persist(
                    StorageLevel.MEMORY_AND_DISK
                )
                land(cur, run_id, "fact_returns", fact_returns, n_returns)
                details = spark.read.parquet(
                    str(SILVER_DIR / "fact_order_details.parquet")
                ).persist(StorageLevel.MEMORY_AND_DISK)
                n_details = details.count()
                land(cur, run_id, "fact_order_details", details, n_details)
                revenue = mart_revenue_by_store_month(facts)
                land(cur, run_id, "mart_revenue_by_store_month", revenue, n_facts)
                rates = mart_return_rate_by_product(details, fact_returns)
                land(cur, run_id, "mart_return_rate_by_product", rates, n_details)
                ramadan = mart_ramadan_seasonality(
                    facts, spark.read.parquet(str(GOLD_DIR / "dim_date.parquet"))
                )
                land(cur, run_id, "mart_ramadan_seasonality", ramadan, n_facts)
                facts.unpersist()
                fact_returns.unpersist()
                details.unpersist()
                finish_run(cur, run_id, "gold", "success", n_orders, n_facts)
            except Exception as exc:
                conn.rollback()
                finish_run(cur, run_id, "gold", "failed", 0, 0, str(exc))
                conn.commit()
                raise
    print(f"gold done run={run_id}")


if __name__ == "__main__":
    main()
