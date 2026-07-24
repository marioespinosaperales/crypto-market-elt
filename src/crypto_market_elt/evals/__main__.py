"""CLI: ``uv run python -m crypto_market_elt.evals`` → artifacts/qc_scorecard.md"""

from __future__ import annotations

import logging
import sys

from crypto_market_elt.evals.scorecard import build_scorecard, write_scorecard
from crypto_market_elt.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    scorecard = build_scorecard(duckdb_path=settings.pipeline.duckdb_path)
    path = write_scorecard(scorecard)
    logger.info(
        "Wrote scorecard → %s (probe pass_rate=%.0f%%)",
        path,
        100 * scorecard.probe_summary.get("pass_rate", 0.0),
    )
    print(path)
    failed = scorecard.probe_summary.get("failed", 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
