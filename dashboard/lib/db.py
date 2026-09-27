# shared postgres readers for the dashboard
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg2

IST = ZoneInfo("Asia/Kolkata")


# builds a libpq dsn through the pooler for any database on the server
def pool_dsn(db: str, user: str, password: str) -> str:
    return (
        f"host={os.getenv('POSTGRES_GOLD_POOL_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_GOLD_POOL_PORT', '6432')} "
        f"dbname={db} user={user} password={password}"
    )


# opens a pooled connection to the gold serving database
def gold_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=pool_dsn(
            os.getenv("POSTGRES_GOLD_DB", "lotus_gold_dev"),
            os.getenv("POSTGRES_GOLD_USER", "lotus_app"),
            os.getenv("POSTGRES_GOLD_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# opens a pooled connection to the ops database
def ops_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=pool_dsn(
            os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev"),
            os.getenv("POSTGRES_OPS_USER", "lotus_ops"),
            os.getenv("POSTGRES_OPS_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# reads a query into a frame
def read_frame(dsn: str, sql: str) -> pd.DataFrame:
    with psycopg2.connect(dsn=dsn, connect_timeout=5) as conn:
        return pd.read_sql(sql, conn)


# decides whether gold missed the 7am ist refresh sla
def gold_stale(now_utc: datetime, last_gold_end: datetime | None) -> bool:
    now_ist = now_utc.astimezone(IST)
    deadline_ist = now_ist.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_ist < deadline_ist:
        deadline_ist = deadline_ist - pd.Timedelta(days=1)
    if last_gold_end is None:
        return True
    end_ist = last_gold_end.astimezone(IST)
    return end_ist < deadline_ist
