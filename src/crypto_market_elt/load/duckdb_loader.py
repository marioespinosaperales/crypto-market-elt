"""Carga del raw layer (Parquet) a DuckDB, donde dbt hace la T del ELT."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DATASETS = ("coingecko_markets", "binance_klines")


def load_raw_tables(
    duckdb_path: Path,
    data_dir: Path,
    raw_schema: str = "raw",
    datasets: tuple[str, ...] = DATASETS,
) -> dict[str, int]:
    """(Re)crea una tabla raw por dataset leyendo TODAS sus particiones Parquet.

    ``ingested_date`` se deriva del path (partición Hive), de modo que dbt puede
    quedarse con el snapshot más reciente por clave natural.
    """
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
        for dataset in datasets:
            glob = (data_dir / dataset / "*" / "*.parquet").as_posix()
            if not list(data_dir.glob(f"{dataset}/*/*.parquet")):
                logger.warning("Sin particiones para %s, se omite", dataset)
                continue
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.{dataset} AS
                SELECT * FROM read_parquet('{glob}', hive_partitioning = true)
                """
            )
            count = conn.execute(f"SELECT count(*) FROM {raw_schema}.{dataset}").fetchone()[0]
            row_counts[dataset] = count
            logger.info("%s.%s: %d filas", raw_schema, dataset, count)

    return row_counts
