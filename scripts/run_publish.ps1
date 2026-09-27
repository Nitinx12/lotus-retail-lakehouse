# publishes gold parquet into the postgres serving schema
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
$env:PYTHONPATH = "."
uv run python scripts/run_publish.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
