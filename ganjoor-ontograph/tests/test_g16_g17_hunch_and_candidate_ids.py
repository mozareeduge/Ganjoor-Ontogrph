"""G16 (L3.6): needs_vocabulary computed after --file candidates merge.
G17 (L3.5): candidate ids are a stable content hash, not per-process
randomized abs(hash()).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ontograph.inquiry_parse import stable_candidate_id

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_needs_vocabulary_false_when_file_supplies_persian_form(tmp_path: Path, capsys) -> None:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g16"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps([{
        "kind": "lexical-anchor", "form": "آینه", "proposer": "mz",
        "proposer_type": "human", "rationale": "supplied directly",
    }]), encoding="utf-8")

    code, out, err = _run(capsys, [
        "inquire", study_id, "--hunch", "Where does the mirror recur in this corpus?",
        "--actor", "mz", "--file", str(proposal), "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["needs_vocabulary"] is False  # was True before G16 -- the hunch text alone is English
    assert "supply attributed" not in result["next_command"]


def test_needs_vocabulary_true_with_no_persian_forms_at_all(tmp_path: Path, capsys) -> None:
    """The flag still fires correctly for the case it exists to catch."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g16-true"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0

    code, out, err = _run(capsys, [
        "inquire", study_id, "--hunch", "Where does the mirror recur in this corpus?",
        "--actor", "mz", "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["needs_vocabulary"] is True


def test_stable_candidate_id_is_a_deterministic_content_hash() -> None:
    """Pinned against a manual computation -- proves this is sha256-derived,
    not Python's process-randomized hash() builtin (which produced three
    different values for the same string across three separate
    `python -c` invocations when this was found)."""
    expected = "cand-" + hashlib.sha256("lexical-anchor\x00آینه\x00mz".encode("utf-8")).hexdigest()[:24]
    assert stable_candidate_id("lexical-anchor", "آینه", "mz") == expected
    # deterministic: calling it again (simulating "a second process") agrees
    assert stable_candidate_id("lexical-anchor", "آینه", "mz") == expected


def test_stable_candidate_id_varies_with_each_input() -> None:
    a = stable_candidate_id("lexical-anchor", "آینه", "mz")
    b = stable_candidate_id("lexical-anchor", "آینه", "someone-else")
    c = stable_candidate_id("lexical-anchor", "آیینه", "mz")
    assert len({a, b, c}) == 3


def test_cli_persian_form_candidate_id_is_reproducible_across_runs(tmp_path: Path, capsys) -> None:
    """The actual regression: a review-decisions file prepared against one
    inquire run must stay usable against a re-run naming the same
    candidate -- requires the id to not depend on process-local hash seed."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "g17-cli"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    code, out, err = _run(capsys, [
        "inquire", study_id, "--hunch", "mirror", "--actor", "mz",
        "--persian-form", "آینه", "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    expected = stable_candidate_id("lexical-anchor", "آینه", "mz")
    assert result["candidates"] == [expected]
