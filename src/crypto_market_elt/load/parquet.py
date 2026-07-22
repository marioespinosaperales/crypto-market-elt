"""Raw layer writer: Parquet partitioned by ingestion date.

Rewriting the day's partition is idempotent: running the pipeline twice on the
same day does not duplicate data.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def write_partition(
    frame: pd.DataFrame,
    data_dir: Path,
    dataset: str,
    ingested_date: dt.date | None = None,
    filename: str = "data.parquet",
) -> Path:
    """Write ``data_dir/<dataset>/ingested_date=YYYY-MM-DD/<filename>``.

    Datasets with multiple units per run (e.g. one Binance symbol per request)
    write one file per unit inside the same partition.
    """
    ingested_date = ingested_date or dt.datetime.now(dt.UTC).date()
    partition_dir = data_dir / dataset / f"ingested_date={ingested_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    path = partition_dir / filename
    frame.to_parquet(path, index=False)
    logger.info("Wrote %d rows to %s", len(frame), path)
    return path
