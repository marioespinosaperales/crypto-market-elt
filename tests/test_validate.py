import pandas as pd
import pandera
import pytest
import respx
from httpx import Response

from crypto_market_elt.extract import fetch_coingecko_markets
from crypto_market_elt.validate import validate_coingecko_markets


@respx.mock
def test_rejects_non_positive_price(coingecko_config, coingecko_payload):
    coingecko_payload[0]["current_price"] = -1.0
    respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
        return_value=Response(200, json=coingecko_payload)
    )
    frame = fetch_coingecko_markets(coingecko_config)

    with pytest.raises(pandera.errors.SchemaError):
        validate_coingecko_markets(frame)


@respx.mock
def test_rejects_duplicated_coin_id(coingecko_config, coingecko_payload):
    coingecko_payload[1]["id"] = "bitcoin"
    respx.get("https://api.coingecko.com/api/v3/coins/markets").mock(
        return_value=Response(200, json=coingecko_payload)
    )
    frame = fetch_coingecko_markets(coingecko_config)

    with pytest.raises(pandera.errors.SchemaError):
        validate_coingecko_markets(frame)


def test_rejects_unexpected_columns(coingecko_config):
    frame = pd.DataFrame({"columna_sorpresa": [1]})
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        validate_coingecko_markets(frame)
