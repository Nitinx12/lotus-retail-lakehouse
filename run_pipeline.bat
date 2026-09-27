@echo off
REM Run the Lotus pipeline on Windows through the shared entrypoint.
setlocal
if "%~1"=="" (
  uv run python main.py all
) else (
  uv run python main.py %*
)
exit /b %ERRORLEVEL%
