"""Escritura del raw layer: Parquet particionado por fecha de ingesta.

Reescribir la partición del día es idempotente: correr el pipeline dos veces
el mismo día no duplica datos.
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
    """Escribe ``data_dir/<dataset>/ingested_date=YYYY-MM-DD/<filename>``.

    Datasets con varias unidades por corrida (p. ej. un símbolo de Binance por
    request) escriben un archivo por unidad dentro de la misma partición.
    """
    ingested_date = ingested_date or dt.datetime.now(dt.UTC).date()
    partition_dir = data_dir / dataset / f"ingested_date={ingested_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    path = partition_dir / filename
    frame.to_parquet(path, index=False)
    logger.info("Escritas %d filas en %s", len(frame), path)
    return path
