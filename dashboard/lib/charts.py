# shared plotly builders in the lotus visual identity
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .config import CURRENCY_PREFIX, PALETTE

_SEQ = [
    PALETTE["navy"],
    PALETTE["blue"],
    PALETTE["lightblue"],
    PALETTE["magenta"],
    PALETTE["orange"],
    PALETTE["green"],
    PALETTE["grey"],
]


# applies the single lotus layout to a figure
def _layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        font={"family": "sans-serif", "size": 13},
        margin={"l": 40, "r": 20, "t": 50 if title else 20, "b": 40},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    return fig


# draws the company wide monthly revenue line
def revenue_trend_line(df: pd.DataFrame) -> go.Figure:
    monthly = df.groupby("month", as_index=False)["revenue"].sum()
    fig = px.line(
        monthly,
        x="month",
        y="revenue",
        markers=True,
        color_discrete_sequence=[PALETTE["navy"]],
    )
    fig.update_yaxes(tickprefix=CURRENCY_PREFIX, tickformat=",.0f")
    return _layout(fig, "Monthly Revenue")


# draws the store by month revenue heatmap
def revenue_store_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = df.pivot_table(
        index="store_id", columns="month", values="revenue", aggfunc="sum"
    )
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        labels={"color": "Revenue"},
    )
    return _layout(fig, "Revenue by Store x Month")


# draws ranked store revenue with the top stores highlighted
def store_ranking_bar(df: pd.DataFrame, top_n: int = 3) -> go.Figure:
    by_store = (
        df.groupby("store_id", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )
    by_store["highlight"] = [
        "Top" if i < top_n else "Other" for i in range(len(by_store))
    ]
    fig = px.bar(
        by_store,
        x="store_id",
        y="revenue",
        color="highlight",
        color_discrete_map={"Top": PALETTE["navy"], "Other": PALETTE["lightblue"]},
    )
    fig.update_yaxes(tickprefix=CURRENCY_PREFIX, tickformat=",.0f")
    return _layout(fig, "Revenue by Store")


# draws product return rates with portfolio outliers flagged
def return_rate_bar(df: pd.DataFrame, z_threshold: float = 1.5) -> go.Figure:
    d = df.copy()
    mu = d["return_rate"].mean()
    sd = d["return_rate"].std()
    if pd.isna(sd) or sd == 0:
        d["flag"] = False
    else:
        d["flag"] = ((d["return_rate"] - mu) / sd).abs() > z_threshold
    d = d.sort_values("return_rate")
    fig = px.bar(
        d,
        x="return_rate",
        y="product_id",
        orientation="h",
        color="flag",
        color_discrete_map={True: PALETTE["magenta"], False: PALETTE["blue"]},
    )
    fig.add_vline(x=mu, line_dash="dash", line_color="grey")
    fig.update_xaxes(tickformat=".1%")
    fig.update_layout(showlegend=False)
    return _layout(fig, "Return Rate by Product")


# draws return volume pareto with cumulative share
def return_pareto(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("times_returned", ascending=False).copy()
    d["cum_share"] = d["times_returned"].cumsum() / d["times_returned"].sum()
    fig = go.Figure()
    fig.add_bar(
        x=d["product_id"],
        y=d["times_returned"],
        marker_color=PALETTE["lightblue"],
        name="Returns",
    )
    fig.add_scatter(
        x=d["product_id"],
        y=d["cum_share"] * d["times_returned"].max(),
        yaxis="y2",
        mode="lines+markers",
        marker_color=PALETTE["magenta"],
        name="Cumulative share",
    )
    fig.update_layout(
        yaxis2={
            "overlaying": "y",
            "side": "right",
            "tickformat": ".0%",
            "range": [0, 1.05],
        }
    )
    return _layout(fig, "Return Volume Pareto")


# draws monthly revenue across ramadan windows
def seasonality_boxplot(df: pd.DataFrame) -> go.Figure:
    fig = px.box(
        df[df["period"] != "Non-seasonal"],
        x="period",
        y="revenue",
        color="period",
        color_discrete_sequence=_SEQ,
    )
    fig.update_yaxes(tickprefix=CURRENCY_PREFIX, tickformat=",.0f")
    fig.update_layout(showlegend=False)
    return _layout(fig, "Monthly Revenue by Ramadan Window")


# renders one kpi card the same way on every page
def kpi_delta(label: str, value: str, delta: str | None = None) -> None:
    st.metric(label, value, delta)
