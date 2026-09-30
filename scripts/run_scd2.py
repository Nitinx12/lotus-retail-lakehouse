# versions type 2 dimensions from cleaned silver tables
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.ops.db import build_dsn, finish_run, start_run, with_batch
from src.silver.scd2 import CUSTOMER_TRACKED, EMPLOYEE_TRACKED, apply_scd2
from src.spark.session import get_spark

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
    frame: DataFrame,
    table: str,
    natural_key: str,
    tracked: list[str],
    sk_col: str,
    anchor_date: str,
    change_date: str,
) -> DataFrame:
    from pyspark.sql import SparkSession

    session = SparkSession.getActiveSession()
    assert session is not None
    path = str(SILVER_DIR / f"{table}_scd2.parquet")
    current = session.read.parquet(path) if Path(path).exists() else None
    start = anchor_date if current is None else change_date
    task = f"scd2_{table}"
    start_run(cur, run_id, task)
    out = with_batch(
        apply_scd2(current, frame, natural_key, tracked, sk_col, start), run_id
    )
    out.write.mode("overwrite").parquet(path)
    versions = out.filter(F.col("is_current") == False).count()
    finish_run(cur, run_id, task, "success", frame.count(), out.count())
    log.info("scd2 %s rows=%s versions_closed=%s", table, out.count(), versions)
    return out


# versions both type 2 dimensions
def main() -> None:
    run_id = str(uuid.uuid4())
    spark = get_spark("lotus-scd2")
    orders = spark.read.parquet(str(SILVER_DIR / "fact_orders.parquet"))
    bounds = orders.agg(
        F.min("order_date").alias("lo"), F.max("order_date").alias("hi")
    ).collect()[0]
    anchor_date = str(bounds["lo"])
    change_date = str(bounds["hi"])
    log.info("scd2 start run=%s anchor=%s", run_id, anchor_date)
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "scd2")
            try:
                customers = spark.read.parquet(
                    str(SILVER_DIR / "dim_customers.parquet")
                )
                n_customers = customers.count()
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
                employees = spark.read.parquet(
                    str(SILVER_DIR / "dim_employees.parquet")
                )
                n_employees = employees.count()
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
                    n_customers + n_employees,
                    n_customers + n_employees,
                )
            except Exception as exc:
                conn.rollback()
                finish_run(cur, run_id, "scd2", "failed", 0, 0, str(exc))
                conn.commit()
                raise
    print(f"scd2 done run={run_id}")


if __name__ == "__main__":
    main()
