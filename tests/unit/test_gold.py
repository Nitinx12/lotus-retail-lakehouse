# unit tests for gold builders
from pyspark.sql import SparkSession

from src.gold.build import (
    build_fact_orders,
    build_fact_returns,
    mart_ramadan_seasonality,
    mart_return_rate_by_product,
    mart_revenue_by_store_month,
)


# checks as of resolution picks the old customer version
def test_build_fact_orders(spark: SparkSession) -> None:
    orders = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "customer_id": "a",
                "employee_id": "e1",
                "order_date": "2024-01-15",
                "total_revenue": 10.0,
                "total_cost": 5.0,
                "store_id": 1,
            }
        ]
    )
    customers = spark.createDataFrame(
        [
            {
                "customer_id": "a",
                "customer_sk": 1,
                "region": "R1",
                "effective_start_date": "2024-01-01",
                "effective_end_date": "2024-02-01",
                "is_current": False,
            },
            {
                "customer_id": "a",
                "customer_sk": 2,
                "region": "R2",
                "effective_start_date": "2024-02-01",
                "effective_end_date": None,
                "is_current": True,
            },
        ]
    )
    employees = spark.createDataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 7,
                "effective_start_date": "2024-01-01",
                "effective_end_date": None,
            }
        ],
        schema=(
            "employee_id STRING, employee_sk INT, "
            "effective_start_date STRING, effective_end_date STRING"
        ),
    )
    row = build_fact_orders(orders, customers, employees).collect()[0]
    assert row["customer_sk"] == 1
    assert row["employee_sk"] == 7


# checks orders survive when no employee version covers the date
def test_build_fact_orders_keeps_unresolved_employee(spark: SparkSession) -> None:
    orders = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "customer_id": "a",
                "employee_id": "e1",
                "order_date": "2024-01-15",
                "total_revenue": 10.0,
                "total_cost": 5.0,
                "store_id": 1,
            }
        ]
    )
    customers = spark.createDataFrame(
        [
            {
                "customer_id": "a",
                "customer_sk": 1,
                "region": "R1",
                "effective_start_date": "2024-01-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ],
        schema=(
            "customer_id STRING, customer_sk INT, region STRING, "
            "effective_start_date STRING, effective_end_date STRING, "
            "is_current BOOLEAN"
        ),
    )
    employees = spark.createDataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 7,
                "effective_start_date": "2024-06-01",
                "effective_end_date": None,
            }
        ],
        schema=(
            "employee_id STRING, employee_sk INT, "
            "effective_start_date STRING, effective_end_date STRING"
        ),
    )
    rows = build_fact_orders(orders, customers, employees).collect()
    assert len(rows) == 1
    assert rows[0]["customer_sk"] == 1
    assert rows[0]["employee_sk"] is None


# checks returns inherit order keys
def test_build_fact_returns(spark: SparkSession) -> None:
    rets = spark.createDataFrame([{"return_id": "r1", "order_id": "o1"}])
    orders = spark.createDataFrame(
        [{"order_id": "o1", "customer_sk": 1, "employee_sk": 7, "store_id": 1}]
    )
    assert build_fact_returns(rets, orders).collect()[0]["customer_sk"] == 1


# checks monthly revenue math
def test_revenue_mart(spark: SparkSession) -> None:
    orders = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "store_id": 1,
                "order_date": "2024-01-05",
                "total_revenue": 10.0,
                "total_cost": 4.0,
            },
            {
                "order_id": "o2",
                "store_id": 1,
                "order_date": "2024-01-06",
                "total_revenue": 20.0,
                "total_cost": 8.0,
            },
        ]
    )
    row = mart_revenue_by_store_month(orders).collect()[0]
    assert row["revenue"] == 30.0
    assert row["orders"] == 2


# checks return rate math
def test_return_rate_mart(spark: SparkSession) -> None:
    det = spark.createDataFrame(
        [
            {"order_id": "o1", "product_id": "p1"},
            {"order_id": "o2", "product_id": "p1"},
            {"order_id": "o2", "product_id": "p2"},
        ]
    )
    out = mart_return_rate_by_product(det, ["o1"]).collect()
    by_product = {r["product_id"]: r for r in out}
    assert by_product["p1"]["return_rate"] == 0.5


# checks ramadan split columns
def test_ramadan_mart(spark: SparkSession) -> None:
    orders = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "order_date": "2024-03-15",
                "date_id": 20240315,
                "total_revenue": 5.0,
            }
        ]
    )
    dates = spark.createDataFrame([{"date_id": 20240315, "is_ramadan": 1}])
    assert mart_ramadan_seasonality(orders, dates).collect()[0]["is_ramadan"] == 1
