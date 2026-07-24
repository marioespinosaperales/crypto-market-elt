"""IsolationForest second-line QC on OHLCV features."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest

from crypto_market_elt.ml.features import FEATURE_COLUMNS, build_feature_matrix
from crypto_market_elt.settings import PROJECT_ROOT


@dataclass(frozen=True)
class AnomalyResult:
    frame: pd.DataFrame
    anomaly_rate: float
    n_anomalies: int
    n_rows: int
    top_flags: list[dict[str, Any]]
    seed: int


def fit_anomaly_model(
    ohlcv: pd.DataFrame,
    *,
    seed: int = 42,
    contamination: float = 0.05,
) -> IsolationForest:
    features = build_feature_matrix(ohlcv)
    x = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=seed,
    )
    model.fit(x)
    return model


def score_ohlcv(
    ohlcv: pd.DataFrame,
    *,
    seed: int = 42,
    contamination: float = 0.05,
    top_k: int = 5,
) -> AnomalyResult:
    features = build_feature_matrix(ohlcv)
    x = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=seed,
    )
    preds = model.fit_predict(x)  # -1 anomaly, 1 normal
    scores = model.decision_function(x)
    features = features.copy()
    features["is_anomaly"] = preds == -1
    features["anomaly_score"] = scores
    n_anom = int(features["is_anomaly"].sum())
    n_rows = int(len(features))
    ranked = features.sort_values("anomaly_score").head(top_k)
    top_flags = [
        {
            "open_time_ms": int(row["open_time_ms"]),
            "symbol": str(row.get("symbol", "")),
            "close": float(row["close"]),
            "return_1d": float(row["return_1d"]),
            "volume": float(row["volume"]),
            "anomaly_score": float(row["anomaly_score"]),
            "is_anomaly": bool(row["is_anomaly"]),
        }
        for _, row in ranked.iterrows()
    ]
    return AnomalyResult(
        frame=features,
        anomaly_rate=round(n_anom / n_rows, 4) if n_rows else 0.0,
        n_anomalies=n_anom,
        n_rows=n_rows,
        top_flags=top_flags,
        seed=seed,
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Crypto market OHLCV anomaly report",
        "",
        "IsolationForest second-line QC on validated OHLCV features "
        "(returns, log-volume, range, rolling z-scores).",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(report.get("summary", {}), indent=2),
        "```",
        "",
        "## Top flags (lowest decision_function)",
        "",
        "```json",
        json.dumps(report.get("top_flags", []), indent=2),
        "```",
        "",
        "## Caveats",
        "",
    ]
    for c in report.get("caveats", []):
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], *, artifacts_dir: Path | None = None) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "ml_anomaly_report.md"
    json_path = out_dir / "ml_anomaly_report.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path


def build_report(result: AnomalyResult, *, source: str) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": source,
        "summary": {
            "n_rows": result.n_rows,
            "n_anomalies": result.n_anomalies,
            "anomaly_rate": result.anomaly_rate,
            "seed": result.seed,
            "feature_columns": FEATURE_COLUMNS,
        },
        "top_flags": result.top_flags,
        "caveats": [
            "Complements pandera contracts; does not replace ingestion validation.",
            "Synthetic augmentation is used when the fixture series is short.",
            "Anomalies are unsupervised flags for review, not automatic deletes.",
        ],
    }


def spike_is_flagged(result: AnomalyResult) -> bool:
    """True if the lowest-score row looks like a return/volume spike."""
    if not result.top_flags:
        return False
    top = result.top_flags[0]
    return bool(top["is_anomaly"] or abs(top["return_1d"]) > 0.1)
