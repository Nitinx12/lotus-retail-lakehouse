# unit tests for scd2 versioning
import pandas as pd

from src.silver.scd2 import apply_scd2, asof_join


# checks first load creates current rows
def test_first_load() -> None:
    inc = pd.DataFrame(
        [{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold", "city": "C"}]
    )
    out = apply_scd2(
        None,
        inc,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-01-01",
    )
    assert len(out) == 1
    assert bool(out["is_current"].iloc[0]) is True
    assert out["customer_sk"].iloc[0] == 1


# checks unchanged reload is a no op
def test_noop() -> None:
    inc = pd.DataFrame(
        [{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold", "city": "C"}]
    )
    first = apply_scd2(
        None,
        inc,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-01-01",
    )
    second = apply_scd2(
        first,
        inc,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-02-01",
    )
    assert len(second) == 1


# checks tracked change closes old and opens new
def test_change() -> None:
    inc = pd.DataFrame(
        [{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold", "city": "C"}]
    )
    first = apply_scd2(
        None,
        inc,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-01-01",
    )
    changed = pd.DataFrame(
        [{"customer_id": "a", "region": "R2", "loyalty_tier": "Gold", "city": "C"}]
    )
    out = apply_scd2(
        first,
        changed,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-02-01",
    )
    assert len(out) == 2
    assert sorted(out["customer_sk"].tolist()) == [1, 2]
    assert out["is_current"].tolist() == [False, True]


# checks point in time join resolves the old version
def test_asof() -> None:
    dim = pd.DataFrame(
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
    facts = pd.DataFrame(
        [{"order_id": "o1", "customer_id": "a", "order_date": "2024-01-15"}]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date")
    assert out["customer_sk"].iloc[0] == 1
