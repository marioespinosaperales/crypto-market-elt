"""CLI for ML companions.

Default: anomaly report.
``--timeseries``: naive vs ARIMA research report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from crypto_market_elt.ml.anomaly import build_report, score_ohlcv, write_report
from crypto_market_elt.ml.features import load_binance_klines, synthesize_ohlcv
from crypto_market_elt.ml.timeseries import build_timeseries_report, write_timeseries_report
from crypto_market_elt.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "binance_klines.json"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Crypto market ML / research reports")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--timeseries",
        action="store_true",
        help="Write naive vs ARIMA forecast eval report",
    )
    args = parser.parse_args(argv)

    if not args.fixture.exists():
        logger.error("Fixture not found: %s", args.fixture)
        return 1

    if args.timeseries:
        report = build_timeseries_report(fixture=args.fixture, seed=args.seed)
        path = write_timeseries_report(report)
        ev = report["evidence"]
        logger.info(
            "Wrote timeseries report → %s (arima_mae=%.4f naive_mae=%.4f)",
            path,
            ev["arima"]["mae"],
            ev["naive"]["mae"],
        )
        print(path)
        return 0

    base = load_binance_klines(args.fixture)
    ohlcv = synthesize_ohlcv(base, seed=args.seed, inject_spike=True)
    result = score_ohlcv(ohlcv, seed=args.seed)
    report = build_report(result, source=str(args.fixture))
    path = write_report(report)
    logger.info(
        "Wrote anomaly report → %s (rate=%.2f%%)",
        path,
        100 * result.anomaly_rate,
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
