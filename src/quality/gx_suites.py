# great expectations suites per medallion layer
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from great_expectations import expectations as ex

BRONZE_TABLES = [
    "dim_customers",
    "dim_date",
    "dim_employees",
    "dim_products",
    "dim_stores",
    "fact_order_details",
    "fact_orders_2022_2023",
    "fact_orders_2024",
    "fact_returns",
]

BRONZE_KEYS = {
    "dim_customers": "customer_id",
    "dim_date": "date_id",
    "dim_employees": "employee_id",
    "dim_products": "product_id",
    "dim_stores": "store_id",
    "fact_order_details": "detail_id",
    "fact_orders_2022_2023": "order_id",
    "fact_orders_2024": "order_id",
    "fact_returns": "return_id",
}

PAYMENTS = {"Cash", "Credit Card", "Debit Card", "Fawry", "InstaPay", "Vodafone Cash"}


# builds row count plus key presence checks for one bronze file
def bronze_checks(table: str) -> list:
    return [
        ex.ExpectTableRowCountToBeBetween(min_value=1),
        ex.ExpectColumnToExist(column=BRONZE_KEYS[table]),
    ]


# builds cleaning invariant checks for one silver file
def silver_checks(table: str) -> list:
    checks: list = [ex.ExpectTableRowCountToBeBetween(min_value=1)]
    if table == "dim_customers":
        checks += [
            ex.ExpectColumnValuesToBeUnique(column="customer_id"),
            ex.ExpectColumnValuesToBeInSet(
                column="gender", value_set=["Male", "Female"]
            ),
        ]
    elif table == "dim_products":
        checks += [ex.ExpectColumnValuesToNotBeNull(column="product_name")]
    elif table == "fact_orders":
        checks += [
            ex.ExpectColumnValuesToBeUnique(column="order_id"),
            ex.ExpectColumnValuesToBeInSet(column="payment_method", value_set=PAYMENTS),
        ]
    return checks


# builds key coverage checks for one gold file
def gold_checks(table: str) -> list:
    checks: list = [ex.ExpectTableRowCountToBeBetween(min_value=1)]
    if table in ("fact_orders", "fact_returns"):
        checks += [ex.ExpectColumnValuesToNotBeNull(column="customer_sk")]
    if table == "fact_orders":
        checks += [ex.ExpectColumnValuesToBeUnique(column="order_id")]
    return checks


# maps a layer name to its table files and check builder
def layer_plan(layer: str) -> dict[str, list]:
    if layer == "bronze":
        return {f"{t}.parquet": bronze_checks(t) for t in BRONZE_TABLES}
    if layer == "silver":
        tables = [
            "dim_customers",
            "dim_products",
            "dim_stores",
            "dim_employees",
            "dim_date",
            "fact_order_details",
            "fact_orders",
            "fact_returns",
        ]
        return {f"{t}.parquet": silver_checks(t) for t in tables}
    if layer == "gold":
        tables = [
            "dim_date",
            "dim_stores",
            "dim_products",
            "dim_customers",
            "dim_employees",
            "fact_orders",
            "fact_returns",
            "fact_order_details",
        ]
        return {f"{t}.parquet": gold_checks(t) for t in tables}
    raise ValueError(f"unknown layer {layer}")


# aggregates checkpoint statistics into a pass percent and failure count
def score_checkpoint(run_results: Mapping[str, Any]) -> tuple[float, int]:
    evaluated = 0
    successful = 0
    for result in run_results.values():
        stats = result.statistics
        evaluated += stats["evaluated_expectations"]
        successful += stats["successful_expectations"]
    failed = evaluated - successful
    pct = 100.0 * successful / evaluated if evaluated else 100.0
    return pct, failed
