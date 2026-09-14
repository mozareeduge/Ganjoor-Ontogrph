"""G21 (L3.4/V201): field build --poet (repeatable, union) and
--exclude-poet (repeatable, difference) -- the CLI surface for a scope
algebra field.py's ScopeSpec already implements and tests.

The exact case that forced an ungoverned workaround in the Esfandyar
study this session: "everything except poet X."
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _all_poem_count(capsys, ws_dir: str, study_id: str) -> int:
    code, out, err = _run(capsys, ["field", "build", study_id, "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    return json.loads(out)["poem_count"]


def test_single_poet_still_works_unchanged(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g21-single"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    code, out, err = _run(capsys, [
        "field", "build", study_id, "--poet", "sample1", "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    assert json.loads(out)["poem_count"] > 0


def test_repeated_poet_unions(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g21-union"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out1, err = _run(capsys, ["field", "build", study_id, "--poet", "sample1", "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out1
    n1 = json.loads(out1)["poem_count"]

    code, out2, err = _run(capsys, [
        "field", "build", study_id, "--poet", "sample1", "--poet", "sample2",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out2
    n_union = json.loads(out2)["poem_count"]
    assert n_union > n1  # sample2 added real poems


def test_exclude_poet_is_the_ferdowsi_case(tmp_path: Path, capsys) -> None:
    """No --poet at all, one --exclude-poet: 'everything except X' in one
    governed call -- the exact case that blocked the Esfandyar study."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g21-exclude"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    assert _run(capsys, ["study", "new", "g21-exclude-total", "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    total = _all_poem_count(capsys, ws_dir, "g21-exclude-total")

    code, out, err = _run(capsys, [
        "field", "build", study_id, "--exclude-poet", "sample1",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    excluded_count = json.loads(out)["poem_count"]
    assert excluded_count < total  # sample1's poems are genuinely gone
    assert excluded_count > 0  # but the rest of the corpus remains

    # governed: the scope is real and persisted, not an ungoverned workaround
    scope = json.loads((Path(ws_dir) / study_id / "field" / "scope.json").read_text(encoding="utf-8"))
    assert scope["kind"] == "difference"


def test_exclude_multiple_poets(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g21-exclude-multi"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    assert _run(capsys, ["study", "new", "g21-exclude-multi-total", "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    total = _all_poem_count(capsys, ws_dir, "g21-exclude-multi-total")

    code, out, err = _run(capsys, [
        "field", "build", study_id, "--exclude-poet", "sample1", "--exclude-poet", "sample2",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    n = json.loads(out)["poem_count"]
    assert 0 < n < total


def test_poet_and_exclude_poet_combined(tmp_path: Path, capsys) -> None:
    """--poet a --poet b --exclude-poet b == just 'a'."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g21-combined"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    assert _run(capsys, ["study", "new", "g21-combined-solo", "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out_solo, err = _run(capsys, ["field", "build", "g21-combined-solo", "--poet", "sample1", "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out_solo
    n_solo = json.loads(out_solo)["poem_count"]

    code, out, err = _run(capsys, [
        "field", "build", study_id, "--poet", "sample1", "--poet", "sample2",
        "--exclude-poet", "sample2", "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    assert json.loads(out)["poem_count"] == n_solo
