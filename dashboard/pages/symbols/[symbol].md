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

<BigValue data={latest} value=close title="Last close" fmt='$#,##0.00' />
<BigValue data={latest} value=daily_return title="Daily return" fmt=pct2 />
<BigValue data={latest} value=volatility_30d title="Volatility (30d)" fmt=pct2 />
<BigValue data={latest} value=quote_volume title="Volume (24h)" fmt='$#,##0,,"M"' />

<LineChart
  data={history}
  x=trade_date
  y=close
  title="Daily close, last 365 days"
  yFmt='$#,##0.00'
/>

<LineChart
  data={history}
  x=trade_date
  y={['volatility_7d', 'volatility_30d']}
  title="Rolling volatility of daily returns"
  yFmt=pct1
/>

<BarChart
  data={history}
  x=trade_date
  y=daily_return
  title="Daily returns"
  yFmt=pct0
/>

<BarChart
  data={history}
  x=trade_date
  y=quote_volume
  title="Quote volume (USDT)"
  yFmt='$#,##0,,"M"'
/>

[← Back to overview](/)
