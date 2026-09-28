# renders the r analysis and the latex report
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
if (-not $env:LOTUS_ENV) { $env:LOTUS_ENV = "dev" }
if (-not $env:REPORT_OUTPUT_DIR) { $env:REPORT_OUTPUT_DIR = "output/$($env:LOTUS_ENV)/report" }
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
if (-not (Get-Command quarto -ErrorAction SilentlyContinue)) {
  "quarto not found, skipping report" | Out-File -FilePath "logs/report.log"
  exit 0
}
$analysis = Start-Process -FilePath "quarto" -ArgumentList "render", "r/analysis.qmd", "--output-dir", "output/$($env:LOTUS_ENV)/analysis" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "logs/report.log" -RedirectStandardError "logs/report.err"
if ($analysis.ExitCode -ne 0) { exit $analysis.ExitCode }
$report = Start-Process -FilePath "quarto" -ArgumentList "render", "r/report.qmd", "--output-dir", "output/$($env:LOTUS_ENV)/report" -Wait -PassThru -NoNewWindow -RedirectStandardOutput "logs/latex.log" -RedirectStandardError "logs/latex.err"
if ($report.ExitCode -ne 0) { exit $report.ExitCode }
