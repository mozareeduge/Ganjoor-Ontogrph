"""Ledger row T06 (CLI-level): mode alias + completeness enforcement.

The unit-level enforcement (census.enforce_mode_completeness,
resolve_mode_alias) is tested in test_t06_mode_completeness.py. These
tests pin the VERB-level contract (spec §6.5, T06 verification row:
"partial-full refusal; alias warning") against a REAL workspace built
through the actual CLI flow (study new -> object add -> scripted walk)
-- no monkeypatching, because the governed route reads the per-hit
ledger from disk (corpus/hit-assessments.jsonl):

1. `census --mode assessed-full` on a partially-assessed object must
   FAIL (exit != 0) with coverage counts and legal alternatives --
   never silently report partial review as prevalence.
2. The alias `--mode assessed` resolves to canonical `assessed-full`
   with a stderr warning; full coverage then computes normally.
3. `census --mode anchor` is unaffected by any of this.
4. Per-hit `assess --hit-id` supersession updates the active decision
   (and can never create coverage out of nothing).
5. Legacy poem-keyed rows (`assess --poem-id`) provide ZERO
   assessed-full coverage (execution-spec lock T04-T06).
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.cli import main

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")

# The fixture's mirror object has exactly 7 hits; walk samples all of
# them (seed 0 default, deterministic order per test_walk.py).
SCRIPT_ALL_ACCEPTED = {"responses": ["a"] * 7}
SCRIPT_PARTIAL = {"responses": ["a", "r", "", "", "", "", ""]}  # 2/7 assessed


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed_study(capsys, tmp_path: Path, study_id: str, script: dict):
    """Real workspace through the real flow; returns (ws_dir, base_argv)."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]
    code, out, err = _run(
        capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT,
                 "--workspaces-dir", ws_dir]
    )
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["object", "add", study_id, "--address", "mirror",
                 "--label", "Mirror", "--anchor", "آینه", "--anchor", "آیینه",
                 "--workspaces-dir", ws_dir]
    )
    assert code == 0, err or out
    script_path = tmp_path / f"{study_id}-script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")
    code, out, err = _run(
        capsys, ["walk", study_id, "--object", "mirror",
                 "--script", str(script_path), *base, "--json"]
    )
    assert code == 0, err or out
    return ws_dir, base


def _hit_ledger(ws_dir: str, study_id: str) -> list[dict]:
    path = Path(ws_dir) / study_id / "corpus" / "hit-assessments.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_census_assessed_full_partial_refusal(tmp_path, capsys) -> None:
    """Partial coverage + assessed-full = refusal with counts/alternatives."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-partial", SCRIPT_PARTIAL)
    code, out, err = _run(
        capsys, ["census", "t06-partial", "--object", "mirror",
                 "--mode", "assessed-full", *base, "--json"]
    )
    assert code != 0, (
        "partial review must be refused, never reported as assessed-full"
    )
    combined = out + err
    assert "assessed-full" in combined
    assert "2/7" in combined          # 2 of 7 eligible hits assessed
    assert "walk" in combined         # legal alternatives are named


def test_census_assessed_alias_resolves_and_warns(tmp_path, capsys) -> None:
    """`--mode assessed` warns on stderr and computes as assessed-full."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-alias", SCRIPT_ALL_ACCEPTED)
    code, out, err = _run(
        capsys, ["census", "t06-alias", "--object", "mirror",
                 "--mode", "assessed", *base, "--json"]
    )
    assert code == 0, err or out
    assert "WARNING" in err and "assessed-full" in err
    result = json.loads(out)
    assert result["mode"] == "assessed-full"   # never "assessed"
    assert result["numerator"] == 7
    assert result["denominator"] == 27
    assert result["accepted_poems"] == [9101, 9102, 9103, 9104, 9105, 9106, 9201]


