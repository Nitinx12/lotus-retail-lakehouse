# brings the docker stack up with .env exported for compose interpolation
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath ".env")) {
  Write-Error "missing .env, copy it from .env.example first"
  exit 2
}
Get-Content -LiteralPath ".env" | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $name, $value = $_.Split('=', 2)
  [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
}
if ($args.Count -eq 0) {
  $cmd = @('up', '--build')
} else {
  $cmd = $args
}
& docker compose -f docker/docker-compose.yml @cmd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
