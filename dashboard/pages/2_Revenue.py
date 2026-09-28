# revenue page mirroring the r revenue analysis
import streamlit as st
from lib import charts, db

st.set_page_config(page_title="Revenue Lotus Retail", page_icon="💰", layout="wide")
st.title("Revenue")

df = db.get_revenue_by_store_month()
if df.empty:
    st.warning("No revenue data available.")
    st.stop()

stores = sorted(df["store_id"].unique())
selected_stores = st.multiselect("Filter by store", stores, default=stores)
filtered = df[df["store_id"].isin(selected_stores)]

st.plotly_chart(charts.revenue_trend_line(filtered), use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(charts.store_ranking_bar(filtered), use_container_width=True)
with col2:
    st.plotly_chart(charts.revenue_store_heatmap(filtered), use_container_width=True)

with st.expander("Raw data"):
    st.dataframe(filtered, use_container_width=True)
