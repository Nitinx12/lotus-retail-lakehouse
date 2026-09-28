#!/usr/bin/env bash
set -euo pipefail
# renders the r analysis and the latex report
cd "$(dirname "$0")/../r"
: "${LOTUS_ENV:=dev}"
export REPORT_OUTPUT_DIR="${REPORT_OUTPUT_DIR:-../output/${LOTUS_ENV}/report}"
echo "[run_report] environment=${LOTUS_ENV}"
echo "[A10] Rendering deep dive R analysis (HTML)..."
quarto render analysis.qmd --output-dir "../output/${LOTUS_ENV}/analysis"
echo "[A11] Rendering stakeholder report (Quarto -> LaTeX -> PDF via latexmk)..."
quarto render report.qmd --output-dir "../output/${LOTUS_ENV}/report"
echo "[run_report] Done."
