suppressPackageStartupMessages({
  library(DBI)
  library(RPostgres)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  library(ggplot2)
  library(scales)
  library(glue)
  library(forecast)
  library(kableExtra)
})

lotus_env <- Sys.getenv("LOTUS_ENV", unset = "dev")
mart_schema <- Sys.getenv("LOTUS_MART_SCHEMA", unset = "marts")

mart_revenue <- "revenue_by_store_month"
mart_returns <- "return_rate_by_product"
mart_season <- "ramadan_seasonality"

report_currency <- "EGP"
report_dir <- Sys.getenv("REPORT_OUTPUT_DIR", unset = file.path("output", lotus_env, "report"))

# returns the first set env var in names, else the default
db_setting <- function(names, default = "") {
  for (name in names) {
    value <- Sys.getenv(name, unset = "")
    if (value != "") {
      return(value)
    }
  }
  default
}

# qualifies a dbt mart name with the configured schema for safe queries
mart_relation <- function(mart) {
  paste0('"', mart_schema, '"."', mart, '"')
}

# opens the serving warehouse through the pooler, NULL when creds are missing
connect_lotus_db <- function() {
  host <- db_setting(c("POSTGRES_GOLD_POOL_HOST", "POSTGRES_GOLD_HOST", "LOTUS_PGHOST"), "localhost")
  port <- db_setting(c("POSTGRES_GOLD_POOL_PORT", "POSTGRES_GOLD_PORT", "LOTUS_PGPORT"), "6432")
  dbname <- db_setting(c("POSTGRES_GOLD_DB", "LOTUS_PGDATABASE"), "lotus_gold_dev")
  user <- db_setting(c("POSTGRES_GOLD_USER", "LOTUS_PGUSER"), "lotus_app")
  password <- db_setting(c("POSTGRES_GOLD_PASSWORD", "LOTUS_PGPASSWORD"), "")
  if (password == "") {
    return(NULL)
  }
  DBI::dbConnect(
    RPostgres::Postgres(),
    host = host,
    port = as.integer(port),
    dbname = dbname,
    user = user,
    password = password,
    sslmode = if (lotus_env == "prod") "require" else "prefer"
  )
}

ramadan_ranges <- tibble::tribble(
  ~year, ~start, ~end,
  2022L, "2022-04-02", "2022-05-01",
  2023L, "2023-03-23", "2023-04-20",
  2024L, "2024-03-11", "2024-04-08"
) |>
  mutate(start = as_date(start), end = as_date(end))

# resolves an output path under the report dir, creating folders as needed
out_dir <- function(...) {
  path <- file.path(report_dir, ...)
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  path
}
