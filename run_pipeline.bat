@echo off
REM Run the Lotus pipeline on Windows through the shared entrypoint.
setlocal
if /I "%~1"=="setup" (
  bash scripts/data_pipeline_setup.sh %2 %3 %4
) else if /I "%~1"=="health" (
  bash scripts/health_check.sh %2 %3 %4
) else if /I "%~1"=="security" (
  bash scripts/security.sh %2 %3 %4
) else if /I "%~1"=="inspect" (
  set PYTHONPATH=%CD%
  uv run python scripts/inspect_gold_schema.py
) else if /I "%~1"=="dbt" (
  bash scripts/run_dbt.sh
) else if /I "%~1"=="backup" (
  bash scripts/backup_postgres.sh
) else if /I "%~1"=="restore" (
  bash scripts/restore_postgres.sh %2 %3
) else if /I "%~1"=="gate" (
  bash scripts/run_tests.sh
) else if /I "%~1"=="report" (
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
