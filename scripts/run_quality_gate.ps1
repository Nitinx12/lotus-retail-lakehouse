# runs bronze silver and gold quality suites into ops
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
$env:PYTHONPATH = "."
uv run python scripts/run_quality.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($suite in @("bronze", "silver", "gold")) {
  uv run python scripts/run_gx.py --suite $suite
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
