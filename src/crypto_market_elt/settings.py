"""Carga y validación de la configuración del proyecto.

Toda la configuración declarativa vive en ``config/*.yaml`` y se valida aquí
con pydantic al arranque. Los secretos (API keys) SOLO entran por variables
de entorno (prefijo ``ELT_``), nunca por YAML.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class HttpSourceConfig(BaseModel):
    """Parámetros comunes a cualquier fuente HTTP."""

    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    backoff_seconds: float = 2.0


class CoinGeckoConfig(HttpSourceConfig):
    vs_currency: str = "usd"
    top_n: int = Field(default=100, ge=1, le=250)


class BinanceConfig(HttpSourceConfig):
    interval: str = "1d"
    lookback_days: int = Field(default=365, ge=1, le=1000)
    symbols: list[str] = Field(min_length=1)


class SourcesConfig(BaseModel):
    coingecko: CoinGeckoConfig
    binance: BinanceConfig


class PipelineConfig(BaseModel):
    data_dir: Path = Path("./data")
    duckdb_path: Path = Path("./warehouse/crypto.duckdb")
    raw_schema: str = "raw"

    def resolve(self, root: Path) -> PipelineConfig:
        """Convierte rutas relativas en absolutas respecto a la raíz del repo."""
        return self.model_copy(
            update={
                "data_dir": (root / self.data_dir).resolve(),
                "duckdb_path": (root / self.duckdb_path).resolve(),
            }
        )


class Secrets(BaseSettings):
    """Secretos y overrides por entorno. Ejemplo: ELT_COINGECKO_API_KEY=..."""

    model_config = SettingsConfigDict(env_prefix="ELT_", env_file=".env", extra="ignore")

    coingecko_api_key: str | None = None


class Settings(BaseModel):
    sources: SourcesConfig
    pipeline: PipelineConfig
    secrets: Secrets


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings(config_dir: Path | None = None) -> Settings:
    config_dir = config_dir or CONFIG_DIR
    sources = SourcesConfig.model_validate(_load_yaml(config_dir / "sources.yaml"))
    pipeline = PipelineConfig.model_validate(_load_yaml(config_dir / "pipelines.yaml"))
    return Settings(
        sources=sources,
        pipeline=pipeline.resolve(PROJECT_ROOT),
        secrets=Secrets(),
    )
