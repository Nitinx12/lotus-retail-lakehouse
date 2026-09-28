source("R/01_load_data.R")

# flags products whose return rate is an outlier against the portfolio
return_rate_outliers <- function(ret_df, z_threshold = 1.5) {
  mu <- mean(ret_df$return_rate, na.rm = TRUE)
  sd_ <- sd(ret_df$return_rate, na.rm = TRUE)
  if (is.na(sd_) || sd_ == 0) {
    return(ret_df |> mutate(z_score = NA_real_, flagged = FALSE) |> arrange(desc(return_rate)))
  }
  ret_df |>
    mutate(z_score = (return_rate - mu) / sd_, flagged = abs(z_score) > z_threshold) |>
    arrange(desc(return_rate))
}

# ranks products by return volume with cumulative share of total returns
return_volume_pareto <- function(ret_df) {
  ret_df |>
    arrange(desc(times_returned)) |>
    mutate(share = times_returned / sum(times_returned), cum_share = cumsum(share))
}

# keeps the top n products by return volume for readable charts
top_return_products <- function(ret_df, top_n = 15) {
  ret_df |> slice_max(times_returned, n = min(top_n, nrow(ret_df)))
}

# tests the portfolio return rate against a benchmark rate
return_rate_vs_benchmark <- function(ret_df, benchmark_rate) {
  rates <- ret_df$return_rate[!is.na(ret_df$return_rate)]
  if (length(rates) < 2) {
    stop("benchmark test needs at least 2 products with a return rate")
  }
  test <- t.test(rates, mu = benchmark_rate)
  list(
    portfolio_rate = mean(rates),
    benchmark_rate = benchmark_rate,
    p_value = test$p.value,
    significant = test$p.value < 0.05
  )
}
