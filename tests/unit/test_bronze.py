# unit tests for bronze pure helpers
import pandas as pd

from src.bronze.ingest import (
    detect_new_columns,
    merge_columns,
    normalize_frame,
    schema_of,
)


# checks _id removal keeps input untouched
def test_normalize_frame() -> None:
    df = pd.DataFrame([{"_id": 1, "a": 2}])
    out = normalize_frame(df)
    assert list(out.columns) == ["a"]
    assert "_id" in df.columns


# checks new column detection
def test_detect_new_columns() -> None:
    assert detect_new_columns({"a": "int64"}, {"a": "int64", "b": "object"}) == ["b"]


# checks column union order
def test_merge_columns() -> None:
    assert merge_columns(["a"], ["a", "b"]) == ["a", "b"]


# checks schema capture type
def test_schema_of() -> None:
    assert schema_of(pd.DataFrame([{"a": 1}])) == {"a": "int64"}
