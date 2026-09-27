# unit tests for gold builders
import pandas as pd

from src.gold.build import (
    build_fact_orders,
    build_fact_returns,
    mart_ramadan_seasonality,
    mart_return_rate_by_product,
    mart_revenue_by_store_month,
)


# checks as of resolution picks the old customer version
def test_build_fact_orders() -> None:
    orders = pd.DataFrame(
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
    customers = pd.DataFrame(
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
    employees = pd.DataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 7,
                "effective_start_date": "2024-01-01",
                "effective_end_date": None,
            }
        ]
    )
    out = build_fact_orders(orders, customers, employees)
    assert out["customer_sk"].iloc[0] == 1
    assert out["employee_sk"].iloc[0] == 7


# checks orders survive when no employee version covers the date
def test_build_fact_orders_keeps_unresolved_employee() -> None:
    orders = pd.DataFrame(
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
    customers = pd.DataFrame(
        [
            {
                "customer_id": "a",
                "customer_sk": 1,
                "region": "R1",
                "effective_start_date": "2024-01-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ]
    )
    employees = pd.DataFrame(
        [
            {
                "employee_id": "e1",
                "employee_sk": 7,
                "effective_start_date": "2024-06-01",
                "effective_end_date": None,
            }
        ]
    )
    out = build_fact_orders(orders, customers, employees)
    assert len(out) == 1
    assert out["customer_sk"].iloc[0] == 1
    assert pd.isna(out["employee_sk"].iloc[0])


# checks returns inherit order keys
def test_build_fact_returns() -> None:
    rets = pd.DataFrame([{"return_id": "r1", "order_id": "o1"}])
    orders = pd.DataFrame(
        [{"order_id": "o1", "customer_sk": 1, "employee_sk": 7, "store_id": 1}]
    )
    out = build_fact_returns(rets, orders)
    assert out["customer_sk"].iloc[0] == 1


# checks monthly revenue math
def test_revenue_mart() -> None:
    orders = pd.DataFrame(
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
    out = mart_revenue_by_store_month(orders)
    assert out["revenue"].iloc[0] == 30.0
    assert out["orders"].iloc[0] == 2


# checks return rate math
def test_return_rate_mart() -> None:
    det = pd.DataFrame(
        [
            {"order_id": "o1", "product_id": "p1"},
            {"order_id": "o2", "product_id": "p1"},
            {"order_id": "o2", "product_id": "p2"},
        ]
    )
    out = mart_return_rate_by_product(det, pd.Series(["o1"]))
    assert out.set_index("product_id").loc["p1", "return_rate"] == 0.5


# checks ramadan split columns
def test_ramadan_mart() -> None:
    orders = pd.DataFrame(
        [
            {
                "order_id": "o1",
                "order_date": "2024-03-15",
                "date_id": 20240315,
                "total_revenue": 5.0,
            }
        ]
    )
    dates = pd.DataFrame([{"date_id": 20240315, "is_ramadan": 1}])
    out = mart_ramadan_seasonality(orders, dates)
    assert out["is_ramadan"].iloc[0] == 1
