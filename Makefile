# Requires make (on Windows: included with Git Bash, or `winget install GnuWin32.Make`).
# PowerShell equivalents are documented in the README.

.PHONY: install lint test ingest transform pipeline snapshot dev

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

dev:
	uv run dagster dev -f orchestration/definitions.py
