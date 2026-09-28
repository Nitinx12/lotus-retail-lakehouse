source("R/00_config.R")

set.seed(42)

# stops with a clear message when expected mart columns are missing
require_columns <- function(df, cols, mart) {
  missing <- setdiff(cols, names(df))
  if (length(missing) > 0) {
    stop(glue("mart {mart} is missing columns: {paste(missing, collapse = ', ')}"))
  }
  df
}

# parses a YYYY-MM month string from dbt into a first of month date
parse_mart_month <- function(month) {
  suppressWarnings(lubridate::ymd(paste0(trimws(as.character(month)), "-01")))
}

# reads the dbt revenue mart and normalizes month and numeric types
get_revenue_by_store_month <- function(con = NULL) {
  if (!is.null(con)) {
    df <- DBI::dbGetQuery(con, paste0("SELECT * FROM ", mart_relation(mart_revenue)))
    df <- require_columns(df, c("store_id", "month", "revenue", "cost", "orders"), mart_revenue)
    return(df |> mutate(
      month_start = parse_mart_month(month),
      revenue = as.numeric(revenue),
      cost = as.numeric(cost),
      orders = as.integer(orders)
    ))
  }
  stores <- paste0("Store_", sprintf("%02d", 1:12))
  months <- seq(as_date("2022-01-01"), as_date("2024-12-01"), by = "month")
  expand_grid(store_id = stores, month_start = months) |>
    mutate(
      base = 180000 + as.integer(factor(store_id)) * 9000,
      trend = as.numeric(month_start - min(month_start)) * 12,
      seasonal = 25000 * sin(2 * pi * month(month_start) / 12),
      noise = rnorm(n(), 0, 12000),
      revenue = pmax(base + trend + seasonal + noise, 0),
      cost = pmax(revenue * rnorm(n(), 0.62, 0.04), 0),
      orders = pmax(round(revenue / rnorm(n(), 420, 30)), 0),
      month = format(month_start, "%Y-%m")
    ) |>
    select(store_id, month, month_start, revenue, cost, orders)
}

# reads the dbt return rate mart and normalizes numeric types
get_return_rate_by_product <- function(con = NULL) {
  if (!is.null(con)) {
    df <- DBI::dbGetQuery(con, paste0("SELECT * FROM ", mart_relation(mart_returns)))
    df <- require_columns(df, c("product_id", "times_ordered", "times_returned", "return_rate"), mart_returns)
    return(df |> mutate(
      times_ordered = as.integer(times_ordered),
      times_returned = as.integer(times_returned),
      return_rate = as.numeric(return_rate)
    ))
  }
  base_rates <- c(0.11, 0.08, 0.05, 0.02, 0.07, 0.06)
  tibble(product_id = paste0("P", sprintf("%04d", 1:60))) |>
    mutate(
      times_ordered = round(runif(n(), 300, 4000)),
      base_rate = rep(base_rates, length.out = n()),
      times_returned = pmax(round(times_ordered * (base_rate + rnorm(n(), 0, 0.01))), 0),
      return_rate = times_returned / pmax(times_ordered, 1)
    ) |>
    select(product_id, times_ordered, times_returned, return_rate)
}

# reads the dbt ramadan mart and normalizes month and flag types
get_ramadan_seasonality <- function(con = NULL) {
  if (!is.null(con)) {
    df <- DBI::dbGetQuery(con, paste0("SELECT * FROM ", mart_relation(mart_season)))
    df <- require_columns(df, c("month", "is_ramadan", "revenue", "orders"), mart_season)
    return(df |> mutate(
      month_start = parse_mart_month(month),
      is_ramadan = as.logical(is_ramadan),
      revenue = as.numeric(revenue),
      orders = as.integer(orders)
    ))
  }
  months <- seq(as_date("2022-01-01"), as_date("2024-12-01"), by = "month")
  tibble(month_start = months) |>
    mutate(
      month_end = month_start %m+% months(1) - days(1),
      is_ramadan = vapply(seq_along(month_start), function(i) {
        any(month_start[i] <= ramadan_ranges$end & month_end[i] >= ramadan_ranges$start)
      }, logical(1)),
      base = 660000,
      lift = ifelse(is_ramadan, 270000, 0),
      noise = rnorm(n(), 0, 40000),
      revenue = pmax(base + lift + noise, 0),
      orders = pmax(round(revenue / rnorm(n(), 420, 30)), 0),
      month = format(month_start, "%Y-%m")
    ) |>
    select(month, month_start, is_ramadan, revenue, orders)
}

# connects when creds exist, else NULL so every getter uses demo data
get_lotus_connection <- function() {
  tryCatch(connect_lotus_db(), error = function(e) NULL)
}
