-- Métricas diarias por símbolo: retorno, volatilidad rolling (7d/30d) y volumen.
with daily as (
    select
        symbol,
        trade_date,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        trade_count,
        close / lag(close) over (partition by symbol order by trade_date) - 1
            as daily_return
    from {{ ref('stg_binance_klines') }}
)

select
    *,
    stddev_samp(daily_return) over (
        partition by symbol order by trade_date
        rows between 6 preceding and current row
    ) as volatility_7d,
    stddev_samp(daily_return) over (
        partition by symbol order by trade_date
        rows between 29 preceding and current row
    ) as volatility_30d,
    avg(quote_volume) over (
        partition by symbol order by trade_date
        rows between 29 preceding and current row
    ) as avg_quote_volume_30d
from daily
