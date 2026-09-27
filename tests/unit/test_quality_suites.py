# unit tests for quality suite checks
import pandas as pd

from scripts.run_quality import gold_checks


# checks historical employee ids pass against all versions
def test_gold_checks_cover_history() -> None:
    facts = pd.DataFrame(
        [
            {
                "order_id": "o1",
                "customer_id": "a",
                "customer_sk": 1,
                "employee_id": "e1",
                "total_revenue": 10.0,
            }
        ]
    )
    customers = pd.DataFrame([{"customer_id": "a"}])
    employees = pd.DataFrame(
        [
            {"employee_id": "e1", "is_current": False},
            {"employee_id": "e2", "is_current": True},
        ]
    )
    returns = pd.DataFrame([{"return_id": "r1", "customer_sk": 1}])
    revenue = pd.DataFrame([{"revenue": 10.0}])
    out = gold_checks(facts, customers, employees, returns, revenue)
    assert out["employees_fk"] == 0
    assert out["mart_reconciled"] == 0
