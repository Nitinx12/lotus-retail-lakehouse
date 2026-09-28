# returns page mirroring the r return analysis
import streamlit as st
from lib import charts, db

st.set_page_config(page_title="Returns Lotus Retail", page_icon="↩️", layout="wide")
st.title("Returns")

df = db.get_return_rate_by_product()
if df.empty:
    st.warning("No return data available.")
    st.stop()

z_threshold = st.slider("Outlier z-score threshold", 1.0, 3.0, 1.5, 0.1)
top = df.sort_values("times_returned", ascending=False).head(15)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(charts.return_rate_bar(top, z_threshold), use_container_width=True)
with col2:
    st.plotly_chart(charts.return_pareto(df), use_container_width=True)

st.dataframe(
    df.assign(return_rate=lambda d: (d["return_rate"] * 100).round(2)).rename(
        columns={"return_rate": "return_rate_pct"}
    ),
    use_container_width=True,
)
