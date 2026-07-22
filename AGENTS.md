# crypto-market-elt — Convenciones del proyecto

ELT pipeline: CoinGecko + Binance REST → Parquet (raw) → DuckDB → dbt → marts.

## Arquitectura

- `src/crypto_market_elt/extract/` — clientes HTTP de las fuentes. Un módulo por fuente.
- `src/crypto_market_elt/validate/` — schemas pandera. TODO dato se valida ANTES de escribirse al raw layer.
- `src/crypto_market_elt/load/` — escritura Parquet (particiones Hive por `ingested_date`) y carga a DuckDB.
- `dbt/` — TODA la transformación vive aquí (patrón ELT). Nunca transformar en Python lo que dbt puede hacer.
- `orchestration/definitions.py` — assets de Dagster. Los assets de carga usan keys `raw/<tabla>` para conectar con las sources de dbt.
- `config/` — parámetros declarativos (endpoints, símbolos, límites). Secretos SOLO por env vars con prefijo `ELT_`.
- `schemas/` — contratos de datos legibles por humanos; su implementación ejecutable son los schemas pandera.

## Reglas

- Python 3.12, type hints en todas las firmas públicas, sin clases donde una función basta.
- Configuración nueva: agregar al YAML en `config/` + modelo pydantic en `settings.py`. Nunca hardcodear params.
- dbt: naming `stg_` (staging, views) / `mart_` (marts, tables). Todo modelo nuevo lleva tests en su `schema.yml`.
- Los datos y logs NUNCA se commitean (`data/`, `warehouse/`, `logs/` están en .gitignore).
- Tests con fixtures de respuestas reales de las APIs (en `tests/fixtures/`), mocking HTTP con respx.
- NO usar `from __future__ import annotations` en archivos con assets de Dagster (rompe la validación de anotaciones de contexto).

## Comandos

- `make pipeline` (o `uv run python -m crypto_market_elt.run` + `uv run dbt build --project-dir dbt --profiles-dir dbt`)
- `make dev` — UI de Dagster
- `make lint && make test` — obligatorio antes de commit
