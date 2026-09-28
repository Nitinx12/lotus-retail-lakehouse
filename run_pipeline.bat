@echo off
REM Run the Lotus pipeline on Windows through the shared entrypoint.
setlocal
if /I "%~1"=="report" (
  powershell -ExecutionPolicy Bypass -File scripts/run_report.ps1
) else if /I "%~1"=="sql" (
  uv run python main.py sql-ops sql-gold
) else if /I "%~1"=="dashboard" (
  uv run streamlit run dashboard/app.py
) else if /I "%~1"=="notebooks" (
  uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks\*.ipynb
) else if "%~1"=="" (
  uv run python main.py all
) else (
  uv run python main.py %*
)
exit /b %ERRORLEVEL%
