"""G18 (L3.7): `field build --json` no longer inlines the full poem_ids
list by default -- a scope_hash + count instead, opt-in --include-poem-ids
for the rare caller that needs the full list.
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


def test_field_build_default_omits_poem_ids_and_stays_small(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g18"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out, err = _run(capsys, ["field", "build", study_id, "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert "poem_ids" not in result
    assert result["poem_count"] > 0
    assert result["scope_hash"].startswith("sh1-")
    assert len(out) < 2000  # was ~1.6MB-scale on the real corpus; tiny on this fixture too, but the KEY is what mattered


def test_field_build_include_poem_ids_reproduces_full_list(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g18-full"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out, err = _run(capsys, ["field", "build", study_id, "--include-poem-ids", "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert "poem_ids" in result
    assert len(result["poem_ids"]) == result["poem_count"]


def test_scope_hash_is_stable_for_the_same_scope(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g18-stable"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out1, err = _run(capsys, ["field", "build", study_id, "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out1
    code, out2, err = _run(capsys, ["field", "build", study_id, "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out2
    assert json.loads(out1)["scope_hash"] == json.loads(out2)["scope_hash"]
