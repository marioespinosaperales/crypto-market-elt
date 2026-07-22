"""Export a marts snapshot for the Evidence dashboard.

Copies mart tables from the warehouse into a small DuckDB file under
``dashboard/sources/crypto/`` — Evidence needs it at build time (Vercel).

If a previous snapshot already exists (in CI it comes from the ``data`` branch),
it is merged: fresh warehouse rows win, and historical rows the warehouse no
longer holds (prior CoinGecko days, candles outside the lookback window) are
kept. That way history accumulates across ephemeral runners.

    uv run python -m crypto_market_elt.export_snapshot
"""

from __future__ import annotations

import logging

import duckdb

from crypto_market_elt.settings import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = PROJECT_ROOT / "dashboard" / "sources" / "crypto" / "crypto_marts.duckdb"
MARTS_SCHEMA = "main_marts"
# Mart table -> natural key used to avoid duplicates when merging.
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
    logger.info("Snapshot exported to %s: %s", SNAPSHOT_PATH, export_snapshot())


if __name__ == "__main__":
    main()
