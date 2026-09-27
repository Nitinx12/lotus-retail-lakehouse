# unit tests for ops dsn helpers
import pandas as pd

from src.ops.db import build_dsn, with_batch


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
