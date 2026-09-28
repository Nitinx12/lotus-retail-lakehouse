# seasonality page mirroring the r seasonality analysis
import pandas as pd
import streamlit as st
from lib import charts, db

st.set_page_config(page_title="Seasonality Lotus Retail", page_icon="🌙", layout="wide")
st.title("Ramadan Seasonality")

df = db.get_ramadan_seasonality()
if df.empty:
    st.warning("No seasonality data available.")
    st.stop()

df["month_start"] = pd.to_datetime(df["month"])
df["period"] = df["month_start"].apply(db.tag_ramadan_period)

st.plotly_chart(charts.seasonality_boxplot(df), use_container_width=True)

summary = (
    df[df["period"] != "Non-seasonal"]
    .groupby("period", as_index=False)["revenue"]
    .mean()
)
st.dataframe(
    summary.rename(columns={"revenue": "avg_monthly_revenue"}),
    use_container_width=True,
)

st.caption(
    "Periods come from explicit Gregorian Ramadan ranges, never from a fixed "
    "calendar month. See the R deep dive notebook for the significance test."
)
