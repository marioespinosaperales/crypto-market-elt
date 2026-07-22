import json
from pathlib import Path

import pytest

from crypto_market_elt.settings import BinanceConfig, CoinGeckoConfig

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def coingecko_payload() -> list[dict]:
    return json.loads((FIXTURES / "coingecko_markets.json").read_text(encoding="utf-8"))


@pytest.fixture
def binance_payload() -> list[list]:
    return json.loads((FIXTURES / "binance_klines.json").read_text(encoding="utf-8"))


@pytest.fixture
def coingecko_config() -> CoinGeckoConfig:
    return CoinGeckoConfig(base_url="https://api.coingecko.com/api/v3", top_n=2, max_retries=0)


@pytest.fixture
def binance_config() -> BinanceConfig:
    return BinanceConfig(
        base_url="https://api.binance.com",
        symbols=["BTCUSDT"],
        lookback_days=3,
        max_retries=0,
    )
