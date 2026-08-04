# OHLCV time-series research (atomic study)

Hypothesis-driven forecast hygiene note. Runnable via:

```bash
make research   # → artifacts/research_timeseries.md
```

## Hypothesis

Short-horizon close levels are partially predictable from recent OHLCV history beyond a
naive last-value baseline.

## Method

1. Load Binance kline fixture and expand synthetically (deterministic seed)
2. Hold out the last N closes
3. Compare rolling one-step **naive** vs **ARIMA(1,1,1)** forecasts
4. Report MAE, RMSE, and directional accuracy

## Evidence

See `artifacts/research_timeseries.md` after `make research`.

## Limitations

- Synthetic augmentation demonstrates methodology; not a claim about live trading edge
- ARIMA is a simple baseline, not a production strategy
- No causal identification — this is predictive measurement discipline

## Why it matters / next measurements

Product and research teams need explicit baselines and holdout metrics before trusting
any signal. The same rigor applies to latency and market-structure measurements
(for example inclusion delay distributions) before they become product primitives.

## Related code

- `src/crypto_market_elt/ml/timeseries.py`
- Anomaly companion: `make ml` (IsolationForest second-line QC)
