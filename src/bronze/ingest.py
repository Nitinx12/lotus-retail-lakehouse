# pure helpers for the bronze landing step
from __future__ import annotations

from pyspark.sql import DataFrame


# drops mongo internals without mutating the input
def normalize_frame(df: DataFrame) -> DataFrame:
    return df.drop("_id") if "_id" in df.columns else df


# captures column dtypes as plain strings
def schema_of(df: DataFrame) -> dict[str, str]:
    return {f.name: str(f.dataType.simpleString()) for f in df.schema.fields}


# lists columns present now that were absent before
def detect_new_columns(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    return sorted([c for c in current if c not in previous])


# unions two column lists keeping first seen order
def merge_columns(previous: list[str], current: list[str]) -> list[str]:
    seen = list(previous)
    for c in current:
        if c not in seen:
            seen.append(c)
    return seen
