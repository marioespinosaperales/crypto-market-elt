-- Vista macro del mercado por día de snapshot: market cap total, dominancia BTC
-- y concentración del top 10.
with snapshot as (
    select
        snapshot_date,
        sum(market_cap) as total_market_cap,
        sum(volume_24h_usd) as total_volume_24h,
        count(*) as coins_tracked,
        sum(case when coin_id = 'bitcoin' then market_cap else 0 end)
            as btc_market_cap,
        sum(case when market_cap_rank <= 10 then market_cap else 0 end)
            as top10_market_cap
    from {{ ref('stg_coingecko_markets') }}
    where market_cap is not null
    group by snapshot_date
)

select
    snapshot_date,
    total_market_cap,
    total_volume_24h,
    coins_tracked,
    btc_market_cap / total_market_cap as btc_dominance,
    top10_market_cap / total_market_cap as top10_share
from snapshot
