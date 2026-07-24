from crypto_market_elt.evals.scorecard import (
    build_scorecard,
    contract_probe_results,
    render_markdown,
    write_scorecard,
)


def test_contract_probes_all_pass_expectations():
    probes = contract_probe_results()
    assert len(probes) >= 5
    assert all(p.passed for p in probes)


def test_scorecard_artifact(tmp_path):
    scorecard = build_scorecard(duckdb_path=tmp_path / "missing.duckdb")
    assert scorecard.probe_summary["failed"] == 0
    assert scorecard.warehouse["available"] is False
    md = render_markdown(scorecard)
    assert "Crypto market ELT QC scorecard" in md
    assert "Contract probes" in md
    out = write_scorecard(scorecard, artifacts_dir=tmp_path)
    assert out.exists()
    assert (tmp_path / "qc_scorecard.json").exists()