def test_walk_full_coverage_census_matches_ground_truth(tmp_path, capsys) -> None:
    """walk writes per-hit rows; 100% coverage computes canonical census."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-golden", SCRIPT_ALL_ACCEPTED)
    rows = _hit_ledger(ws_dir, "t06-golden")
    assert len(rows) == 7, "walk must persist one per-hit row per decision"
    assert all(r["decision"] == "accepted" for r in rows)
    code, out, err = _run(
        capsys, ["census", "t06-golden", "--object", "mirror",
                 "--mode", "assessed-full", *base, "--json"]
    )
    assert code == 0, err or out
    result = json.loads(out)
    assert result["mode"] == "assessed-full"
    assert result["numerator"] == 7
    assert result["ambiguous_only_poems"] == []


def test_census_anchor_mode_unaffected(tmp_path, capsys) -> None:
    """Anchor mode never touches the ledger or the gate."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-anchor", SCRIPT_PARTIAL)
    code, out, err = _run(
        capsys, ["census", "t06-anchor", "--object", "mirror",
                 "--mode", "anchor", *base, "--json"]
    )
    assert code == 0, err or out
    result = json.loads(out)
    assert result["mode"] == "anchor"
    assert result["hit_count"] == 7


def test_census_assessed_full_without_any_hit_rows_refuses(tmp_path, capsys) -> None:
    """No walk, no ledger: coverage 0/7, refusal -- never a silent zero."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    code, out, err = _run(
        capsys, ["study", "new", "t06-empty", "--corpus-root", FIXTURE_ROOT,
                 "--workspaces-dir", ws_dir]
    )
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["object", "add", "t06-empty", "--address", "mirror",
                 "--label", "Mirror", "--anchor", "آینه", "--anchor", "آیینه",
                 "--workspaces-dir", ws_dir]
    )
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["census", "t06-empty", "--object", "mirror",
                 "--mode", "assessed-full", "--workspaces-dir", ws_dir,
                 "--corpus-root", FIXTURE_ROOT, "--json"]
    )
    assert code != 0
    assert "0/7" in out + err


def test_assess_hit_id_supersession_updates_active_decision(tmp_path, capsys) -> None:
    """Per-hit assess route chains supersession; coverage never inflates."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-supersede", SCRIPT_PARTIAL)
    rows = _hit_ledger(ws_dir, "t06-supersede")
    assert len(rows) == 2
    hit_id = rows[0]["anchor_hit_id"]
    code, out, err = _run(
        capsys, ["assess", "t06-supersede", "--object", "mirror",
                 "--hit-id", hit_id, "--decision", "rejected",
                 "--rationale", "re-decided", "--workspaces-dir", ws_dir,
                 "--json"]
    )
    assert code == 0, err or out
    result = json.loads(out)
    assert result["superseded"] == rows[0]["id"]
    assert result["ledger"] == "corpus/hit-assessments.jsonl"
    # supersession rewrote an active decision, it did not add coverage:
    # the census must STILL refuse with the same 2/7.
    code, out, err = _run(
        capsys, ["census", "t06-supersede", "--object", "mirror",
                 "--mode", "assessed-full", *base, "--json"]
    )
    assert code != 0
    assert "2/7" in out + err
    # append-only: the superseded row is still on disk
    rows_after = _hit_ledger(ws_dir, "t06-supersede")
    assert any(r["id"] == rows[0]["id"] for r in rows_after)
    assert len(rows_after) == 3


def test_legacy_poem_keyed_rows_provide_zero_coverage(tmp_path, capsys) -> None:
    """Execution-spec lock T04-T06: poem-keyed rows never count toward
    assessed-full coverage (no fanning poem decisions across hits)."""
    ws_dir, base = _seed_study(capsys, tmp_path, "t06-legacy", SCRIPT_PARTIAL)
    code, out, err = _run(
        capsys, ["assess", "t06-legacy", "--object", "mirror",
                 "--poem-id", "9105", "--decision", "accepted",
                 "--assessor", "human", "--workspaces-dir", ws_dir, "--json"]
    )
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["census", "t06-legacy", "--object", "mirror",
                 "--mode", "assessed-full", *base, "--json"]
    )
    assert code != 0, "legacy poem-keyed row must not create coverage"
    assert "2/7" in out + err
