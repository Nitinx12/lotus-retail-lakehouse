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


# inserts a running row for a task
def start_run(cur: object, run_id: str, task: str) -> None:
    cur.execute(
        "INSERT INTO ops.pipeline_runs (run_id, task_name, status) "
        "VALUES (%s, %s, 'running') "
        "ON CONFLICT (run_id, task_name) DO UPDATE SET "
        "status = 'running', started_at = now(), ended_at = NULL, "
        "error_message = NULL",
        (run_id, task),
    )


# marks a task row terminal with counts and an optional error
def finish_run(
    cur: object,
    run_id: str,
    task: str,
    status: str,
    rows_in: int = 0,
    rows_out: int = 0,
    err: str | None = None,
) -> None:
    cur.execute(
        "INSERT INTO ops.pipeline_runs "
        "(run_id, task_name, status, rows_in, rows_out, error_message) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (run_id, task_name) DO UPDATE SET "
        "status = EXCLUDED.status, ended_at = now(), "
        "rows_in = EXCLUDED.rows_in, rows_out = EXCLUDED.rows_out, "
        "error_message = EXCLUDED.error_message",
        (run_id, task, status, rows_in, rows_out, err),
    )


# stamps every row with the producing run id
def with_batch(df: pd.DataFrame, run_id: str) -> pd.DataFrame:
    out = df.copy()
    out["_batch_id"] = run_id
    return out
