"""Load the raw layer (Parquet) into DuckDB, where dbt runs the T in ELT."""

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
    """(Re)create one raw table per dataset by reading ALL of its Parquet partitions.

    ``ingested_date`` is derived from the path (Hive partition), so dbt can keep
    the latest snapshot per natural key.
    """
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
        for dataset in datasets:
            glob = (data_dir / dataset / "*" / "*.parquet").as_posix()
            if not list(data_dir.glob(f"{dataset}/*/*.parquet")):
                logger.warning("No partitions for %s, skipping", dataset)
                continue
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {raw_schema}.{dataset} AS
                SELECT * FROM read_parquet('{glob}', hive_partitioning = true)
                """
            )
            count = conn.execute(f"SELECT count(*) FROM {raw_schema}.{dataset}").fetchone()[0]
            row_counts[dataset] = count
            logger.info("%s.%s: %d rows", raw_schema, dataset, count)

    return row_counts
