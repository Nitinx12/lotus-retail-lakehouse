# unit tests for ops dsn helpers
from unittest.mock import MagicMock

import pandas as pd
from pyspark.sql import SparkSession

from src.ops.db import build_dsn, finish_run, start_run, with_batch


# checks libpq dsn formatting
def test_build_dsn() -> None:
    assert (
        build_dsn("localhost", 5432, "lotus_ops_dev", "lotus_ops", "pw")
        == "host=localhost port=5432 dbname=lotus_ops_dev user=lotus_ops password=pw"
    )


# checks batch stamping keeps rows untouched
def test_with_batch() -> None:
    df = pd.DataFrame([{"a": 1}, {"a": 2}])
    out = with_batch(df, "run-1")
    assert out["_batch_id"].tolist() == ["run-1", "run-1"]
    assert "_batch_id" not in df.columns


# checks restamping overwrites a stale batch id on spark frames
def test_with_batch_spark_overwrites(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"a": 1, "_batch_id": "old"}])
    out = with_batch(df, "run-2")
    rows = out.collect()
    assert [c for c in out.columns if c.startswith("_batch_id")] == ["_batch_id"]
    assert rows[0]["_batch_id"] == "run-2"


# checks running row sql carries the task name
def test_start_run() -> None:
    cur = MagicMock()
    start_run(cur, "run-1", "silver")
    sql, params = cur.execute.call_args[0]
    assert "running" in sql
    assert params == ("run-1", "silver")


# checks terminal row sql carries status and error
def test_finish_run() -> None:
    cur = MagicMock()
    finish_run(cur, "run-1", "silver", "failed", 3, 2, "boom")
    sql, params = cur.execute.call_args[0]
    assert "ON CONFLICT" in sql
    assert params == ("run-1", "silver", "failed", 3, 2, "boom")
