# OHLCV research notes (atomic studies)

Hypothesis-driven measurement hygiene. Runnable via:

```bash
make research   # → artifacts/research_timeseries.md + research_event_study.md
```

---

## 1. Time-series forecast eval

### Hypothesis

Short-horizon close levels are partially predictable from recent OHLCV history beyond a
naive last-value baseline.

### Method

1. Load Binance kline fixture and expand synthetically (deterministic seed)
2. Hold out the last N closes
3. Compare rolling one-step **naive** vs **ARIMA(1,1,1)** forecasts
4. Report MAE, RMSE, and directional accuracy

### Evidence

See `artifacts/research_timeseries.md` after `make research`.

### Limitations

- Synthetic augmentation demonstrates methodology; not a claim about live trading edge
- ARIMA is a simple baseline, not a production strategy
- No causal identification — this is predictive measurement discipline

---

## 2. Quasi-experimental event study

### Hypothesis

A discrete price shock produces a detectable shift in mean log returns in a short
post-event window relative to a matched pre-event window.

### Method

1. Inject a known 12% close jump at a fixed index in synthetic OHLCV
2. Compare the event-bar log return to the pre-window mean
3. Bootstrap null: redraw the event return from the pre-window; report p-value + 95% CI

### Evidence

See `artifacts/research_event_study.md` after `make research`.

### Limitations

- Synthetic shock demonstrates identification hygiene, not a live listing/hack study
- Not a full difference-in-differences with an untreated control series
- No volume/funding/cross-venue confounders

---

## Why it matters / next measurements

Product and research teams need explicit baselines, holdout metrics, and event-window
templates (with uncertainty) before trusting any signal. The same rigor applies to
latency and market-structure measurements (inclusion delay, builder/PBS incidence)
before they become product primitives.

## Related code

- `src/crypto_market_elt/ml/timeseries.py`
- `src/crypto_market_elt/ml/event_study.py`
- Anomaly companion: `make ml` (IsolationForest second-line QC)
