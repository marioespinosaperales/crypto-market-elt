"""Shared HTTP client with retries and exponential backoff for all sources."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from crypto_market_elt.settings import HttpSourceConfig

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_json(
    config: HttpSourceConfig,
    path: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET with retries. Raises httpx.HTTPStatusError when attempts are exhausted."""
    url = f"{config.base_url.rstrip('/')}/{path.lstrip('/')}"
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        if attempt > 0:
            delay = config.backoff_seconds * (2 ** (attempt - 1))
            logger.warning("Retry %d/%d in %.1fs: %s", attempt, config.max_retries, delay, url)
            time.sleep(delay)
        try:
            response = httpx.get(
                url, params=params, headers=headers, timeout=config.timeout_seconds
            )
            if response.status_code in RETRYABLE_STATUS:
                last_error = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", request=response.request, response=response
                )
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Retries exhausted against {url}") from last_error
