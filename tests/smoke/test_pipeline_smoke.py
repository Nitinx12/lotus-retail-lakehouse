# smoke test for the full bronze to gold chain on synthetic rows
import pandas as pd

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
def test_smoke_pipeline() -> None:
    raw_customers = pd.DataFrame(
        [
            {
                "_id": "x",
                "customer_id": "a",
                "full_name": "Ann ",
                "gender": "FEMALE",
                "phone": 1,
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
    employees = pd.DataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 1,
                "effective_start_date": "2022-01-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ]
    )
    first = clean_orders(
        pd.DataFrame(
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
    orders = union_orders(first, first.copy())
    enriched = enrich_returns(
        pd.DataFrame(
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
        pd.DataFrame(
            [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 10.0}]
        ),
    )
    facts = build_fact_orders(orders, versioned, employees)
    assert len(facts) == 1
    assert facts["customer_sk"].iloc[0] == 1
    assert len(mart_revenue_by_store_month(facts)) == 1
    assert check_unique(facts, ["order_id"])["order_id"] == 0
    pct, failed = score(
        {"orders_unique": 0, "orphans": int(enriched["return_orphan"].sum())}
    )
    assert pct == 100.0
    assert failed == 0
