# unit tests for gx suite builders
from types import SimpleNamespace

from src.quality.gx_suites import layer_plan, score_checkpoint


# checks every bronze file has a key check
def test_bronze_plan() -> None:
    plan = layer_plan("bronze")
    assert len(plan) == 9
    assert all(len(checks) == 2 for checks in plan.values())


# checks silver covers uniqueness and domains
def test_silver_plan() -> None:
    plan = layer_plan("silver")
    assert len(plan["dim_customers.parquet"]) == 3
    assert len(plan["fact_orders.parquet"]) == 3


# checks gold covers surrogate keys
def test_gold_plan() -> None:
    plan = layer_plan("gold")
    assert any(
        type(c).__name__ == "ExpectColumnValuesToNotBeNull"
        for c in plan["fact_orders.parquet"]
    )


# checks scoring aggregates validation statistics
def test_score_checkpoint() -> None:
    results = {
        "a": SimpleNamespace(
            statistics={"evaluated_expectations": 4, "successful_expectations": 3}
        ),
        "b": SimpleNamespace(
            statistics={"evaluated_expectations": 2, "successful_expectations": 2}
        ),
    }
    pct, failed = score_checkpoint(results)
    assert pct == 100.0 * 5 / 6
    assert failed == 1
