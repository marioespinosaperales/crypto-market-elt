# crypto-market-elt — Project conventions

ELT pipeline: CoinGecko + Binance REST → Parquet (raw) → DuckDB → dbt → marts.
Portfolio story: **ingestion contracts + fail-fast QC** (sibling: dex labeling, lp ground-truth).

## Architecture

- `src/crypto_market_elt/extract/` — HTTP clients for each source. One module per source.
- `src/crypto_market_elt/validate/` — pandera schemas. EVERY row is validated BEFORE writing to the raw layer.
- `src/crypto_market_elt/evals/` — QC scorecard (contract probes + warehouse sanity).
- `src/crypto_market_elt/ml/` — IsolationForest anomaly + ARIMA timeseries research reports.
- `RESEARCH.md` — naive vs ARIMA atomic study.
- `src/crypto_market_elt/load/` — Parquet writer (Hive partitions by `ingested_date`) and DuckDB loader.
- `dbt/` — ALL transformation lives here (ELT pattern). Never transform in Python what dbt can do.
- `orchestration/definitions.py` — Dagster assets. Load assets use keys `raw/<table>` to wire into dbt sources.
- `config/` — declarative parameters (endpoints, symbols, limits). Secrets ONLY via env vars with the `ELT_` prefix.
- `schemas/` — human-readable data contracts; their executable implementation is the pandera schemas.
- `Dockerfile` / `docker-compose.yml` — reproducible Linux pipeline + scorecard.

## Rules

- Python 3.12, type hints on every public signature, no classes where a function will do.
- New config: add it to YAML under `config/` + a pydantic model in `settings.py`. Never hardcode params.
- dbt: naming `stg_` (staging, views) / `mart_` (marts, tables). Every new model gets tests in its `schema.yml`.
- Data, artifacts, and logs are NEVER committed (`data/`, `warehouse/`, `artifacts/`, `logs/` are gitignored).
- Tests use fixtures of real API responses (in `tests/fixtures/`), with HTTP mocked via respx.
- Do NOT use `from __future__ import annotations` in files with Dagster assets (breaks runtime annotation validation).

## Commands

- `make pipeline` (or `uv run python -m crypto_market_elt.run` + `uv run dbt build --project-dir dbt --profiles-dir dbt`)
- `make eval` — QC scorecard → `artifacts/qc_scorecard.md`
- `make ml` — anomaly report → `artifacts/ml_anomaly_report.md`
- `make research` — timeseries + event-study → `artifacts/research_*.md`
- `make docker-pipeline` / `make docker-test`
- `make dev` — Dagster UI
- `make lint && make test` — required before every commit
