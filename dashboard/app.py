# lotus retail view over the governed dbt marts
from __future__ import annotations

import os

import streamlit as st
from lib.db import pool_dsn, read_frame


# loads the marts through the pooler
def load_marts(dsn: str) -> dict:
    return {
        "revenue": read_frame(
            dsn, "SELECT * FROM marts.revenue_by_store_month ORDER BY month"
        ),
        "returns": read_frame(
            dsn, "SELECT * FROM marts.return_rate_by_product ORDER BY return_rate DESC"
        ),
        "ramadan": read_frame(
            dsn, "SELECT * FROM marts.ramadan_seasonality ORDER BY month"
        ),
        "customers": read_frame(
            dsn, "SELECT count(*) AS masked_customers FROM gold.dim_customers_masked"
        ),
    }


st.title("Lotus Retail")
dsn = pool_dsn(
    os.getenv("POSTGRES_GOLD_DB", "lotus_gold_dev"),
    os.getenv("POSTGRES_GOLD_USER", "lotus_app"),
    os.getenv("POSTGRES_GOLD_PASSWORD", ""),
)
marts = load_marts(dsn)

st.header("Revenue by store and month")
st.dataframe(marts["revenue"])
st.bar_chart(marts["revenue"].groupby("month")["revenue"].sum())

st.header("Return rate by product")
st.dataframe(marts["returns"].head(20))

st.header("Ramadan seasonality")
st.dataframe(marts["ramadan"])
st.bar_chart(marts["ramadan"].groupby("month")["revenue"].sum())

st.header("Masked customers")
st.dataframe(marts["customers"])
