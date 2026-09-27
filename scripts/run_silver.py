# builds cleaned silver parquet from bronze
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn, finish_run, start_run, with_batch
from src.silver.transforms import (
    clean_customers,
    clean_orders,
    clean_products,
    drop_extract_meta,
    enrich_returns,
    union_orders,
)

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
def land(cur: object, run_id: str, name: str, df: pd.DataFrame, rows_in: int) -> None:
    task = f"silver_{name}"
    start_run(cur, run_id, task)
    path = SILVER_DIR / f"{name}.parquet"
    df = with_batch(df, run_id)
    df.to_parquet(path, index=False)
    finish_run(cur, run_id, task, "success", rows_in, len(df))
    log.info("silver %s rows_in=%s rows_out=%s", name, rows_in, len(df))


# runs every silver build in dependency order
def main() -> None:
    run_id = str(uuid.uuid4())
    log.info("silver start run=%s", run_id)
    total_in = 0
    total_out = 0
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "silver")
            try:
                customers = pd.read_parquet(BRONZE_DIR / "dim_customers.parquet")
                out = clean_customers(customers)
                total_in += len(customers)
                total_out += len(out)
                land(cur, run_id, "dim_customers", out, len(customers))

                products = pd.read_parquet(BRONZE_DIR / "dim_products.parquet")
                out = clean_products(products)
                total_in += len(products)
                total_out += len(out)
                land(cur, run_id, "dim_products", out, len(products))

                for name in (
                    "dim_stores",
                    "dim_employees",
                    "dim_date",
                    "fact_order_details",
                ):
                    df = drop_extract_meta(
                        pd.read_parquet(BRONZE_DIR / f"{name}.parquet")
                    )
                    total_in += len(df)
                    total_out += len(df)
                    land(cur, run_id, name, df, len(df))

                first = clean_orders(
                    pd.read_parquet(BRONZE_DIR / "fact_orders_2022_2023.parquet")
                )
                second = clean_orders(
                    pd.read_parquet(BRONZE_DIR / "fact_orders_2024.parquet")
                )
                orders = union_orders(first, second)
                total_in += len(first) + len(second)
                total_out += len(orders)
                land(cur, run_id, "fact_orders", orders, len(first) + len(second))

                returns = drop_extract_meta(
                    pd.read_parquet(BRONZE_DIR / "fact_returns.parquet")
                )
                details = drop_extract_meta(
                    pd.read_parquet(BRONZE_DIR / "fact_order_details.parquet")
                )
                enriched = enrich_returns(returns, details)
                total_in += len(returns)
                total_out += len(enriched)
                land(cur, run_id, "fact_returns", enriched, len(returns))

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
