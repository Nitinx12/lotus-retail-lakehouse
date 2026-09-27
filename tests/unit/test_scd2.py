# unit tests for scd2 versioning
import pandas as pd

from src.silver.scd2 import CUSTOMER_TRACKED, apply_scd2, asof_join


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


# checks duplicate keys in one batch collapse to a single current row
def test_batch_dedupe() -> None:
    dup = pd.DataFrame(
        [
            {"customer_id": "b", "region": "R1", "loyalty_tier": "Gold"},
            {"customer_id": "b", "region": "R2", "loyalty_tier": "Gold"},
        ]
    )
    out = apply_scd2(
        None, dup, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2024-01-01"
    )
    assert len(out) == 1
    assert bool(out["is_current"].iloc[0]) is True
    assert out["region"].iloc[0] == "R2"


# checks untracked city change alone opens no new version
def test_untracked_city_noop() -> None:
    inc = pd.DataFrame([{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold"}])
    first = apply_scd2(
        None, inc, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2024-01-01"
    )
    moved = pd.DataFrame(
        [
            {
                "customer_id": "a",
                "region": "R1",
                "loyalty_tier": "Gold",
                "city": "Luxor",
            }
        ]
    )
    out = apply_scd2(
        first, moved, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2024-02-01"
    )
    assert len(out) == 1


# checks facts with an unknown key survive with a null surrogate
def test_asof_keeps_orphan() -> None:
    dim = pd.DataFrame(
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
    facts = pd.DataFrame(
        [
            {"order_id": "o1", "customer_id": "ghost", "order_date": "2024-01-15"},
            {"order_id": "o2", "customer_id": "a", "order_date": "2024-01-15"},
        ]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date")
    assert len(out) == 2
    assert pd.isna(out.set_index("order_id").loc["o1", "customer_sk"])
    assert out.set_index("order_id").loc["o2", "customer_sk"] == 1


# checks facts outside every version window survive with a null surrogate
def test_asof_keeps_predated_fact() -> None:
    dim = pd.DataFrame(
        [
            {
                "customer_id": "a",
                "customer_sk": 1,
                "region": "R1",
                "effective_start_date": "2024-02-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ]
    )
    facts = pd.DataFrame(
        [{"order_id": "o1", "customer_id": "a", "order_date": "2024-01-15"}]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date")
    assert len(out) == 1
    assert pd.isna(out["customer_sk"].iloc[0])
