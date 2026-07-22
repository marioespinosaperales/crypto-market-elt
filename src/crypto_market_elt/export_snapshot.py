"""Exporta un snapshot de los marts al dashboard de Evidence.

Copia las tablas mart del warehouse a un DuckDB pequeño en
``dashboard/sources/crypto/`` — Evidence lo necesita en build time (Vercel).

Si ya existe un snapshot previo (en CI viene de la rama ``data``), se fusiona:
los datos frescos del warehouse ganan y las filas históricas que el warehouse
ya no tiene (días previos de CoinGecko, velas fuera de la ventana de lookback)
se conservan. Así la historia acumula entre corridas de runners efímeros.

    uv run python -m crypto_market_elt.export_snapshot
"""

from __future__ import annotations

import logging

import duckdb

from crypto_market_elt.settings import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = PROJECT_ROOT / "dashboard" / "sources" / "crypto" / "crypto_marts.duckdb"
MARTS_SCHEMA = "main_marts"
# Tabla mart -> clave natural usada para no duplicar filas al fusionar.
MART_KEYS = {
    "mart_daily_ohlcv": ("symbol", "trade_date"),
    "mart_market_overview": ("snapshot_date",),
}


def export_snapshot() -> dict[str, int]:
    settings = get_settings()
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SNAPSHOT_PATH.with_suffix(".duckdb.tmp")
    tmp_path.unlink(missing_ok=True)

    warehouse_path = str(settings.pipeline.duckdb_path).replace("'", "''")
    merge_previous = SNAPSHOT_PATH.exists()

    counts: dict[str, int] = {}
    with duckdb.connect(str(tmp_path)) as conn:
        conn.execute(f"ATTACH '{warehouse_path}' AS warehouse (READ_ONLY)")
        if merge_previous:
            old_path = str(SNAPSHOT_PATH).replace("'", "''")
            conn.execute(f"ATTACH '{old_path}' AS previous (READ_ONLY)")
        for table, keys in MART_KEYS.items():
            conn.execute(
                f"CREATE TABLE {table} AS SELECT * FROM warehouse.{MARTS_SCHEMA}.{table}"
            )
            if merge_previous:
                using = ", ".join(keys)
                conn.execute(
                    f"INSERT INTO {table} "
                    f"SELECT old.* FROM previous.{table} AS old "
                    f"ANTI JOIN {table} AS fresh USING ({using})"
                )
            counts[table] = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    SNAPSHOT_PATH.unlink(missing_ok=True)
    tmp_path.rename(SNAPSHOT_PATH)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Snapshot exportado a %s: %s", SNAPSHOT_PATH, export_snapshot())


if __name__ == "__main__":
    main()
