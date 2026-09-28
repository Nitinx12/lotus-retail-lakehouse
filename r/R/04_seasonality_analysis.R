source("R/01_load_data.R")

# labels one month as pre ramadan, ramadan, post ramadan or non seasonal
classify_month <- function(month_start, window_months) {
  month_end <- month_start %m+% months(1) - days(1)
  for (i in seq_len(nrow(ramadan_ranges))) {
    start <- ramadan_ranges$start[i]
    end <- ramadan_ranges$end[i]
    if (month_start <= end && month_end >= start) {
      return("Ramadan")
    }
    if (month_end < start && month_end >= start %m-% months(window_months)) {
      return("Pre-Ramadan")
    }
    if (month_start > end && month_start <= end %m+% months(window_months)) {
      return("Post-Ramadan")
    }
  }
  "Non-seasonal"
}

# tags every mart row with its ramadan window period
tag_ramadan_windows <- function(season_df, window_months = 1) {
  month_labels <- tibble(month_start = unique(season_df$month_start)) |>
    mutate(period = vapply(month_start, classify_month, character(1), window_months = window_months))
  season_df |>
    left_join(month_labels, by = "month_start") |>
    mutate(period = factor(period, levels = c("Pre-Ramadan", "Ramadan", "Post-Ramadan", "Non-seasonal")))
}

# compares average revenue across periods with an anova significance test
ramadan_period_comparison <- function(tagged_df) {
  summary_tbl <- tagged_df |>
    group_by(period) |>
    summarise(avg_revenue = mean(revenue), total_orders = sum(orders), n_months = n(), .groups = "drop")
  seasonal_only <- tagged_df |> filter(period != "Non-seasonal") |> mutate(period = droplevels(period))
  group_counts <- table(seasonal_only$period)
  if (length(group_counts) < 2 || any(group_counts < 2)) {
    return(list(summary = summary_tbl, p_value = NA_real_))
  }
  aov_fit <- aov(revenue ~ period, data = seasonal_only)
  list(summary = summary_tbl, p_value = summary(aov_fit)[[1]][["Pr(>F)"]][1])
}

# measures the ramadan revenue lift separately for each year
ramadan_yoy_lift <- function(tagged_df) {
  tagged_df |>
    mutate(year = year(month_start)) |>
    filter(period %in% c("Ramadan", "Non-seasonal")) |>
    group_by(year, period) |>
    summarise(avg_revenue = mean(revenue), .groups = "drop") |>
    pivot_wider(names_from = period, values_from = avg_revenue) |>
    mutate(lift_pct = Ramadan / `Non-seasonal` - 1)
}
