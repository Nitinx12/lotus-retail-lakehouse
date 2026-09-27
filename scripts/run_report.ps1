# renders the r analysis and builds the latex report
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
if (-not $env:REPORT_OUTPUT_DIR) { $env:REPORT_OUTPUT_DIR = "reports" }
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
New-Item -ItemType Directory -Path $env:REPORT_OUTPUT_DIR -Force | Out-Null
if (-not (Test-Path -LiteralPath "r/analysis.Rmd")) {
  "report sources not present, skipping" | Out-File -FilePath "logs/report.log"
  exit 0
}
if (-not (Get-Command Rscript -ErrorAction SilentlyContinue)) {
  "Rscript not found, skipping report" | Out-File -FilePath "logs/report.log"
  exit 0
}
& Rscript -e "rmarkdown::render('r/analysis.Rmd', output_dir='$env:REPORT_OUTPUT_DIR')" > logs/report.log 2>&1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (Get-Command latexmk -ErrorAction SilentlyContinue) {
  & latexmk -pdf -outdir="$env:REPORT_OUTPUT_DIR" "$env:REPORT_OUTPUT_DIR/report.tex" >> logs/report.log 2>&1
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
