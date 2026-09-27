# pipeline ops view over runs quality and schema changes
from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from lib.db import gold_stale, pool_dsn, read_frame


# loads the three ops tables through the pooler
def load_ops(dsn: str) -> dict:
    return {
        "runs": read_frame(
            dsn, "SELECT * FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT 500"
        ),
        "quality": read_frame(
            dsn, "SELECT * FROM ops.quality_results ORDER BY checked_at DESC LIMIT 200"
        ),
        "schemas": read_frame(
            dsn, "SELECT * FROM ops.schema_changes ORDER BY detected_at DESC LIMIT 100"
        ),
    }


st.title("Pipeline Ops")
dsn = pool_dsn(
    os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev"),
    os.getenv("POSTGRES_OPS_USER", "lotus_ops"),
    os.getenv("POSTGRES_OPS_PASSWORD", ""),
)
ops = load_ops(dsn)
runs = ops["runs"]

st.header("Task status")
latest = runs.sort_values("started_at").drop_duplicates("task_name", keep="last")
st.dataframe(latest[["task_name", "status", "started_at", "ended_at"]])

st.header("Freshness")
gold_rows = runs[(runs["task_name"] == "gold") & (runs["status"] == "success")]
last_gold = gold_rows["ended_at"].max() if len(gold_rows) else None
if last_gold is not None and getattr(last_gold, "tzinfo", None) is None:
    last_gold = last_gold.replace(tzinfo=UTC)
stale = gold_stale(datetime.now(UTC), last_gold)
if stale:
    st.error("Gold is older than the 7am IST refresh SLA")
else:
    st.success("Gold is within the 7am IST refresh SLA")

st.header("Duration per task")
done = runs[runs["ended_at"].notna()].copy()
done["seconds"] = (done["ended_at"] - done["started_at"]).dt.total_seconds()
st.bar_chart(done.groupby("task_name")["seconds"].mean())

st.header("Row count trend")
st.line_chart(runs.groupby("started_at")["rows_out"].sum())

st.header("Quality pass rate")
st.line_chart(ops["quality"].groupby("checked_at")["success_percent"].mean())

st.header("Schema changes")
st.dataframe(ops["schemas"])
