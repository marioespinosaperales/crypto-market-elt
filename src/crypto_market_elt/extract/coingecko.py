"""Extracción del snapshot diario de mercado desde CoinGecko (/coins/markets)."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from crypto_market_elt.extract.http import get_json
from crypto_market_elt.settings import CoinGeckoConfig

# Columnas del contrato raw (ver schemas/raw_coingecko_markets.json)
_COLUMNS = [
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "market_cap_rank",
    "total_volume",
    "price_change_percentage_24h",
    "circulating_supply",
    "last_updated",
]


def fetch_coingecko_markets(
    config: CoinGeckoConfig,
    api_key: str | None = None,
    snapshot_date: dt.date | None = None,
) -> pd.DataFrame:
    """Snapshot del top-N por market cap. Una fila por moneda."""
    headers = {"x-cg-demo-api-key": api_key} if api_key else None
    payload = get_json(
        config,
        "/coins/markets",
        params={
            "vs_currency": config.vs_currency,
            "order": "market_cap_desc",
            "per_page": config.top_n,
            "page": 1,
            "sparkline": "false",
        },
        headers=headers,
    )
    frame = pd.DataFrame(payload)[_COLUMNS].rename(columns={"id": "coin_id"})
    frame["vs_currency"] = config.vs_currency
    frame["snapshot_date"] = pd.Timestamp(
        snapshot_date or dt.datetime.now(dt.UTC).date()
    )
    return frame
