# smoke test for the full bronze to gold chain on synthetic rows
from pyspark.sql import SparkSession

from src.bronze.ingest import normalize_frame
from src.gold.build import build_fact_orders, mart_revenue_by_store_month
from src.quality.gates import check_unique, score
from src.silver.scd2 import CUSTOMER_TRACKED, apply_scd2
from src.silver.transforms import (
    clean_customers,
    clean_orders,
    enrich_returns,
    union_orders,
)


# checks a sampled end to end run preserves every order
def test_smoke_pipeline(spark: SparkSession) -> None:
    raw_customers = spark.createDataFrame(
        [
            {
                "_id": "x",
                "customer_id": "a",
                "full_name": "Ann ",
                "gender": "FEMALE",
                "phone": "1",
                "birth_date": "2000-01-01",
                "registration_date": "2022-01-01",
                "city": "Cairo",
                "region": "R1",
                "loyalty_tier": "Gold",
                "email": "a@x.com",
            }
        ]
    )
    customers = clean_customers(normalize_frame(raw_customers))
    versioned = apply_scd2(
        None, customers, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2022-01-01"
    )
    employees = spark.createDataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 1,
                "effective_start_date": "2022-01-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ],
        schema=(
            "employee_id STRING, employee_sk INT, "
            "effective_start_date STRING, effective_end_date STRING, "
            "is_current BOOLEAN"
        ),
    )
    first = clean_orders(
        spark.createDataFrame(
            [
                {
                    "order_id": "o1",
                    "order_date": "2022-03-01",
                    "customer_id": "a",
                    "employee_id": "e1",
                    "store_id": 1,
                    "payment_method": "Cash",
                    "order_status": "Completed",
                    "total_revenue": 10.0,
                    "total_cost": 4.0,
                }
            ]
        )
    )
    orders = union_orders(first, first)
    enriched = enrich_returns(
        spark.createDataFrame(
            [
                {
                    "return_id": "r1",
                    "order_id": "o1",
                    "return_date": "2022-03-02",
                    "return_reason": "X",
                    "refund_method": "Cash",
                    "return_status": "Refunded",
                }
            ]
        ),
        spark.createDataFrame(
            [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 10.0}]
        ),
    )
    facts = build_fact_orders(orders, versioned, employees)
    assert facts.count() == 1
    assert facts.collect()[0]["customer_sk"] == 1
    assert mart_revenue_by_store_month(facts).count() == 1
    assert check_unique(facts.toPandas(), ["order_id"])["order_id"] == 0
    orphans = enriched.filter("return_orphan").count()
    pct, failed = score({"orders_unique": 0, "orphans": orphans})
    assert pct == 100.0
    assert failed == 0
