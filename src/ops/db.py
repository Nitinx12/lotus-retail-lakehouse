# helpers for the ops postgres store
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


# builds a libpq dsn from parts
def build_dsn(host: str, port: int, db: str, user: str, password: str) -> str:
    return f"host={host} port={port} dbname={db} user={user} password={password}"


# resolves ops connection parts from the environment
def ops_config(prefix: str = "POSTGRES_OPS") -> dict[str, str | int]:
    return {
        "host": os.getenv(f"{prefix}_HOST", "localhost"),
        "port": int(os.getenv(f"{prefix}_PORT", "5432")),
        "db": os.getenv(f"{prefix}_DB", "lotus_ops_dev"),
        "user": os.getenv(f"{prefix}_USER", "lotus_ops"),
        "password": os.getenv(f"{prefix}_PASSWORD", ""),
    }


# reads a sql file as text
def read_sql(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


# stamps every row with the producing run id
def with_batch(df: pd.DataFrame, run_id: str) -> pd.DataFrame:
    out = df.copy()
    out["_batch_id"] = run_id
    return out
