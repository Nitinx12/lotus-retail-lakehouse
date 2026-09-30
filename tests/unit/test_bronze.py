# unit tests for bronze pure helpers
from pyspark.sql import SparkSession

from scripts.run_bronze import columns_to_log, needs_reload
from src.bronze.ingest import (
    detect_new_columns,
    merge_columns,
    normalize_frame,
    schema_of,
)


# checks _id removal keeps input untouched
def test_normalize_frame(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"_id": "x", "a": 2}])
    out = normalize_frame(df)
    assert out.columns == ["a"]
    assert "_id" in df.columns


# checks new column detection
def test_detect_new_columns() -> None:
    assert detect_new_columns({"a": "int"}, {"a": "int", "b": "string"}) == ["b"]


# checks column union order
def test_merge_columns() -> None:
    assert merge_columns(["a"], ["a", "b"]) == ["a", "b"]


# checks schema capture type
def test_schema_of(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"a": 1}])
    assert schema_of(df) == {"a": "bigint"}


# checks unchanged collections skip the reread
def test_needs_reload() -> None:
    assert needs_reload(None, 10, True) is True
    assert needs_reload(10, 10, False) is True
    assert needs_reload(10, 10, True) is False
    assert needs_reload(10, 12, True) is True


# checks first load logs no schema changes
def test_columns_to_log() -> None:
    assert columns_to_log([], {"a": "bigint"}) == []
    assert columns_to_log(["a"], {"a": "bigint", "b": "string"}) == ["b"]
