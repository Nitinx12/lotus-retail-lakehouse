# pooled postgres readers over the governed dbt marts
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from . import config

logger = logging.getLogger("lotus.dashboard")

REVENUE_MART = f"{config.MART_SCHEMA}.revenue_by_store_month"
RETURNS_MART = f"{config.MART_SCHEMA}.return_rate_by_product"
SEASON_MART = f"{config.MART_SCHEMA}.ramadan_seasonality"
MASKED_CUSTOMERS = "gold.dim_customers_masked"

RAMADAN_RANGES = {
    2022: ("2022-04-02", "2022-05-01"),
    2023: ("2023-03-23", "2023-04-20"),
    2024: ("2024-03-11", "2024-04-08"),
}


# builds the sqlalchemy url for the pooler without connecting
def engine_url() -> str:
    return (
        f"postgresql+psycopg2://{config.PG_USER}:{config.PG_PASSWORD}"
        f"@{config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}"
        f"?sslmode={config.PG_SSLMODE}"
    )


# returns true when gold is older than the sla
def is_stale(
    freshness_hours: float | None,
    sla_hours: int = config.GOLD_FRESHNESS_SLA_HOURS,
) -> bool:
    return freshness_hours is None or freshness_hours > sla_hours


# tags one month pre ramadan ramadan post ramadan or non seasonal
def tag_ramadan_period(month_start: pd.Timestamp, window_months: int = 1) -> str:
    month_end = month_start + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)
    for start_text, end_text in RAMADAN_RANGES.values():
        start = pd.Timestamp(start_text)
        end = pd.Timestamp(end_text)
        if month_start <= end and month_end >= start:
            return "Ramadan"
        window = pd.DateOffset(months=window_months)
        if month_end < start and month_end >= start - window:
            return "Pre-Ramadan"
        if month_start > end and month_start <= end + window:
            return "Post-Ramadan"
    return "Non-seasonal"


# opens one pooled engine per server process through pgbouncer
@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    if not config.PG_PASSWORD:
        logger.warning("Gold password not set, dashboard cannot reach Postgres.")
    return create_engine(engine_url(), pool_size=5, max_overflow=5, pool_pre_ping=True)


# runs one read query returning an empty frame on failure
def _run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    try:
        with get_engine().connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception:
        logger.exception("Query failed: %s", sql[:200])
        st.error(
            "Could not reach the data warehouse. Postgres or PgBouncer may be "
            "unreachable, or the Gold refresh has not run yet."
        )
        return pd.DataFrame()


# reads the dbt revenue mart
@st.cache_data(ttl=config.DATA_TTL_SECONDS, show_spinner="Loading revenue data...")
def get_revenue_by_store_month() -> pd.DataFrame:
    return _run_query(f"SELECT * FROM {REVENUE_MART}")


# reads the dbt return rate mart
@st.cache_data(ttl=config.DATA_TTL_SECONDS, show_spinner="Loading return data...")
def get_return_rate_by_product() -> pd.DataFrame:
    return _run_query(f"SELECT * FROM {RETURNS_MART}")


# reads the dbt ramadan seasonality mart
@st.cache_data(ttl=config.DATA_TTL_SECONDS, show_spinner="Loading seasonality data...")
def get_ramadan_seasonality() -> pd.DataFrame:
    return _run_query(f"SELECT * FROM {SEASON_MART}")


# reads the masked customer view keeping pii out of bi pages
@st.cache_data(ttl=config.DATA_TTL_SECONDS, show_spinner="Loading customers...")
def get_customers_masked() -> pd.DataFrame:
    return _run_query(f"SELECT * FROM {MASKED_CUSTOMERS}")


# reads recent pipeline runs for the ops page
@st.cache_data(ttl=config.OPS_TTL_SECONDS, show_spinner=False)
def get_pipeline_runs(limit: int = 500) -> pd.DataFrame:
    return _run_query(
        "SELECT * FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT :limit",
        {"limit": limit},
    )


# reads recent quality results for the ops page
@st.cache_data(ttl=config.OPS_TTL_SECONDS, show_spinner=False)
def get_quality_results(limit: int = 500) -> pd.DataFrame:
    return _run_query(
        "SELECT * FROM ops.quality_results ORDER BY checked_at DESC LIMIT :limit",
        {"limit": limit},
    )


# reads recent schema changes for the ops page
@st.cache_data(ttl=config.OPS_TTL_SECONDS, show_spinner=False)
def get_schema_changes(limit: int = 200) -> pd.DataFrame:
    return _run_query(
        "SELECT * FROM ops.schema_changes ORDER BY detected_at DESC LIMIT :limit",
        {"limit": limit},
    )


# returns hours since the last successful gold or publish run
@st.cache_data(ttl=config.OPS_TTL_SECONDS, show_spinner=False)
def get_gold_freshness_hours() -> float | None:
    df = _run_query(
        "SELECT ended_at FROM ops.pipeline_runs "
        "WHERE task_name IN ('gold', 'publish') AND status = 'success' "
        "ORDER BY ended_at DESC LIMIT 1"
    )
    if df.empty:
        return None
    last = pd.to_datetime(df.iloc[0]["ended_at"], utc=True)
    return (pd.Timestamp.now(tz="UTC") - last).total_seconds() / 3600
