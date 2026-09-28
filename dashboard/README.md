# Lotus Retail Dashboard

Streamlit views over the dbt governed marts plus the pipeline ops page.
Run from the repo root so `dashboard` stays importable:

```bash
uv sync
uv run streamlit run dashboard/app.py
```

## Layout

`app.py` is the landing page with KPIs and the freshness banner.
`lib/config.py` holds env driven settings with pooler first defaults.
`lib/db.py` owns one pooled engine per server process plus cached queries.
`lib/charts.py` holds shared Plotly builders in one visual identity.
`pages/` holds Revenue, Returns, Seasonality, and Ops views.

## Data

Pages read `marts.revenue_by_store_month`, `marts.return_rate_by_product`,
and `marts.ramadan_seasonality`, built by dbt after the Gold refresh.
Set the warehouse credentials through the pooler vars:

```bash
export POSTGRES_GOLD_POOL_HOST=localhost POSTGRES_GOLD_POOL_PORT=6432
export POSTGRES_GOLD_DB=lotus_gold_dev POSTGRES_GOLD_USER=lotus_app
export POSTGRES_GOLD_PASSWORD=secret
```

Without a reachable warehouse every query returns an empty frame and the
page shows a warning instead of failing.

## PII

General pages only read `gold.dim_customers_masked`. Nothing outside an
access controlled ops path may query the unmasked customer table.

## Ops page

The Ops page is read only history for browsing runs, quality pass rate,
and schema changes. Alerts fire independently through the Airflow
callback, never through this page.

## Auth

Nothing here gates access yet. Put the dashboard behind a reverse proxy
with SSO headers or add an authenticator package, then use
`config.PII_ROLES` to gate any future unmasked PII page.
