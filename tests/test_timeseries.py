from pathlib import Path

from crypto_market_elt.ml.features import load_binance_klines, synthesize_ohlcv
from crypto_market_elt.ml.timeseries import (
    build_timeseries_report,
    evaluate_forecasts,
    write_timeseries_report,
)

FIXTURE = Path(__file__).parent / "fixtures" / "binance_klines.json"


def test_evaluate_forecasts_writes_comparison():
    base = load_binance_klines(FIXTURE)
    ohlcv = synthesize_ohlcv(base, n_extra=60, seed=1, inject_spike=False)
    result = evaluate_forecasts(ohlcv["close"].to_numpy(), holdout=8)
    assert "naive" in result and "arima" in result
    assert result["naive"]["mae"] >= 0.0
    assert result["arima"]["mae"] >= 0.0
    assert result["n_holdout"] == 8


def test_timeseries_report_artifact(tmp_path):
    report = build_timeseries_report(fixture=FIXTURE, seed=2, holdout=8)
    assert "hypothesis" in report
    out = write_timeseries_report(report, artifacts_dir=tmp_path)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "time-series research report" in body.lower()
    assert "Evidence" in body
