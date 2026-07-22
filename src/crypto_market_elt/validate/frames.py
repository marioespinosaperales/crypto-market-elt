"""Ingestion-time validation: data is validated BEFORE landing in the raw layer.

Catching bad data here is cheaper than discovering it in the warehouse.
Human-readable contracts live in ``schemas/``; these schemas are their
executable implementation.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

coingecko_markets_schema = pa.DataFrameSchema(
    {
        "coin_id": pa.Column(str, unique=True, nullable=False),
        "symbol": pa.Column(str, nullable=False),
        "name": pa.Column(str, nullable=False),
        "current_price": pa.Column(float, pa.Check.gt(0), nullable=False, coerce=True),
        "market_cap": pa.Column(float, pa.Check.ge(0), nullable=True, coerce=True),
        "market_cap_rank": pa.Column(float, pa.Check.ge(1), nullable=True, coerce=True),
        "total_volume": pa.Column(float, pa.Check.ge(0), nullable=True, coerce=True),
        "price_change_percentage_24h": pa.Column(float, nullable=True, coerce=True),
        "circulating_supply": pa.Column(float, pa.Check.ge(0), nullable=True, coerce=True),
        "last_updated": pa.Column(str, nullable=False),
        "vs_currency": pa.Column(str, nullable=False),
        "snapshot_date": pa.Column("datetime64[ns]", nullable=False, coerce=True),
    },
    strict=True,
)

binance_klines_schema = pa.DataFrameSchema(
    {
        "open_time_ms": pa.Column("int64", pa.Check.gt(0), nullable=False),
        "open": pa.Column(float, pa.Check.gt(0), nullable=False),
        "high": pa.Column(float, pa.Check.gt(0), nullable=False),
        "low": pa.Column(float, pa.Check.gt(0), nullable=False),
        "close": pa.Column(float, pa.Check.gt(0), nullable=False),
        "volume": pa.Column(float, pa.Check.ge(0), nullable=False),
        "close_time_ms": pa.Column("int64", pa.Check.gt(0), nullable=False),
        "quote_volume": pa.Column(float, pa.Check.ge(0), nullable=False),
        "trade_count": pa.Column("int64", pa.Check.ge(0), nullable=False),
        "taker_buy_base_volume": pa.Column(float, pa.Check.ge(0), nullable=False),
        "taker_buy_quote_volume": pa.Column(float, pa.Check.ge(0), nullable=False),
        "open_time": pa.Column(nullable=False),
        "symbol": pa.Column(str, nullable=False),
        "interval": pa.Column(str, nullable=False),
    },
    strict=True,
    checks=[
        pa.Check(lambda df: (df["high"] >= df["low"]).all(), error="high < low"),
        pa.Check(
            lambda df: ~df.duplicated(subset=["symbol", "open_time_ms"]).any(),
            error="duplicate candles for (symbol, open_time)",
        ),
    ],
)


def validate_coingecko_markets(frame: pd.DataFrame) -> pd.DataFrame:
    return coingecko_markets_schema.validate(frame)


def validate_binance_klines(frame: pd.DataFrame) -> pd.DataFrame:
    return binance_klines_schema.validate(frame)
