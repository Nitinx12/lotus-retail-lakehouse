lotus_palette <- c(
  "#1B4B66", "#2E86AB", "#5DA9C4", "#A23B72",
  "#D68C45", "#3A7D44", "#8E8E8E"
)

# applies the single lotus visual identity to a ggplot
theme_lotus <- function(base_size = 11) {
  theme_minimal(base_size = base_size, base_family = "sans") +
    theme(
      plot.title = element_text(face = "bold", size = rel(1.15), margin = margin(b = 4)),
      plot.subtitle = element_text(color = "grey35", size = rel(0.95), margin = margin(b = 10)),
      plot.caption = element_text(color = "grey50", size = rel(0.75), hjust = 0),
      axis.title = element_text(color = "grey25", size = rel(0.9)),
      axis.text = element_text(color = "grey30"),
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "grey90", linewidth = 0.3),
      legend.position = "bottom",
      legend.title = element_blank(),
      strip.text = element_text(face = "bold", size = rel(0.9)),
      plot.margin = margin(10, 14, 10, 10)
    )
}

# saves a chart at report grade resolution under the report dir
save_chart <- function(plot, name, width = 7, height = 4.2, dpi = 300) {
  path <- out_dir("figures", paste0(name, ".png"))
  ggsave(path, plot, width = width, height = height, dpi = dpi, bg = "white")
  invisible(path)
}

# formats values as egyptian pounds for chart axes
fmt_egp <- function(x) scales::label_currency(prefix = paste0(report_currency, " "), big.mark = ",")(x)

# formats fractions as percentages for chart axes
fmt_pct <- function(x) scales::label_percent(accuracy = 0.1)(x)
