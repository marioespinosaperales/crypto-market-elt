"""OHLCV feature engineering for anomaly detection."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "return_1d",
    "log_volume",
    "hl_range_pct",
    "close_open_pct",
    "volume_z",
    "return_z",
]


def load_binance_klines(path: Path, *, symbol: str = "BTCUSDT") -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = [
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
    frame = pd.DataFrame(payload, columns=fields).drop(columns="_ignore")
    for col in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ):
        frame[col] = pd.to_numeric(frame[col])
    frame["trade_count"] = frame["trade_count"].astype("int64")
    frame["open_time"] = pd.to_datetime(frame["open_time_ms"], unit="ms", utc=True)
    frame["symbol"] = symbol
    frame["interval"] = "1d"
    return frame


def synthesize_ohlcv(
    base: pd.DataFrame,
    *,
    n_extra: int = 60,
    seed: int = 42,
    inject_spike: bool = True,
) -> pd.DataFrame:
    """Expand a tiny fixture into a longer synthetic series for IsolationForest."""
    rng = np.random.default_rng(seed)
    if base.empty:
        raise ValueError("base OHLCV frame is empty")
    last = base.iloc[-1]
    price = float(last["close"])
    t0 = int(last["open_time_ms"]) + 86_400_000
    records = []
    for i in range(n_extra):
        ret = float(rng.normal(0.0, 0.015))
        open_p = price
        close_p = max(price * (1.0 + ret), 1.0)
        high_p = max(open_p, close_p) * (1.0 + abs(float(rng.normal(0.0, 0.005))))
        low_p = min(open_p, close_p) * (1.0 - abs(float(rng.normal(0.0, 0.005))))
        vol = float(max(rng.lognormal(9.0, 0.25), 1.0))
        if inject_spike and i == n_extra - 1:
            close_p = open_p * 1.35
            high_p = close_p * 1.02
            vol *= 20.0
        records.append(
            {
                "open_time_ms": t0 + i * 86_400_000,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "close_time_ms": t0 + i * 86_400_000 + 86_399_999,
                "quote_volume": vol * close_p,
                "trade_count": int(rng.integers(1000, 50_000)),
                "taker_buy_base_volume": vol * 0.5,
                "taker_buy_quote_volume": vol * close_p * 0.5,
                "open_time": pd.to_datetime(t0 + i * 86_400_000, unit="ms", utc=True),
                "symbol": str(last["symbol"]),
                "interval": "1d",
            }
        )
        price = close_p
    synth = pd.DataFrame.from_records(records)
    return pd.concat([base, synth], ignore_index=True)


def build_feature_matrix(ohlcv: pd.DataFrame) -> pd.DataFrame:
    frame = ohlcv.sort_values("open_time_ms").reset_index(drop=True).copy()
    close = frame["close"].astype(float)
    open_ = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float).clip(lower=1e-12)

    frame["return_1d"] = close.pct_change().fillna(0.0)
    frame["log_volume"] = volume.map(lambda v: math.log(v))
    frame["hl_range_pct"] = ((high - low) / close.replace(0, np.nan)).fillna(0.0)
    frame["close_open_pct"] = ((close - open_) / open_.replace(0, np.nan)).fillna(0.0)

    roll = 7
    ret_mean = frame["return_1d"].rolling(roll, min_periods=1).mean()
    ret_std = frame["return_1d"].rolling(roll, min_periods=1).std().replace(0, np.nan)
    vol_mean = frame["log_volume"].rolling(roll, min_periods=1).mean()
    vol_std = frame["log_volume"].rolling(roll, min_periods=1).std().replace(0, np.nan)
    frame["return_z"] = ((frame["return_1d"] - ret_mean) / ret_std).fillna(0.0)
    frame["volume_z"] = ((frame["log_volume"] - vol_mean) / vol_std).fillna(0.0)
    return frame
