"""Quasi-experimental event study on synthetic OHLCV around a price shock.

Compares the event-bar log return to the pre-window mean, with a bootstrap null
that redraws the event return from the pre-window distribution. Methodology demo,
not causal identification of a live market event.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from crypto_market_elt.ml.features import load_binance_klines, synthesize_ohlcv
from crypto_market_elt.settings import PROJECT_ROOT


def _log_returns(closes: np.ndarray) -> np.ndarray:
    closes = np.asarray(closes, dtype=float)
    return np.diff(np.log(np.maximum(closes, 1e-12)))


def event_study(
    ohlcv: pd.DataFrame,
    *,
    event_index: int,
    pre_window: int = 10,
    post_window: int = 10,
    n_boot: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Event-bar return vs pre-window mean; optional post-window mean for context."""
    closes = ohlcv["close"].to_numpy(dtype=float)
    if event_index < pre_window + 1 or event_index + post_window >= len(closes):
        raise ValueError("event_index leaves insufficient pre/post window")

    rets = _log_returns(closes)
    # returns[i] = log(close[i+1]/close[i]); jump into event bar is rets[event_index - 1]
    pre = rets[event_index - 1 - pre_window : event_index - 1]
    event_ret = float(rets[event_index - 1])
    post = rets[event_index : event_index + post_window]

    pre_mean = float(np.mean(pre))
    post_mean = float(np.mean(post))
    diff = event_ret - pre_mean

    rng = np.random.default_rng(seed)
    boot = [float(rng.choice(pre) - pre_mean) for _ in range(n_boot)]
    boot_arr = np.asarray(boot, dtype=float)
    p_value = float(np.mean(np.abs(boot_arr) >= abs(diff)))
    ci_lo = float(np.percentile(boot_arr, 2.5))
    ci_hi = float(np.percentile(boot_arr, 97.5))

    return {
        "event_index": int(event_index),
        "pre_window": int(pre_window),
        "post_window": int(post_window),
        "n_pre": int(len(pre)),
        "n_post": int(len(post)),
        "pre_mean_log_return": round(pre_mean, 6),
        "event_log_return": round(event_ret, 6),
        "post_mean_log_return": round(post_mean, 6),
        "diff_event_minus_pre": round(diff, 6),
        "bootstrap_ci_95": [round(ci_lo, 6), round(ci_hi, 6)],
        "bootstrap_p_event_vs_pre": round(p_value, 4),
        "event_close": round(float(closes[event_index]), 4),
        "pre_close": round(float(closes[event_index - 1]), 4),
        "abs_price_jump_pct": round(
            100.0 * (closes[event_index] / closes[event_index - 1] - 1.0), 4
        ),
    }


def build_event_study_report(
    *,
    fixture: Path,
    seed: int = 42,
    n_extra: int = 80,
    pre_window: int = 12,
) -> dict[str, Any]:
    base = load_binance_klines(fixture)
    ohlcv = synthesize_ohlcv(base, n_extra=n_extra, seed=seed, inject_spike=False)
    mid = len(base) + n_extra // 2
    shocked = ohlcv.copy()
    prev = float(shocked.iloc[mid - 1]["close"])
    shocked.iloc[mid, shocked.columns.get_loc("close")] = prev * 1.12
    high_i = shocked.columns.get_loc("high")
    shocked.iloc[mid, high_i] = max(float(shocked.iloc[mid]["high"]), prev * 1.12)

    evidence = event_study(
        shocked,
        event_index=mid,
        pre_window=pre_window,
        post_window=pre_window,
        seed=seed,
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(fixture),
        "hypothesis": (
            "A discrete price shock produces an event-bar log return that differs from "
            "the pre-event mean under a bootstrap null redrawing the event from the "
            "pre-window (quasi-experimental event study on synthetic OHLCV)."
        ),
        "method": (
            "Inject a 12% close jump at a known index; compare the event-bar log return "
            f"to the mean of the prior {pre_window} returns; report difference with a "
            "bootstrap p-value (null: event redrawn from the pre-window) and 95% CI."
        ),
        "evidence": evidence,
        "limitations": [
            "Synthetic shock shows identification hygiene, not a live listing/hack claim.",
            "Bootstrap vs pre-window is not a full DiD with a control series.",
            "No confounders (volume regime, funding, cross-venue) are modeled.",
        ],
        "product_implications": [
            "Market-structure / networking products should ship event-window measurement "
            "templates (pre/event + uncertainty) before claiming latency or inclusion wins.",
            "Same pattern applies to builder/PBS incidence around contended blocks: define "
            "the event, the window, and the null before productizing the metric.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OHLCV event-study research report",
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
    lines.extend(["", "## Product implications", ""])
    for item in report.get("product_implications", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_event_study_report(
    report: dict[str, Any],
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "research_event_study.md"
    json_path = out_dir / "research_event_study.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path
