# builds cleaned silver parquet from bronze
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pyspark import StorageLevel
from pyspark.sql import DataFrame

from src.ops.db import build_dsn, finish_run, start_run, with_batch
from src.silver.transforms import (
    clean_customers,
    clean_orders,
    clean_products,
    drop_extract_meta,
    enrich_returns,
    union_orders,
)
from src.spark.session import get_spark

load_dotenv()

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")
LOG_FILE = Path("logs/silver.log")
SILVER_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("silver")


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
    task = f"silver_{name}"
    start_run(cur, run_id, task)
    path = str(SILVER_DIR / f"{name}.parquet")
    stamped = with_batch(df, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    rows_out = stamped.count()
    stamped.write.mode("overwrite").parquet(path)
    stamped.unpersist()
    finish_run(cur, run_id, task, "success", rows_in, rows_out)
    log.info("silver %s rows_in=%s rows_out=%s", name, rows_in, rows_out)
    return rows_out


# runs every silver build in dependency order
def main() -> None:
    run_id = str(uuid.uuid4())
    log.info("silver start run=%s", run_id)
    total_in = 0
    total_out = 0
    spark = get_spark("lotus-silver")
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "silver")
            try:
                customers = spark.read.parquet(
                    str(BRONZE_DIR / "dim_customers.parquet")
                )
                rows_in = customers.count()
                total_in += rows_in
                total_out += land(
                    cur, run_id, "dim_customers", clean_customers(customers), rows_in
                )

                products = spark.read.parquet(str(BRONZE_DIR / "dim_products.parquet"))
                rows_in = products.count()
                total_in += rows_in
                total_out += land(
                    cur, run_id, "dim_products", clean_products(products), rows_in
                )

                for name in (
                    "dim_stores",
                    "dim_employees",
                    "dim_date",
                    "fact_order_details",
                ):
                    df = drop_extract_meta(
                        spark.read.parquet(str(BRONZE_DIR / f"{name}.parquet"))
                    )
                    rows_in = df.count()
                    total_in += rows_in
                    total_out += land(cur, run_id, name, df, rows_in)

                first = clean_orders(
                    spark.read.parquet(
                        str(BRONZE_DIR / "fact_orders_2022_2023.parquet")
                    )
                ).persist(StorageLevel.MEMORY_AND_DISK)
                second = clean_orders(
                    spark.read.parquet(str(BRONZE_DIR / "fact_orders_2024.parquet"))
                ).persist(StorageLevel.MEMORY_AND_DISK)
                n_first = first.count()
                n_second = second.count()
                orders = union_orders(first, second)
                first.unpersist()
                second.unpersist()
                total_in += n_first + n_second
                total_out += land(
                    cur, run_id, "fact_orders", orders, n_first + n_second
                )

                returns = drop_extract_meta(
                    spark.read.parquet(str(BRONZE_DIR / "fact_returns.parquet"))
                )
                details = drop_extract_meta(
                    spark.read.parquet(str(BRONZE_DIR / "fact_order_details.parquet"))
                )
                n_returns = returns.count()
                total_in += n_returns
                total_out += land(
                    cur,
                    run_id,
                    "fact_returns",
                    enrich_returns(returns, details),
                    n_returns,
                )

                finish_run(cur, run_id, "silver", "success", total_in, total_out)
            except Exception as exc:
                conn.rollback()
                finish_run(
                    cur, run_id, "silver", "failed", total_in, total_out, str(exc)
                )
                conn.commit()
                raise
    log.info("silver done in=%s out=%s run=%s", total_in, total_out, run_id)
    print(f"silver done in={total_in} out={total_out} run={run_id}")


if __name__ == "__main__":
    main()
