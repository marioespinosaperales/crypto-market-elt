from pathlib import Path

from crypto_market_elt.ml.event_study import (
    build_event_study_report,
    event_study,
    write_event_study_report,
)
from crypto_market_elt.ml.features import load_binance_klines, synthesize_ohlcv

FIXTURE = Path(__file__).parent / "fixtures" / "binance_klines.json"


def test_event_study_detects_injected_jump():
    base = load_binance_klines(FIXTURE)
    ohlcv = synthesize_ohlcv(base, n_extra=80, seed=3, inject_spike=False)
    mid = len(base) + 40
    ohlcv = ohlcv.copy()
    prev = float(ohlcv.iloc[mid - 1]["close"])
    ohlcv.iloc[mid, ohlcv.columns.get_loc("close")] = prev * 1.15
    result = event_study(ohlcv, event_index=mid, pre_window=10, post_window=10, seed=3)
    assert result["abs_price_jump_pct"] > 10.0
    assert result["diff_event_minus_pre"] > 0.05
    assert result["bootstrap_p_event_vs_pre"] < 0.05
    assert len(result["bootstrap_ci_95"]) == 2


def test_event_study_report_artifact(tmp_path):
    report = build_event_study_report(fixture=FIXTURE, seed=5)
    assert "hypothesis" in report
    out = write_event_study_report(report, artifacts_dir=tmp_path)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "event-study" in body.lower()
    assert "Evidence" in body
