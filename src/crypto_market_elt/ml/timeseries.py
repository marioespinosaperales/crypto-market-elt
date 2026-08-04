"""Naive vs ARIMA short-horizon forecast eval on OHLCV closes."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from statsmodels.tsa.arima.model import ARIMA

from crypto_market_elt.ml.features import load_binance_klines, synthesize_ohlcv
from crypto_market_elt.settings import PROJECT_ROOT


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(math.sqrt(np.mean(err**2)))
    # Directional accuracy on first differences of the series vs predicted path
    if len(y_true) < 2:
        directional = 0.0
    else:
        true_dir = np.sign(np.diff(y_true))
        pred_dir = np.sign(y_pred[1:] - y_true[:-1])
        directional = float(np.mean(true_dir == pred_dir))
    return {
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "directional_accuracy": round(directional, 4),
    }


def evaluate_forecasts(
    closes: np.ndarray,
    *,
    holdout: int = 10,
    arima_order: tuple[int, int, int] = (1, 1, 1),
) -> dict[str, Any]:
    """Compare naive (last value) vs ARIMA one-step forecasts on a holdout tail."""
    closes = np.asarray(closes, dtype=float)
    if len(closes) <= holdout + 5:
        raise ValueError("Need a longer series than holdout+5 for forecast eval")

    train = closes[:-holdout]
    test = closes[-holdout:]

    naive_preds = []
    arima_preds = []
    history = list(train)
    for actual in test:
        naive_preds.append(history[-1])
        try:
            fitted = ARIMA(history, order=arima_order).fit()
            arima_preds.append(float(fitted.forecast(steps=1)[0]))
        except Exception:  # noqa: BLE001 — fall back to naive if ARIMA fails
            arima_preds.append(history[-1])
        history.append(float(actual))

    y_true = np.asarray(test, dtype=float)
    naive_m = _metrics(y_true, np.asarray(naive_preds, dtype=float))
    arima_m = _metrics(y_true, np.asarray(arima_preds, dtype=float))
    return {
        "n_train": int(len(train)),
        "n_holdout": int(holdout),
        "arima_order": list(arima_order),
        "naive": naive_m,
        "arima": arima_m,
        "arima_beats_naive_mae": bool(arima_m["mae"] < naive_m["mae"]),
    }


def build_timeseries_report(
    *,
    fixture: Path,
    seed: int = 42,
    holdout: int = 10,
) -> dict[str, Any]:
    base = load_binance_klines(fixture)
    # Smooth series without giant terminal spike for fair forecast eval
    ohlcv = synthesize_ohlcv(base, n_extra=80, seed=seed, inject_spike=False)
    closes = ohlcv["close"].to_numpy(dtype=float)
    eval_result = evaluate_forecasts(closes, holdout=holdout)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(fixture),
        "hypothesis": (
            "Short-horizon close levels are partially predictable from recent OHLCV "
            "history beyond a naive last-value baseline."
        ),
        "method": (
            "Expand fixture OHLCV synthetically, then compare rolling one-step naive "
            "vs ARIMA(1,1,1) forecasts on a holdout tail (MAE, RMSE, directional accuracy)."
        ),
        "evidence": eval_result,
        "limitations": [
            "Synthetic augmentation is for methodology; not a claim about live alpha.",
            "ARIMA is a simple baseline — not a production trading model.",
            "No causal identification; this is predictive measurement hygiene.",
        ],
        "why_it_matters": (
            "Product and research teams need explicit baselines and holdout metrics "
            "before trusting any signal — the same rigor applies to latency and "
            "market-structure measurements."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OHLCV time-series research report",
        "",
        f"Generated: `{report.get('generated_at')}`",
        f"Source: `{report.get('source')}`",
        "",
        "## Hypothesis",
        "",
        str(report.get("hypothesis", "")),
        "",
        "## Method",
        "",
        str(report.get("method", "")),
        "",
        "## Evidence",
        "",
        "```json",
        json.dumps(report.get("evidence", {}), indent=2),
        "```",
        "",
        "## Limitations",
        "",
    ]
    for item in report.get("limitations", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Why it matters",
            "",
            str(report.get("why_it_matters", "")),
            "",
        ]
    )
    return "\n".join(lines)


def write_timeseries_report(
    report: dict[str, Any],
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "research_timeseries.md"
    json_path = out_dir / "research_timeseries.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path
