-- Clean, deduplicated snapshot: if the same (coin_id, snapshot_date) was
-- ingested more than once, the latest ingestion wins.
with ranked as (
    select
        coin_id,
        lower(symbol) as symbol,
        name,
        current_price as price_usd,
        market_cap,
        cast(market_cap_rank as integer) as market_cap_rank,
        total_volume as volume_24h_usd,
        price_change_percentage_24h as pct_change_24h,
        circulating_supply,
        cast(snapshot_date as date) as snapshot_date,
        ingested_date,
        row_number() over (
            partition by coin_id, cast(snapshot_date as date)
            order by ingested_date desc
        ) as rn
    from {{ source('raw', 'coingecko_markets') }}
)

select * exclude (rn)
from ranked
where rn = 1
