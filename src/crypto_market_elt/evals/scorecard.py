"""QC scorecard: contract probe pass/fail rates + warehouse freshness/row sanity."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pandera

from crypto_market_elt.settings import PROJECT_ROOT
from crypto_market_elt.validate import validate_binance_klines, validate_coingecko_markets

FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


@dataclass(frozen=True)
class ProbeResult:
    name: str
    dataset: str
    expected: str  # pass | fail
    passed: bool
    detail: str


@dataclass
class Scorecard:
    generated_at: str
    probes: list[ProbeResult] = field(default_factory=list)
    probe_summary: dict[str, Any] = field(default_factory=dict)
    warehouse: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "probes": [asdict(p) for p in self.probes],
            "probe_summary": self.probe_summary,
            "warehouse": self.warehouse,
            "caveats": self.caveats,
        }


def _coingecko_frame(payload: list[dict], *, snapshot_date: dt.date | None = None) -> pd.DataFrame:
    columns = [
        "id",
        "symbol",
        "name",
        "current_price",
        "market_cap",
        "market_cap_rank",
        "total_volume",
        "price_change_percentage_24h",
        "circulating_supply",
        "last_updated",
    ]
    frame = pd.DataFrame(payload)[columns].rename(columns={"id": "coin_id"})
    frame["vs_currency"] = "usd"
    frame["snapshot_date"] = pd.Timestamp(snapshot_date or dt.datetime.now(UTC).date())
    return frame


def _binance_frame(payload: list[list], *, symbol: str = "BTCUSDT") -> pd.DataFrame:
    fields = [
        "open_time_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time_ms",
        "quote_volume",
        "trade_count",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
        "_ignore",
    ]
    frame = pd.DataFrame(payload, columns=fields).drop(columns="_ignore")
    for col in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ):
        frame[col] = pd.to_numeric(frame[col])
    frame["trade_count"] = frame["trade_count"].astype("int64")
    frame["open_time"] = pd.to_datetime(frame["open_time_ms"], unit="ms", utc=True)
    frame["symbol"] = symbol
    frame["interval"] = "1d"
    return frame


def _run_probe(
    name: str,
    dataset: str,
    expected: str,
    fn,
) -> ProbeResult:
    try:
        fn()
        passed = expected == "pass"
        detail = "validated" if passed else "expected failure but schema accepted rows"
    except (pandera.errors.SchemaError, pandera.errors.SchemaErrors) as exc:
        passed = expected == "fail"
        detail = str(exc).split("\n", 1)[0][:200]
    return ProbeResult(name=name, dataset=dataset, expected=expected, passed=passed, detail=detail)


def contract_probe_results(*, fixtures_dir: Path | None = None) -> list[ProbeResult]:
    """Executable contract probes: good fixtures pass; mutated rows fail."""
    root = fixtures_dir or FIXTURES
    cg_payload = json.loads((root / "coingecko_markets.json").read_text(encoding="utf-8"))
    bn_payload = json.loads((root / "binance_klines.json").read_text(encoding="utf-8"))

    probes: list[ProbeResult] = []

    good_cg = _coingecko_frame(cg_payload)
    probes.append(
        _run_probe(
            "coingecko_valid_fixture",
            "coingecko_markets",
            "pass",
            lambda: validate_coingecko_markets(good_cg),
        )
    )

    bad_price = _coingecko_frame(cg_payload)
    bad_price = bad_price.copy()
    bad_price.loc[bad_price.index[0], "current_price"] = -1.0
    probes.append(
        _run_probe(
            "coingecko_rejects_negative_price",
            "coingecko_markets",
            "fail",
            lambda: validate_coingecko_markets(bad_price),
        )
    )

    bad_dup = _coingecko_frame(cg_payload)
    bad_dup = bad_dup.copy()
    if len(bad_dup) >= 2:
        bad_dup.loc[bad_dup.index[1], "coin_id"] = bad_dup.loc[bad_dup.index[0], "coin_id"]
    probes.append(
        _run_probe(
            "coingecko_rejects_duplicate_coin_id",
            "coingecko_markets",
            "fail",
            lambda: validate_coingecko_markets(bad_dup),
        )
    )

    good_bn = _binance_frame(bn_payload)
    probes.append(
        _run_probe(
            "binance_valid_fixture",
            "binance_klines",
            "pass",
            lambda: validate_binance_klines(good_bn),
        )
    )

    bad_ohlc = _binance_frame(bn_payload).copy()
    bad_ohlc.loc[bad_ohlc.index[0], "high"] = bad_ohlc.loc[bad_ohlc.index[0], "low"] - 1.0
    probes.append(
        _run_probe(
            "binance_rejects_high_lt_low",
            "binance_klines",
            "fail",
            lambda: validate_binance_klines(bad_ohlc),
        )
    )

    return probes


def summarize_probes(probes: list[ProbeResult]) -> dict[str, Any]:
    total = len(probes)
    passed = sum(1 for p in probes if p.passed)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
    }


def warehouse_sanity(duckdb_path: Path) -> dict[str, Any]:
    if not duckdb_path.exists():
        return {"available": False, "reason": f"warehouse not found: {duckdb_path}"}

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        out: dict[str, Any] = {"available": True, "tables": sorted(tables), "row_counts": {}}
        for table in ("mart_daily_ohlcv", "mart_market_overview", "stg_binance_klines"):
            if table in tables:
                count = con.execute(f"select count(*) from {table}").fetchone()[0]
                out["row_counts"][table] = int(count)

        if "mart_daily_ohlcv" in tables:
            freshness = con.execute(
                """
                select
                    count(distinct symbol) as symbols,
                    max(trade_date) as max_day,
                    min(trade_date) as min_day
                from mart_daily_ohlcv
                """
            ).fetchone()
            out["ohlcv"] = {
                "symbols": int(freshness[0]),
                "max_day": str(freshness[1]),
                "min_day": str(freshness[2]),
            }
        return out
    finally:
        con.close()


def build_scorecard(*, duckdb_path: Path | None = None) -> Scorecard:
    probes = contract_probe_results()
    summary = summarize_probes(probes)
    warehouse = warehouse_sanity(duckdb_path) if duckdb_path is not None else {"available": False}
    caveats: list[str] = []
    if summary["failed"]:
        caveats.append(
            f"{summary['failed']} contract probe(s) failed — ingestion gates may be broken."
        )
    if not warehouse.get("available"):
        caveats.append(
            "Warehouse unavailable: scorecard covers contract probes only. "
            "Run the pipeline to enable freshness/row-count sanity."
        )
    elif warehouse.get("row_counts", {}).get("mart_daily_ohlcv", 0) == 0:
        caveats.append("mart_daily_ohlcv is empty — downstream analytics are not usable yet.")

    return Scorecard(
        generated_at=datetime.now(UTC).isoformat(),
        probes=probes,
        probe_summary=summary,
        warehouse=warehouse,
        caveats=caveats,
    )


def render_markdown(scorecard: Scorecard) -> str:
    lines = [
        "# Crypto market ELT QC scorecard",
        "",
        f"Generated: `{scorecard.generated_at}`",
        "",
        "## Contract probes",
        "",
        "| Probe | Dataset | Expected | Passed | Detail |",
        "|---|---|---|---|---|",
    ]
    for p in scorecard.probes:
        detail = p.detail.replace("|", "\\|")
        lines.append(
            f"| {p.name} | {p.dataset} | {p.expected} | {p.passed} | {detail} |"
        )
    lines.extend(
        [
            "",
            "### Summary",
            "",
            "```json",
            json.dumps(scorecard.probe_summary, indent=2),
            "```",
            "",
            "## Warehouse sanity",
            "",
            "```json",
            json.dumps(scorecard.warehouse, indent=2, default=str),
            "```",
            "",
            "## Caveats",
            "",
        ]
    )
    if scorecard.caveats:
        lines.extend(f"- {c}" for c in scorecard.caveats)
    else:
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)


def write_scorecard(
    scorecard: Scorecard,
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "qc_scorecard.md"
    json_path = out_dir / "qc_scorecard.json"
    md_path.write_text(render_markdown(scorecard), encoding="utf-8")
    payload = json.dumps(scorecard.to_dict(), indent=2, default=str) + "\n"
    json_path.write_text(payload, encoding="utf-8")
    return md_path
