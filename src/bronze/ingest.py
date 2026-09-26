# pure helpers for the bronze landing step
from __future__ import annotations

import pandas as pd


# drops mongo internals without mutating the input
def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["_id"], errors="ignore")


# captures column dtypes as plain strings
def schema_of(df: pd.DataFrame) -> dict[str, str]:
    return {str(c): str(df[c].dtype) for c in df.columns}


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
