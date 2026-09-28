# unit tests for dashboard helpers and charts
import pandas as pd
import plotly.graph_objects as go
import pytest

from dashboard.lib import charts, config, db


# checks the engine url points through the pooler with an ssl mode
def test_engine_url() -> None:
    url = db.engine_url()
    assert url.startswith("postgresql+psycopg2://")
    assert f"@{config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE}" in url
    assert "sslmode=" in url


# checks mart relations match the dbt governed names
def test_mart_relations() -> None:
    assert db.REVENUE_MART == f"{config.MART_SCHEMA}.revenue_by_store_month"
    assert db.RETURNS_MART == f"{config.MART_SCHEMA}.return_rate_by_product"
    assert db.SEASON_MART == f"{config.MART_SCHEMA}.ramadan_seasonality"


# checks stale flags missing or over sla freshness
def test_is_stale() -> None:
    assert db.is_stale(None) is True
    assert db.is_stale(25.0, sla_hours=24) is True
    assert db.is_stale(5.0, sla_hours=24) is False


# checks ramadan month tagging against the explicit ranges
def test_tag_ramadan_period() -> None:
    assert db.tag_ramadan_period(pd.Timestamp("2023-04-01")) == "Ramadan"
    assert db.tag_ramadan_period(pd.Timestamp("2023-02-01")) == "Pre-Ramadan"
    assert db.tag_ramadan_period(pd.Timestamp("2023-05-01")) == "Post-Ramadan"
    assert db.tag_ramadan_period(pd.Timestamp("2023-07-01")) == "Non-seasonal"


# builds a revenue frame matching the mart schema
@pytest.fixture
def revenue_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "store_id": ["S1", "S1", "S2", "S2"],
            "month": ["2024-01", "2024-02", "2024-01", "2024-02"],
            "revenue": [100.0, 200.0, 300.0, 400.0],
            "cost": [60.0, 120.0, 180.0, 240.0],
            "orders": [10, 20, 30, 40],
        }
    )


# builds a return frame matching the mart schema
@pytest.fixture
def returns_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": [f"P{i}" for i in range(6)],
            "times_ordered": [1000, 900, 800, 700, 600, 500],
            "times_returned": [110, 72, 40, 14, 42, 30],
            "return_rate": [0.11, 0.08, 0.05, 0.02, 0.07, 0.06],
        }
    )


# checks revenue charts return figures
def test_revenue_charts(revenue_df: pd.DataFrame) -> None:
    assert isinstance(charts.revenue_trend_line(revenue_df), go.Figure)
    assert isinstance(charts.revenue_store_heatmap(revenue_df), go.Figure)
    assert isinstance(charts.store_ranking_bar(revenue_df), go.Figure)


# checks return charts return figures
def test_return_charts(returns_df: pd.DataFrame) -> None:
    assert isinstance(charts.return_rate_bar(returns_df), go.Figure)
    assert isinstance(charts.return_pareto(returns_df), go.Figure)


# checks the seasonality chart returns a figure
def test_seasonality_chart() -> None:
    df = pd.DataFrame(
        {
            "period": ["Ramadan", "Pre-Ramadan", "Ramadan", "Non-seasonal"],
            "revenue": [900.0, 600.0, 950.0, 620.0],
        }
    )
    assert isinstance(charts.seasonality_boxplot(df), go.Figure)
