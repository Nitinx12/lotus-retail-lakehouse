# lands mongo collections into bronze parquet
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath ".env") {
  Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
  }
}
$env:PYTHONPATH = "."
uv run python scripts/run_plpgsql.py --suite source
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python scripts/run_bronze.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
