# lotus retail home page over the governed dbt marts
from __future__ import annotations

import streamlit as st
from lib import charts, db

st.set_page_config(page_title="Lotus Retail", page_icon="🏬", layout="wide")
st.title("Lotus Retail")

freshness = db.get_gold_freshness_hours()
if db.is_stale(freshness):
    st.error("Gold is stale, check the Ops page for the latest run.")
else:
    st.success(f"Gold is fresh, last refreshed {freshness:.1f}h ago.")

rev = db.get_revenue_by_store_month()
if rev.empty:
    st.warning("No revenue data available.")
    st.stop()

total_revenue = rev["revenue"].sum()
total_orders = rev["orders"].sum()
top_store = rev.groupby("store_id")["revenue"].sum().idxmax()

ret = db.get_return_rate_by_product()
mean_rate = ret["return_rate"].mean() if not ret.empty else 0.0

cards = st.columns(3)
with cards[0]:
    charts.kpi_delta("Total revenue", f"EGP {total_revenue:,.0f}")
with cards[1]:
    charts.kpi_delta("Total orders", f"{int(total_orders):,}")
with cards[2]:
    charts.kpi_delta("Mean return rate", f"{mean_rate:.2%}")

st.plotly_chart(charts.revenue_trend_line(rev), use_container_width=True)
st.plotly_chart(charts.store_ranking_bar(rev), use_container_width=True)

masked = db.get_customers_masked()
st.caption(f"Masked customer records available: {len(masked):,}.")
