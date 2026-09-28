DEFAULT_GOAL := help

.PHONY: install lint format test unit smoke dag integration pipeline publish quality sql report dashboard notebooks docker-build docker-up clean help

# install project dependencies with uv
install:
	uv sync

# run ruff and sqlfluff checks same scope as the git hooks
lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run sqlfluff lint sql/

# apply ruff formatting
format:
	uv run ruff format .

# run unit smoke and dag suites
test: unit smoke dag

# run unit suite
unit:
	uv run pytest tests/unit -q

# run smoke suite
smoke:
	uv run pytest tests/smoke -q

# run dag integrity suite
dag:
	uv run pytest tests/dag -q

# run integration suite needs postgres
integration:
	uv run pytest tests/integration -q

# run full local pipeline through main entrypoint
pipeline:
	uv run python main.py all

# publish gold parquet to postgres
publish:
	uv run python main.py publish

# run python quality gates
quality:
	uv run python main.py quality

# apply versioned sql objects to ops then gold
sql:
	uv run python main.py sql-ops sql-gold

# render the r analysis and stakeholder report
report:
	bash scripts/run_report.sh

# launch the streamlit dashboard locally
dashboard:
	uv run streamlit run dashboard/app.py

# execute all notebooks in place
notebooks:
	uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/*.ipynb

# build pipeline dashboard and report images
docker-build:
	docker build -f docker/Dockerfile.pipeline -t lotus-pipeline:local .
	docker build -f docker/Dockerfile.dashboard -t lotus-dashboard:local .
	docker build -f docker/Dockerfile.report -t lotus-report:local .

# start the docker stack through the env exporting wrapper
docker-up:
	bash scripts/docker_up.sh up --build

# remove generated reports and notebook checkpoints never source data
clean:
	rm -rf output reports notebooks/.ipynb_checkpoints .quarto r/.quarto

# show available targets
help:
	uv run python main.py --list
