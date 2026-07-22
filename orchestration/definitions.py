"""Dagster definitions: ingestion assets + dbt assets + daily schedule.

Start the local UI with:

    uv run dagster dev -f orchestration/definitions.py
"""

import os

import dagster as dg
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from crypto_market_elt.extract import fetch_binance_klines, fetch_coingecko_markets
from crypto_market_elt.load import load_raw_tables, write_partition
from crypto_market_elt.settings import PROJECT_ROOT, get_settings
from crypto_market_elt.validate import validate_binance_klines, validate_coingecko_markets

settings = get_settings()

# dbt resolves the warehouse path via env var (see dbt/profiles.yml).
os.environ.setdefault("ELT_DUCKDB_PATH", str(settings.pipeline.duckdb_path))

dbt_project = DbtProject(
    project_dir=PROJECT_ROOT / "dbt",
    profiles_dir=PROJECT_ROOT / "dbt",
)
dbt_project.prepare_if_dev()


@dg.asset(group_name="ingestion", description="CoinGecko top-N snapshot to Parquet (raw).")
def coingecko_markets_parquet(context: AssetExecutionContext) -> None:
    frame = fetch_coingecko_markets(
        settings.sources.coingecko, api_key=settings.secrets.coingecko_api_key
    )
    frame = validate_coingecko_markets(frame)
    write_partition(frame, settings.pipeline.data_dir, "coingecko_markets")
    context.add_output_metadata({"rows": len(frame)})


@dg.asset(group_name="ingestion", description="Binance OHLCV candles to Parquet (raw).")
def binance_klines_parquet(context: AssetExecutionContext) -> None:
    config = settings.sources.binance
    total = 0
    for symbol in config.symbols:
        frame = fetch_binance_klines(config, symbol)
        frame = validate_binance_klines(frame)
        write_partition(
            frame, settings.pipeline.data_dir, "binance_klines", filename=f"{symbol}.parquet"
        )
        total += len(frame)
    context.add_output_metadata({"rows": total, "symbols": len(config.symbols)})


def _load_one(dataset: str) -> int:
    counts = load_raw_tables(
        duckdb_path=settings.pipeline.duckdb_path,
        data_dir=settings.pipeline.data_dir,
        raw_schema=settings.pipeline.raw_schema,
        datasets=(dataset,),
    )
    return counts.get(dataset, 0)


# Keys ["raw", <table>] match dbt sources, so the dependency graph
# ingestion -> raw -> staging -> marts wires up automatically.
@dg.asset(
    key=["raw", "coingecko_markets"],
    deps=[coingecko_markets_parquet],
    group_name="warehouse",
    description="Load CoinGecko Parquet partitions into DuckDB.",
)
def raw_coingecko_markets(context: AssetExecutionContext) -> None:
    context.add_output_metadata({"rows": _load_one("coingecko_markets")})


@dg.asset(
    key=["raw", "binance_klines"],
    deps=[binance_klines_parquet],
    group_name="warehouse",
    description="Load Binance Parquet partitions into DuckDB.",
)
def raw_binance_klines(context: AssetExecutionContext) -> None:
    context.add_output_metadata({"rows": _load_one("binance_klines")})


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


daily_job = dg.define_asset_job("daily_elt", selection="*")

daily_schedule = dg.ScheduleDefinition(
    job=daily_job,
    cron_schedule="0 6 * * *",  # 06:00 UTC: after the daily candle closes
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

defs = dg.Definitions(
    assets=[
        coingecko_markets_parquet,
        binance_klines_parquet,
        raw_coingecko_markets,
        raw_binance_klines,
        dbt_models,
    ],
    schedules=[daily_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
