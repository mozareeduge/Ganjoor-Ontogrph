"""Tests for ontograph.validate (ledger row P7.4, spec §69 gates 1-5)."""
import json
import pathlib

from ontograph.cli import main as cli_main
from ontograph.validate import run_gates

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"
REPO_ROOT = pathlib.Path(__file__).parent.parent


def test_all_five_gates_pass_against_the_fixture(tmp_path):
    results = run_gates(REPO_ROOT, FIXTURE_ROOT, tmp_path / "ontograph-workspaces")
    assert [r.gate for r in results] == [1, 2, 3, 4, 5]
    for r in results:
        assert r.passed, f"gate {r.gate} ({r.name}) failed: {r.detail}"


def test_validate_cli_verb_reports_all_green_json(tmp_path, capsys):
    code = cli_main([
        "validate", "--gates", "--repo-root", str(REPO_ROOT),
        "--corpus-root", str(FIXTURE_ROOT),
        "--workspaces-dir", str(tmp_path / "ontograph-workspaces"), "--json",
    ])
    out = capsys.readouterr().out
    assert code == 0
    result = json.loads(out)  # must parse cleanly -- no leaked --help text from gate 4's own internal check
    assert result["all_green"] is True
    assert len(result["gates"]) == 5


def test_gate_3_re_runs_appendix_a_live_not_just_trusted():
    from ontograph.validate import check_gate_3_deterministic_engine
    result = check_gate_3_deterministic_engine(REPO_ROOT)
    assert result.passed
    assert "passed" in result.detail  # pytest's own summary line, proving a real subprocess ran
