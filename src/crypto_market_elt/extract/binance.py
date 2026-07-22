"""Extracción de velas OHLCV diarias desde la API pública de Binance (/api/v3/klines)."""

from __future__ import annotations

import pandas as pd

from crypto_market_elt.extract.http import get_json
from crypto_market_elt.settings import BinanceConfig

# La API devuelve arrays posicionales; este es el contrato posicional documentado.
_KLINE_FIELDS = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time_ms",
    "quote_volume",
    "trade_count",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "_ignore",
]

_NUMERIC_FIELDS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def fetch_binance_klines(config: BinanceConfig, symbol: str) -> pd.DataFrame:
    """Velas OHLCV de un símbolo. Una fila por vela cerrada."""
    payload = get_json(
        config,
        "/api/v3/klines",
        params={
            "symbol": symbol,
            "interval": config.interval,
            "limit": min(config.lookback_days, 1000),
        },
    )
    frame = pd.DataFrame(payload, columns=_KLINE_FIELDS).drop(columns="_ignore")
    for field in _NUMERIC_FIELDS:
        frame[field] = pd.to_numeric(frame[field])
    frame["trade_count"] = frame["trade_count"].astype("int64")
    frame["open_time"] = pd.to_datetime(frame["open_time_ms"], unit="ms", utc=True)
    frame["symbol"] = symbol
    frame["interval"] = config.interval
    # La última vela puede estar aún abierta: se descarta para no cargar datos parciales.
    now_ms = pd.Timestamp.now(tz="UTC").value // 1_000_000
    return frame[frame["close_time_ms"] <= now_ms].reset_index(drop=True)
