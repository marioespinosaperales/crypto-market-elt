---
title: Crypto Market Overview
---

Daily ELT pipeline: CoinGecko + Binance → Parquet → DuckDB → dbt marts → this dashboard.
Refreshed automatically by GitHub Actions. Source code: [crypto-market-elt](https://github.com/marioespinosaperales/crypto-market-elt).

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
  fmt='$#,##0.0,,,"B"'
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

## Market history

One snapshot per pipeline run — these series grow as the scheduled job keeps running.

```sql overview_history
select
    snapshot_date,
    total_market_cap,
    btc_dominance,
    top10_share
from crypto.market_overview
order by snapshot_date
```

<LineChart
  data={overview_history}
  x=snapshot_date
  y=total_market_cap
  title="Total market cap over time"
  yFmt='$#,##0.0,,,"B"'
/>

<LineChart
  data={overview_history}
  x=snapshot_date
  y={['btc_dominance', 'top10_share']}
  title="BTC dominance and top-10 concentration"
  yFmt=pct0
/>

## Tracked pairs (Binance, daily candles)

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
  <Column id=last_close fmt='$#,##0.00' title="Last close" />
  <Column id=last_daily_return fmt=pct2 title="Daily return" contentType=delta />
  <Column id=volatility_30d fmt=pct2 title="Volatility (30d)" />
  <Column id=avg_quote_volume_30d fmt='$#,##0,,"M"' title="Avg volume 30d" />
  <Column id=last_trade_date title="Last candle" />
</DataTable>
