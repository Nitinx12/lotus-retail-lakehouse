# Lotus Retail R Analysis and Reporting Layer

This is `A10` (R analysis) and `A11` (LaTeX report build) from the Airflow DAG
in `ARCHITECTURE.md`.

## Structure

`R/00_config.R` owns shared setup: library block, environment selector,
warehouse connection, dbt mart names, Ramadan date ranges, and output paths.

`R/01_load_data.R` reads the dbt governed marts from the `marts` schema and
normalizes month and numeric types. R never recomputes mart logic, so these
numbers cannot drift from the dashboard.

`R/02_revenue_analysis.R` builds trend summaries, STL decomposition, store
concentration, and a directional forecast from the revenue mart.

`R/03_return_analysis.R` builds outlier flags, Pareto views, and benchmark
tests from the return rate mart at product grain.

`R/04_seasonality_analysis.R` tags Ramadan windows from explicit Gregorian
ranges and compares revenue across periods with ANOVA plus yearly lift.

`R/05_chart_theme.R` owns the single shared chart theme, palette, and
formatters used by every figure.

`analysis.qmd` is the working analyst copy with all code visible.
`report.qmd` is the curated stakeholder report rendered to PDF.
`templates/preamble.tex` styles the PDF.

## Running locally

Set the warehouse credentials (or leave the password unset to run on
seeded demo data), then render from this directory:

```bash
export POSTGRES_GOLD_POOL_HOST=localhost POSTGRES_GOLD_POOL_PORT=6432
export POSTGRES_GOLD_DB=lotus_gold_dev POSTGRES_GOLD_USER=lotus_app POSTGRES_GOLD_PASSWORD=secret
export LOTUS_ENV=dev LOTUS_MART_SCHEMA=marts REPORT_OUTPUT_DIR=./reports
quarto render analysis.qmd
quarto render report.qmd
```

If the password is missing, loaders fall back to seeded demo data
automatically, so chart design stays reviewable before the warehouse is live.
Figures land under `REPORT_OUTPUT_DIR/figures`.
