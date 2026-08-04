# Requires make (on Windows: included with Git Bash, or `winget install GnuWin32.Make`).
# PowerShell equivalents are documented in the README.

.PHONY: install lint test ingest transform pipeline snapshot eval ml research dev docker-build docker-pipeline docker-test

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

ingest:
	uv run python -m crypto_market_elt.run

transform:
	uv run dbt build --project-dir dbt --profiles-dir dbt

pipeline: ingest transform

snapshot:
	uv run python -m crypto_market_elt.export_snapshot

eval:
	uv run python -m crypto_market_elt.evals

ml:
	uv run python -m crypto_market_elt.ml

research:
	uv run python -m crypto_market_elt.ml --timeseries
	uv run python -m crypto_market_elt.ml --event-study

dev:
	uv run dagster dev -f orchestration/definitions.py

docker-build:
	docker compose build

docker-pipeline:
	docker compose run --rm pipeline

docker-test:
	docker compose run --rm test
