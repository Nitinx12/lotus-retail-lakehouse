DEFAULT_GOAL := help

.PHONY: install lint format test unit smoke dag integration pipeline publish quality docker-build docker-up help

# install project dependencies with uv
install:
	uv sync

# run ruff and sqlfluff checks
lint:
	uv run ruff check .
	uv run ruff format --check src scripts tests dags dashboard main.py
	uv run sqlfluff lint sql/

# apply ruff formatting
format:
	uv run ruff format src scripts tests dags dashboard main.py

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

# build pipeline dashboard and report images
docker-build:
	docker build -f docker/Dockerfile.pipeline -t lotus-pipeline:local .
	docker build -f docker/Dockerfile.dashboard -t lotus-dashboard:local .
	docker build -f docker/Dockerfile.report -t lotus-report:local .

# start the docker stack through the env exporting wrapper
docker-up:
	bash scripts/docker_up.sh up --build

# show available targets
help:
	uv run python main.py --list
