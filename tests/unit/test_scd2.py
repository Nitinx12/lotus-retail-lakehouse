# unit tests for scd2 versioning
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.silver.scd2 import CUSTOMER_TRACKED, apply_scd2, asof_join


# checks first load creates current rows
def test_first_load(spark: SparkSession) -> None:
    inc = spark.createDataFrame(
        [{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold", "city": "C"}]
    )
    out = apply_scd2(
        None,
        inc,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-01-01",
    ).collect()
    assert len(out) == 1
    assert out[0]["is_current"] is True
    assert out[0]["customer_sk"] == 1


# checks unchanged reload is a no op
def test_noop(spark: SparkSession) -> None:
    inc = spark.createDataFrame(
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
    assert second.count() == 1


# checks tracked change closes old and opens new
def test_change(spark: SparkSession) -> None:
    inc = spark.createDataFrame(
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
    changed = spark.createDataFrame(
        [{"customer_id": "a", "region": "R2", "loyalty_tier": "Gold", "city": "C"}]
    )
    out = apply_scd2(
        first,
        changed,
        "customer_id",
        ["region", "loyalty_tier", "city"],
        "customer_sk",
        "2024-02-01",
    ).collect()
    assert len(out) == 2
    assert sorted([r["customer_sk"] for r in out]) == [1, 2]
    assert [r["is_current"] for r in sorted(out, key=lambda r: r["customer_sk"])] == [
        False,
        True,
    ]


# checks corrupted history with two current rows fails loudly
def test_duplicate_current_errors(spark: SparkSession) -> None:
    schema = (
        "customer_id STRING, region STRING, loyalty_tier STRING, customer_sk INT, "
        "effective_start_date STRING, effective_end_date STRING, "
        "is_current BOOLEAN, attribute_hash STRING"
    )
    current = spark.createDataFrame(
        [
            {
                "customer_id": "a",
                "region": "R1",
                "loyalty_tier": "Gold",
                "customer_sk": 1,
                "effective_start_date": "2024-01-01",
                "effective_end_date": None,
                "is_current": True,
                "attribute_hash": "h1",
            },
            {
                "customer_id": "a",
                "region": "R2",
                "loyalty_tier": "Gold",
                "customer_sk": 2,
                "effective_start_date": "2024-02-01",
                "effective_end_date": None,
                "is_current": True,
                "attribute_hash": "h2",
            },
        ],
        schema=schema,
    )
    inc = spark.createDataFrame(
        [{"customer_id": "a", "region": "R3", "loyalty_tier": "Gold"}]
    )
    with pytest.raises(ValueError, match="several current rows"):
        apply_scd2(
            current,
            inc,
            "customer_id",
            ["region", "loyalty_tier"],
            "customer_sk",
            "2024-03-01",
        )


# checks point in time join resolves the old version
def test_asof(spark: SparkSession) -> None:
    dim = spark.createDataFrame(
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
    facts = spark.createDataFrame(
        [{"order_id": "o1", "customer_id": "a", "order_date": "2024-01-15"}]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date").collect()
    assert out[0]["customer_sk"] == 1


# checks duplicate keys in one batch collapse to a single current row
def test_batch_dedupe(spark: SparkSession) -> None:
    dup = spark.createDataFrame(
        [
            {"customer_id": "b", "region": "R1", "loyalty_tier": "Gold"},
            {"customer_id": "b", "region": "R2", "loyalty_tier": "Gold"},
        ]
    )
    out = apply_scd2(
        None, dup, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2024-01-01"
    ).collect()
    assert len(out) == 1
    assert out[0]["is_current"] is True
    assert out[0]["region"] == "R2"


# checks untracked city change alone opens no new version
def test_untracked_city_noop(spark: SparkSession) -> None:
    inc = spark.createDataFrame(
        [{"customer_id": "a", "region": "R1", "loyalty_tier": "Gold"}]
    )
    first = apply_scd2(
        None, inc, "customer_id", CUSTOMER_TRACKED, "customer_sk", "2024-01-01"
    )
    moved = spark.createDataFrame(
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
    assert out.count() == 1


# checks facts with an unknown key survive with a null surrogate
def test_asof_keeps_orphan(spark: SparkSession) -> None:
    schema = (
        "customer_id STRING, customer_sk INT, region STRING, "
        "effective_start_date STRING, effective_end_date STRING, is_current BOOLEAN"
    )
    dim = spark.createDataFrame(
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
        schema=schema,
    )
    facts = spark.createDataFrame(
        [
            {"order_id": "o1", "customer_id": "ghost", "order_date": "2024-01-15"},
            {"order_id": "o2", "customer_id": "a", "order_date": "2024-01-15"},
        ]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date").collect()
    by_id = {r["order_id"]: r for r in out}
    assert len(out) == 2
    assert by_id["o1"]["customer_sk"] is None
    assert by_id["o2"]["customer_sk"] == 1


# checks facts outside every version window survive with a null surrogate
def test_asof_keeps_predated_fact(spark: SparkSession) -> None:
    schema = (
        "customer_id STRING, customer_sk INT, region STRING, "
        "effective_start_date STRING, effective_end_date STRING, is_current BOOLEAN"
    )
    dim = spark.createDataFrame(
        [
            {
                "customer_id": "a",
                "customer_sk": 1,
                "region": "R1",
                "effective_start_date": "2024-02-01",
                "effective_end_date": None,
                "is_current": True,
            }
        ],
        schema=schema,
    )
    facts = spark.createDataFrame(
        [{"order_id": "o1", "customer_id": "a", "order_date": "2024-01-15"}]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date").collect()
    assert len(out) == 1
    assert out[0]["customer_sk"] is None


# checks stale batch ids on both sides never break the join
def test_asof_ignores_batch_ids(spark: SparkSession) -> None:
    schema = (
        "customer_id STRING, customer_sk INT, region STRING, "
        "effective_start_date STRING, effective_end_date STRING, is_current BOOLEAN"
    )
    dim = spark.createDataFrame(
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
        schema=schema,
    ).withColumn("_batch_id", F.lit("old"))
    facts = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "customer_id": "a",
                "order_date": "2024-01-15",
                "_batch_id": "older",
            }
        ]
    )
    out = asof_join(facts, dim, "customer_id", "customer_sk", "order_date").collect()
    assert len(out) == 1
    assert out[0]["customer_sk"] == 1
