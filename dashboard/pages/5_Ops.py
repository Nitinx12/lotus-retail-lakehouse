# ops page over runs quality and schema changes
import pandas as pd
import streamlit as st
from lib import config, db

st.set_page_config(page_title="Ops Lotus Retail", page_icon="🛠️", layout="wide")
st.title("Pipeline Ops")

freshness = db.get_gold_freshness_hours()
if db.is_stale(freshness):
    st.error(f"Gold is stale, SLA is {config.GOLD_FRESHNESS_SLA_HOURS}h.")
elif freshness is not None:
    st.success(f"Gold is fresh, last refreshed {freshness:.1f}h ago.")

runs = db.get_pipeline_runs()
if not runs.empty:
    latest_per_task = runs.sort_values("started_at").groupby("task_name").tail(1)
    cols = st.columns(min(len(latest_per_task), 6) or 1)
    for i, (_, row) in enumerate(latest_per_task.iterrows()):
        icon = {"success": "✅", "failed": "❌", "running": "🔄"}.get(
            row["status"], "❔"
        )
        cols[i % len(cols)].metric(row["task_name"], f"{icon} {row['status']}")

    st.divider()

    runs["duration_min"] = (
        pd.to_datetime(runs["ended_at"]) - pd.to_datetime(runs["started_at"])
    ).dt.total_seconds() / 60
    st.subheader("Task duration (most recent runs)")
    st.bar_chart(runs.groupby("task_name")["duration_min"].mean())

    st.subheader("Row count trend")
    row_trend = runs.pivot_table(
        index="started_at", columns="task_name", values="rows_out", aggfunc="sum"
    )
    st.line_chart(row_trend)

    failed = runs[runs["status"] == "failed"].head(20)
    if not failed.empty:
        st.subheader("Recent failures")
        st.dataframe(
            failed[["task_name", "started_at", "error_message"]],
            use_container_width=True,
        )
else:
    st.info("No pipeline runs recorded yet.")

st.divider()

quality = db.get_quality_results()
if not quality.empty:
    st.subheader("Quality test pass rate")
    pivot = quality.pivot_table(
        index="checked_at", columns="suite_name", values="success_percent"
    )
    st.line_chart(pivot)
else:
    st.info("No quality results recorded yet.")

st.divider()

schema_changes = db.get_schema_changes()
if not schema_changes.empty:
    st.subheader("Recent schema changes")
    st.dataframe(schema_changes, use_container_width=True)
else:
    st.caption("No schema changes detected recently.")
