"""G19 (L3.8): `inquire --refresh` no longer writes a SQLite index
directly into the pinned corpus root -- routes through index_cache like
every other verb.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

FIXTURE_ROOT_SRC = Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_refresh_creates_no_file_under_corpus_root(tmp_path: Path, capsys) -> None:
    # copy the fixture corpus so this test can inspect it in isolation
    # without polluting (or being polluted by) the shared fixtures/ dir
    corpus_root = tmp_path / "corpus"
    shutil.copytree(FIXTURE_ROOT_SRC, corpus_root)
    before = sorted(p.name for p in corpus_root.iterdir())

    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g19"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", str(corpus_root), "--workspaces-dir", ws_dir])[0] == 0

    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps([{
        "kind": "lexical-anchor", "form": "آینه", "proposer": "mz",
        "proposer_type": "human", "rationale": "test",
    }]), encoding="utf-8")
    code, out, err = _run(capsys, [
        "inquire", study_id, "--hunch", "mirror", "--actor", "mz",
        "--file", str(proposal), "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    catalog_id = json.loads(out)["catalog_id"]

    code, out, err = _run(capsys, [
        "inquire", study_id, "--refresh", catalog_id, "--actor", "mz",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out

    after = sorted(p.name for p in corpus_root.iterdir())
    assert after == before  # nothing new written into the pinned corpus root
    assert not (corpus_root / "ontograph-support-idx.sqlite").exists()


def test_refresh_still_computes_real_support(tmp_path: Path, capsys) -> None:
    """Not just "no stray file" -- the refresh must still actually work."""
    corpus_root = tmp_path / "corpus"
    shutil.copytree(FIXTURE_ROOT_SRC, corpus_root)
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g19-works"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", str(corpus_root), "--workspaces-dir", ws_dir])[0] == 0

    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps([{
        "kind": "lexical-anchor", "form": "آینه", "proposer": "mz",
        "proposer_type": "human", "rationale": "test",
    }]), encoding="utf-8")
    code, out, err = _run(capsys, [
        "inquire", study_id, "--hunch", "mirror", "--actor", "mz",
        "--file", str(proposal), "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    catalog_id = json.loads(out)["catalog_id"]

    code, out, err = _run(capsys, [
        "inquire", study_id, "--refresh", catalog_id, "--actor", "mz",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["verified"] == 1  # آینه is really in the mirror fixture
