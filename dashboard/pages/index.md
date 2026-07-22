---
title: Crypto Market Overview
---

Daily ELT pipeline: CoinGecko + Binance → Parquet → DuckDB → dbt marts → this dashboard.
Refreshed hourly by GitHub Actions. Source: [crypto-market-elt](https://github.com/marioespinosaperales/crypto-market-elt).

```sql latest_overview
select *
from crypto.market_overview
order by snapshot_date desc
limit 1
```

<BigValue
  data={latest_overview}
  value=total_market_cap
  title="Total Market Cap (top 100)"
  fmt=usd
/>

<BigValue
  data={latest_overview}
  value=btc_dominance
  title="BTC Dominance"
  fmt=pct1
/>

<BigValue
  data={latest_overview}
  value=top10_share
  title="Top 10 Concentration"
  fmt=pct1
/>

<BigValue
  data={latest_overview}
  value=coins_tracked
  title="Coins Tracked"
/>

## Price history (Binance, last ~365 days)

```sql prices
select
    trade_date,
    symbol,
    close
from crypto.daily_ohlcv
order by trade_date, symbol
```

<LineChart
  data={prices}
  x=trade_date
  y=close
  series=symbol
  title="Daily close by pair"
  yFmt=usd2
  handleMissing=connect
/>

## Rolling volatility (30d)

```sql vol
select
    trade_date,
    symbol,
    volatility_30d
from crypto.daily_ohlcv
where volatility_30d is not null
order by trade_date, symbol
```

<LineChart
  data={vol}
  x=trade_date
  y=volatility_30d
  series=symbol
  title="30-day rolling volatility of daily returns"
  yFmt=pct1
  handleMissing=connect
/>

## Tracked pairs

Click a row to drill into that pair.

```sql latest_by_symbol
select
    symbol,
    '/symbols/' || symbol as symbol_link,
    max_by(close, trade_date) as last_close,
    max_by(daily_return, trade_date) as last_daily_return,
    max_by(volatility_30d, trade_date) as volatility_30d,
    max_by(avg_quote_volume_30d, trade_date) as avg_quote_volume_30d,
    max(trade_date) as last_trade_date
from crypto.daily_ohlcv
group by symbol, symbol_link
order by avg_quote_volume_30d desc
```

<DataTable data={latest_by_symbol} link=symbol_link>
  <Column id=symbol />
  <Column id=last_close fmt=usd2 title="Last close" />
  <Column id=last_daily_return fmt=pct2 title="Daily return" contentType=delta />
  <Column id=volatility_30d fmt=pct2 title="Volatility (30d)" />
  <Column id=avg_quote_volume_30d fmt=usd title="Avg volume 30d" />
  <Column id=last_trade_date title="Last candle" />
</DataTable>
