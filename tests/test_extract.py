import time

import pandas as pd
import respx
from httpx import Response

from crypto_market_elt.extract import fetch_binance_klines, fetch_coingecko_markets
from crypto_market_elt.validate import validate_binance_klines, validate_coingecko_markets


@respx.mock
def test_fetch_coingecko_markets(coingecko_config, coingecko_payload):
    respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
        return_value=Response(200, json=coingecko_payload)
    )
    frame = fetch_coingecko_markets(coingecko_config)

    assert len(frame) == 2
    assert set(frame["coin_id"]) == {"bitcoin", "ethereum"}
    # The raw contract holds as soon as data leaves the extractor
    validate_coingecko_markets(frame)


@respx.mock
def test_fetch_binance_klines(binance_config, binance_payload):
    respx.get("https://api.binance.com/api/v3/klines").mock(
        return_value=Response(200, json=binance_payload)
    )
    frame = fetch_binance_klines(binance_config, "BTCUSDT")

    assert len(frame) == 3
    assert frame["close"].dtype == "float64"
    assert (frame["symbol"] == "BTCUSDT").all()
    validate_binance_klines(frame)


@respx.mock
def test_fetch_binance_klines_drops_open_candle(binance_config, binance_payload):
    # Latest candle closes in the future -> still open -> must be dropped
    future_ms = int(time.time() * 1000) + 86_400_000
    open_candle = list(binance_payload[-1])
    open_candle[0] = future_ms - 86_399_999
    open_candle[6] = future_ms
    respx.get("https://api.binance.com/api/v3/klines").mock(
        return_value=Response(200, json=binance_payload + [open_candle])
    )
    frame = fetch_binance_klines(binance_config, "BTCUSDT")

    assert len(frame) == 3
    assert (pd.to_datetime(frame["close_time_ms"], unit="ms", utc=True)
            <= pd.Timestamp.now(tz="UTC")).all()
