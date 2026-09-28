source("R/01_load_data.R")

# aggregates company wide monthly revenue with growth and margin
revenue_trend_summary <- function(rev_df) {
  rev_df |>
    group_by(month_start) |>
    summarise(revenue = sum(revenue), cost = sum(cost), orders = sum(orders), .groups = "drop") |>
    arrange(month_start) |>
    mutate(
      margin = (revenue - cost) / revenue,
      mom_growth = revenue / lag(revenue) - 1,
      yoy_growth = revenue / lag(revenue, 12) - 1
    )
}

# decomposes the company wide monthly series into trend seasonal remainder
revenue_stl_decomposition <- function(rev_df) {
  monthly <- rev_df |>
    group_by(month_start) |>
    summarise(revenue = sum(revenue), .groups = "drop") |>
    arrange(month_start)
  if (nrow(monthly) < 24 || any(is.na(monthly$revenue))) {
    stop("stl decomposition needs at least 24 complete months of revenue")
  }
  ts_obj <- ts(monthly$revenue,
    start = c(year(min(monthly$month_start)), month(min(monthly$month_start))),
    frequency = 12
  )
  list(monthly = monthly, stl = stl(ts_obj, s.window = "periodic", robust = TRUE))
}

# measures what share of revenue the top n stores contribute
store_concentration <- function(rev_df, top_n = 3) {
  by_store <- rev_df |>
    group_by(store_id) |>
    summarise(revenue = sum(revenue), .groups = "drop") |>
    arrange(desc(revenue)) |>
    mutate(share = revenue / sum(revenue), cum_share = cumsum(share), rank = row_number())
  top_share <- by_store |>
    filter(rank <= top_n) |>
    summarise(share = sum(share)) |>
    pull(share)
  list(by_store = by_store, top_n = top_n, top_n_share = top_share)
}

# forecasts revenue per store with ets, naive flat line on short history
forecast_single_store <- function(df, h) {
  df <- arrange(df, month_start)
  if (nrow(df) < 8 || any(is.na(df$revenue))) {
    last_value <- df$revenue[nrow(df)]
    return(tibble(
      month_start = seq(max(df$month_start) %m+% months(1), by = "month", length.out = h),
      forecast = rep(last_value, h),
      lo_80 = rep(NA_real_, h),
      hi_80 = rep(NA_real_, h)
    ))
  }
  ts_obj <- ts(df$revenue,
    start = c(year(min(df$month_start)), month(min(df$month_start))),
    frequency = 12
  )
  fc <- forecast::forecast(forecast::ets(ts_obj), h = h)
  tibble(
    month_start = seq(max(df$month_start) %m+% months(1), by = "month", length.out = h),
    forecast = as.numeric(fc$mean),
    lo_80 = as.numeric(fc$lower[, "80%"]),
    hi_80 = as.numeric(fc$upper[, "80%"])
  )
}

# builds a directional h month forecast for every store
revenue_forecast_by_store <- function(rev_df, h = 3) {
  rev_df |>
    group_by(store_id) |>
    group_modify(function(df, key) forecast_single_store(df, h)) |>
    ungroup()
}
