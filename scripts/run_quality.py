# runs bronze, silver, and gold quality suites into ops
from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn, finish_run, start_run
from src.quality.gates import (
    check_domain,
    check_not_null,
    check_referential,
    check_unique,
    score,
)
from src.quality.gx_suites import BRONZE_TABLES, PAYMENTS

load_dotenv()

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")
LOG_FILE = Path("logs/quality.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("quality")


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


# checks raw landing completeness against the known source total
def bronze_suite() -> dict[str, int | list[str]]:
    total = 0
    results: dict[str, int | list[str]] = {}
    for name in BRONZE_TABLES:
        df = pd.read_parquet(BRONZE_DIR / f"{name}.parquet")
        results[f"{name}_nonempty"] = 0 if len(df) else 1
        total += len(df)
    results["total_rows"] = 0 if total == 42877 else abs(total - 42877)
    return results


# checks cleaned silver invariants
def silver_suite() -> dict[str, int | list[str]]:
    customers = pd.read_parquet(SILVER_DIR / "dim_customers.parquet")
    products = pd.read_parquet(SILVER_DIR / "dim_products.parquet")
    orders = pd.read_parquet(SILVER_DIR / "fact_orders.parquet")
    returns = pd.read_parquet(SILVER_DIR / "fact_returns.parquet")
    apparel_missing = products[
        (products["category"] != "Electronics")
        & (products["color"].isna() | products["size"].isna())
    ]
    return {
        "customers_unique": check_unique(customers, ["customer_id"])["customer_id"],
        "gender_domain": check_domain(customers, "gender", {"Male", "Female"}),
        "product_split": check_not_null(products, ["product_name"])["product_name"]
        + len(apparel_missing),
        "orders_unique": check_unique(orders, ["order_id"])["order_id"],
        "payment_domain": check_domain(orders, "payment_method", PAYMENTS),
        "returns_enriched": check_not_null(returns, ["n_items"])["n_items"],
    }


# checks gold keys and mart reconciliation
def gold_checks(
    facts: pd.DataFrame,
    customers: pd.DataFrame,
    employees: pd.DataFrame,
    returns: pd.DataFrame,
    revenue: pd.DataFrame,
) -> dict[str, int | list[str]]:
    named = facts[facts["employee_id"].notna()]
    return {
        "customer_sk_covered": check_not_null(facts, ["customer_sk"])["customer_sk"],
        "customers_fk": check_referential(
            facts, "customer_id", customers, "customer_id"
        ),
        "employees_fk": check_referential(
            named, "employee_id", employees, "employee_id"
        ),
        "returns_sk": check_not_null(returns, ["customer_sk"])["customer_sk"],
        "mart_reconciled": 0
        if round(revenue["revenue"].sum(), 2) == round(facts["total_revenue"].sum(), 2)
        else 1,
    }


# loads gold frames and checks keys and mart reconciliation
def gold_suite() -> dict[str, int | list[str]]:
    facts = pd.read_parquet(GOLD_DIR / "fact_orders.parquet")
    customers = pd.read_parquet(GOLD_DIR / "dim_customers.parquet")
    employees = pd.read_parquet(GOLD_DIR / "dim_employees.parquet")
    returns = pd.read_parquet(GOLD_DIR / "fact_returns.parquet")
    revenue = pd.read_parquet(GOLD_DIR / "mart_revenue_by_store_month.parquet")
    return gold_checks(facts, customers, employees, returns, revenue)


# runs all three suites and blocks on failure
def main() -> None:
    run_id = str(uuid.uuid4())
    suites = {"bronze": bronze_suite(), "silver": silver_suite(), "gold": gold_suite()}
    blocked = False
    with ops_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            start_run(cur, run_id, "quality")
            try:
                for name, results in suites.items():
                    pct, failed = score(results)
                    cur.execute(
                        "INSERT INTO ops.quality_results (run_id, suite_name, success_percent, failed_expectations) VALUES (%s, %s, %s, %s)",
                        (run_id, name, pct, failed),
                    )
                    finish_run(
                        cur,
                        run_id,
                        f"quality_{name}",
                        "failed" if failed else "success",
                        0,
                        failed,
                    )
                    log.info("quality %s pct=%s failed=%s", name, pct, failed)
                    if failed:
                        blocked = True
                        log.warning(
                            "quality %s failures=%s",
                            name,
                            {k: v for k, v in results.items() if v},
                        )
                finish_run(
                    cur, run_id, "quality", "failed" if blocked else "success", 0, 0
                )
            except Exception as exc:
                conn.rollback()
                finish_run(cur, run_id, "quality", "failed", 0, 0, str(exc))
                conn.commit()
                raise
    print(f"quality done run={run_id} blocked={blocked}")
    if blocked:
        sys.exit(1)


if __name__ == "__main__":
    main()
