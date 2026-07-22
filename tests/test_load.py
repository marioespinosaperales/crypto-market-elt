import datetime as dt

import duckdb
import pandas as pd

from crypto_market_elt.load import load_raw_tables, write_partition


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame({"coin_id": ["bitcoin", "ethereum"], "price": [117234.0, 4456.78]})


def test_write_partition_creates_hive_layout(tmp_path):
    date = dt.date(2026, 7, 21)
    path = write_partition(_sample_frame(), tmp_path, "coingecko_markets", ingested_date=date)

    assert path == tmp_path / "coingecko_markets" / "ingested_date=2026-07-21" / "data.parquet"
    assert len(pd.read_parquet(path)) == 2


def test_write_partition_is_idempotent(tmp_path):
    date = dt.date(2026, 7, 21)
    write_partition(_sample_frame(), tmp_path, "coingecko_markets", ingested_date=date)
    write_partition(_sample_frame(), tmp_path, "coingecko_markets", ingested_date=date)

    files = list((tmp_path / "coingecko_markets").rglob("*.parquet"))
    assert len(files) == 1
    assert len(pd.read_parquet(files[0])) == 2


def test_load_raw_tables_reads_all_partitions(tmp_path):
    data_dir = tmp_path / "data"
    write_partition(_sample_frame(), data_dir, "coingecko_markets", dt.date(2026, 7, 20))
    write_partition(_sample_frame(), data_dir, "coingecko_markets", dt.date(2026, 7, 21))
    db_path = tmp_path / "warehouse" / "test.duckdb"

    counts = load_raw_tables(db_path, data_dir, datasets=("coingecko_markets",))

    assert counts == {"coingecko_markets": 4}
    with duckdb.connect(str(db_path)) as conn:
        dates = conn.execute(
            "SELECT DISTINCT ingested_date FROM raw.coingecko_markets ORDER BY 1"
        ).fetchall()
    assert len(dates) == 2


def test_load_raw_tables_skips_missing_dataset(tmp_path):
    counts = load_raw_tables(tmp_path / "test.duckdb", tmp_path, datasets=("binance_klines",))
    assert counts == {}
