# publishes gold parquet into the postgres serving schema
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

from src.ops.db import build_dsn, finish_run, read_sql, start_run

load_dotenv()

GOLD_DIR = Path("data/gold")
LOG_FILE = Path("logs/publish.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("publish")

GOLD_SCHEMA = "gold"

TABLES = [
    "dim_date",
    "dim_stores",
    "dim_products",
    "dim_customers",
    "dim_employees",
    "fact_orders",
    "fact_returns",
    "fact_order_details",
]


# opens the gold serving warehouse
def gold_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=build_dsn(
            os.getenv("POSTGRES_GOLD_HOST", "localhost"),
            int(os.getenv("POSTGRES_GOLD_PORT", "5432")),
            os.getenv("POSTGRES_GOLD_DB", "lotus_gold_dev"),
            os.getenv("POSTGRES_GOLD_USER", "lotus_pipeline"),
            os.getenv("POSTGRES_GOLD_PASSWORD", ""),
        ),
        connect_timeout=5,
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


# builds a sqlalchemy engine for bulk loads from parts
def gold_engine_url() -> str:
    return (
        "postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_GOLD_USER', 'lotus_pipeline')}"
        f":{os.getenv('POSTGRES_GOLD_PASSWORD', '')}"
        f"@{os.getenv('POSTGRES_GOLD_HOST', 'localhost')}"
        f":{os.getenv('POSTGRES_GOLD_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_GOLD_DB', 'lotus_gold_dev')}"
    )


# replaces one serving table inside its own transaction
def publish_table(engine: Engine, df: pd.DataFrame, table: str) -> int:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {GOLD_SCHEMA}"))
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_name = :table"
            ),
            {"schema": GOLD_SCHEMA, "table": table},
        ).first()
        if exists:
            conn.execute(text(f"DELETE FROM {GOLD_SCHEMA}.{table}"))
        df.to_sql(
            table,
            conn,
            schema=GOLD_SCHEMA,
            if_exists="append",
            index=False,
            chunksize=2000,
            method="multi",
        )
    return len(df)


# loads every gold table into the serving schema
def main() -> None:
    run_id = str(uuid.uuid4())
    log.info("publish start run=%s", run_id)
    total = 0
    with ops_conn() as ops:
        ops.autocommit = True
        with ops.cursor() as cur:
            start_run(cur, run_id, "publish")
            try:
                engine = create_engine(gold_engine_url())
                with gold_conn() as gold:
                    gold.autocommit = True
                    for name in TABLES:
                        task = f"publish_{name}"
                        start_run(cur, run_id, task)
                        df = pd.read_parquet(GOLD_DIR / f"{name}.parquet")
                        rows = publish_table(engine, df, name)
                        finish_run(cur, run_id, task, "success", rows, rows)
                        total += rows
                        log.info("publish %s rows=%s", name, rows)
                    with gold.cursor() as gcur:
                        for name in (
                            "index/02_gold_indexes.sql",
                            "triggers/02_gold_triggers.sql",
                        ):
                            gcur.execute(read_sql(Path(f"sql/{name}")))
                            log.info("publish ensured %s", name)
                        gcur.execute(
                            "REVOKE ALL ON gold.dim_customers "
                            "FROM lotus_app, lotus_api_reader"
                        )
                        log.info("publish reissued dim_customers revokes")
                finish_run(cur, run_id, "publish", "success", total, total)
            except Exception as exc:
                ops.rollback()
                finish_run(cur, run_id, "publish", "failed", total, total, str(exc))
                ops.commit()
                raise
    log.info("publish done total=%s run=%s", total, run_id)
    print(f"publish done total={total} run={run_id}")


if __name__ == "__main__":
    main()
