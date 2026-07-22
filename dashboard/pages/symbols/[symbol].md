# {params.symbol}

```sql history
select
    trade_date,
    open,
    high,
    low,
    close,
    daily_return,
    volatility_7d,
    volatility_30d,
    quote_volume
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
order by trade_date
```

```sql latest
select
    close,
    daily_return,
    volatility_30d,
    quote_volume
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
order by trade_date desc
limit 1
```

<BigValue data={latest} value=close title="Last close" fmt=usd2 />
<BigValue data={latest} value=daily_return title="Daily return" fmt=pct2 />
<BigValue data={latest} value=volatility_30d title="Volatility (30d)" fmt=pct2 />
<BigValue data={latest} value=quote_volume title="Volume (24h)" fmt=usd />

```sql price_series
select trade_date, close
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
order by trade_date
```

<LineChart
  data={price_series}
  x=trade_date
  y=close
  title="Daily close, last 365 days"
  yFmt=usd2
  handleMissing=connect
/>

```sql vol_series
select trade_date, volatility_7d, volatility_30d
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
  and (volatility_7d is not null or volatility_30d is not null)
order by trade_date
```

<LineChart
  data={vol_series}
  x=trade_date
  y={["volatility_7d", "volatility_30d"]}
  title="Rolling volatility of daily returns"
  yFmt=pct1
  handleMissing=connect
/>

```sql returns
select trade_date, daily_return
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
  and daily_return is not null
order by trade_date
```

<BarChart
  data={returns}
  x=trade_date
  y=daily_return
  title="Daily returns"
  yFmt=pct0
/>

```sql volumes
select trade_date, quote_volume
from crypto.daily_ohlcv
where symbol = '${params.symbol}'
order by trade_date
```

<BarChart
  data={volumes}
  x=trade_date
  y=quote_volume
  title="Quote volume (USDT)"
  yFmt=usd
/>

[← Back to overview](/)
