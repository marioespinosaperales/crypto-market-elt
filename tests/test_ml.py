from pathlib import Path

from crypto_market_elt.ml.anomaly import score_ohlcv, spike_is_flagged, write_report
from crypto_market_elt.ml.features import (
    FEATURE_COLUMNS,
    build_feature_matrix,
    load_binance_klines,
    synthesize_ohlcv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "binance_klines.json"


def test_features_and_spike_flagged(tmp_path):
    base = load_binance_klines(FIXTURE)
    ohlcv = synthesize_ohlcv(base, n_extra=50, seed=7, inject_spike=True)
    feats = build_feature_matrix(ohlcv)
    assert set(FEATURE_COLUMNS).issubset(feats.columns)
    assert len(feats) >= 50

    result = score_ohlcv(ohlcv, seed=7, contamination=0.08)
    assert result.n_rows == len(ohlcv)
    assert spike_is_flagged(result)

    clean = synthesize_ohlcv(base, n_extra=50, seed=7, inject_spike=False)
    clean_result = score_ohlcv(clean, seed=7, contamination=0.05)
    assert clean_result.anomaly_rate <= 0.15

    from crypto_market_elt.ml.anomaly import build_report

    report = build_report(result, source=str(FIXTURE))
    out = write_report(report, artifacts_dir=tmp_path)
    assert out.exists()
    assert "anomaly report" in out.read_text(encoding="utf-8").lower()
