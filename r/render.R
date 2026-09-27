# renders the lotus retail analysis to pdf
rmarkdown::render(
  "r/analysis.Rmd",
  output_file = "report.pdf",
  output_dir = Sys.getenv("REPORT_OUTPUT_DIR", "reports")
)
