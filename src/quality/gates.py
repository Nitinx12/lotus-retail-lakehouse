# pure data quality checks backing the gate suites
from __future__ import annotations

import pandas as pd


# counts nulls in the given columns
def check_not_null(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    return {c: int(df[c].isna().sum()) for c in cols if c in df.columns}


# counts duplicated values in the given key columns
def check_unique(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    return {c: int(df.duplicated(subset=[c]).sum()) for c in cols if c in df.columns}


# counts child keys with no matching parent key
def check_referential(
    child: pd.DataFrame, child_col: str, parent: pd.DataFrame, parent_col: str
) -> int:
    return int((~child[child_col].isin(set(parent[parent_col].dropna()))).sum())


# lists values outside the allowed domain
def check_domain(df: pd.DataFrame, col: str, allowed: set[str]) -> list[str]:
    return sorted(set(df[col].dropna().astype(str)) - allowed)


# scores a suite mapping check name to failure count
def score(results: dict[str, int | list[str]]) -> tuple[float, int]:
    failed = 0
    for v in results.values():
        if isinstance(v, list):
            failed += len(v)
        else:
            failed += v
    total = len(results)
    passed = sum(
        1 for v in results.values() if (len(v) if isinstance(v, list) else v) == 0
    )
    return (100.0 * passed / total if total else 100.0, failed)
