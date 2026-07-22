"""Entrypoint de ingesta: extract -> validate -> load (raw layer + DuckDB).

La T del ELT vive en dbt (``make transform``). Dagster orquesta ambos pasos
en producción; este módulo permite correr la ingesta a mano:

    uv run python -m crypto_market_elt.run
"""

from __future__ import annotations

import logging

from crypto_market_elt.extract import fetch_binance_klines, fetch_coingecko_markets
from crypto_market_elt.load import load_raw_tables, write_partition
from crypto_market_elt.settings import get_settings
from crypto_market_elt.validate import validate_binance_klines, validate_coingecko_markets

logger = logging.getLogger(__name__)


def ingest_coingecko() -> int:
    settings = get_settings()
    frame = fetch_coingecko_markets(
        settings.sources.coingecko, api_key=settings.secrets.coingecko_api_key
    )
    frame = validate_coingecko_markets(frame)
    write_partition(frame, settings.pipeline.data_dir, "coingecko_markets")
    return len(frame)


def ingest_binance() -> int:
    settings = get_settings()
    config = settings.sources.binance
    total = 0
    for symbol in config.symbols:
        frame = fetch_binance_klines(config, symbol)
        frame = validate_binance_klines(frame)
        write_partition(
            frame,
            settings.pipeline.data_dir,
            "binance_klines",
            filename=f"{symbol}.parquet",
        )
        total += len(frame)
    return total


def load_warehouse() -> dict[str, int]:
    settings = get_settings()
    return load_raw_tables(
        duckdb_path=settings.pipeline.duckdb_path,
        data_dir=settings.pipeline.data_dir,
        raw_schema=settings.pipeline.raw_schema,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("CoinGecko: %d filas", ingest_coingecko())
    logger.info("Binance: %d filas", ingest_binance())
    logger.info("Warehouse: %s", load_warehouse())


if __name__ == "__main__":
    main()
