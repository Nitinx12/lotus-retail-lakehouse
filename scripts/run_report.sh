# renders the r analysis and builds the latex report
set -euo pipefail
if [ -f .env ]; then set -a; source .env; set +a; fi
mkdir -p logs "${REPORT_OUTPUT_DIR:-reports}"
if [ ! -f r/analysis.Rmd ]; then
  echo "report sources not present, skipping" | tee logs/report.log
  exit 0
fi
if ! command -v Rscript >/dev/null 2>&1; then
  echo "Rscript not found, skipping report" | tee logs/report.log
  exit 0
fi
Rscript -e "rmarkdown::render('r/analysis.Rmd', output_dir='${REPORT_OUTPUT_DIR:-reports}')" 2>&1 | tee logs/report.log
if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -outdir="${REPORT_OUTPUT_DIR:-reports}" "${REPORT_OUTPUT_DIR:-reports}"/report.tex 2>&1 | tee -a logs/report.log
fi
