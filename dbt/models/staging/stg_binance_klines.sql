-- Velas OHLCV limpias y deduplicadas por (symbol, open_time): gana la ingesta
-- más reciente. Solo llegan velas cerradas (el extractor descarta la abierta).
with ranked as (
    select
        symbol,
        "interval",
        open_time,
        cast(open_time as date) as trade_date,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        trade_count,
        ingested_date,
        row_number() over (
            partition by symbol, open_time
            order by ingested_date desc
        ) as rn
    from {{ source('raw', 'binance_klines') }}
)

select * exclude (rn)
from ranked
where rn = 1
