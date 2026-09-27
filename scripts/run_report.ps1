# renders the r analysis and builds the latex report
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
if (-not $env:REPORT_OUTPUT_DIR) { $env:REPORT_OUTPUT_DIR = "reports" }
if (-not [IO.Path]::IsPathRooted($env:REPORT_OUTPUT_DIR)) {
  $env:REPORT_OUTPUT_DIR = Join-Path (Get-Location) $env:REPORT_OUTPUT_DIR
}
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
$render = Start-Process -FilePath "Rscript" -ArgumentList "r/render.R" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "logs/report.log" -RedirectStandardError "logs/report.err"
if ($render.ExitCode -ne 0) { exit $render.ExitCode }
if (Get-Command latexmk -ErrorAction SilentlyContinue) {
  $build = Start-Process -FilePath "latexmk" -ArgumentList "-pdf", "-outdir=$env:REPORT_OUTPUT_DIR", "$env:REPORT_OUTPUT_DIR/report.tex" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "logs/latex.log" -RedirectStandardError "logs/latex.err"
  if ($build.ExitCode -ne 0) { exit $build.ExitCode }
}
