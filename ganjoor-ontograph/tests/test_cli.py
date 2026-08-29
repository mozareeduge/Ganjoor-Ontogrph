"""Tests for ontograph.cli (ledger rows P5.1-P5.3)."""
import json
import pathlib

import pytest

from ontograph.cli import main

FIXTURE_ROOT = str(pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def _base(tmp_path, *extra):
    return ["--workspaces-dir", str(tmp_path / "ontograph-workspaces"), *extra]


# --- P5.1: every verb runs against the fixture, exits 0, well-formed JSON ---

def test_full_verb_sequence_against_fixture(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"

    code, out = _run(capsys, ["study", "new", "mirror-study", "--workspaces-dir", str(ws_dir), "--json"])
    assert code == 0
    result = json.loads(out)
    assert result["study_id"] == "mirror-study"

    code, out = _run(capsys, [
        "field", "build", "mirror-study", "--corpus-root", FIXTURE_ROOT,
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["poem_count"] == 27

    code, out = _run(capsys, [
        "object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["object_address"] == "mirror"

    code, out = _run(capsys, [
        "object", "add", "mirror-study", "--label", "rust", "--address", "rust",
        "--anchor", "زنگار", "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0

    code, out = _run(capsys, [
        "calibrate", "mirror-study", "--object", "mirror", "--sample", "3", "--seed", "1",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["sample_size"] == 3
    assert len(result["context"]) == 3

    code, out = _run(capsys, [
        "census", "mirror-study", "--object", "mirror",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["hit_count"] == 7  # token-aware census, matches P1.5/manifest ground truth

    code, out = _run(capsys, [
        "map", "recurrence", "mirror-study", "--object", "mirror",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["distinct_poems"] == 7  # anchor-level: includes rejected/ambiguous poems 9105, 9106

    code, out = _run(capsys, [
        "companions", "mirror-study", "--object", "mirror", "--with", "rust", "--scale", "couplet",
        "--min-support", "3", "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["poem_scale"] == [9101, 9102, 9106, 9201]  # anchor-level ground truth
    assert result["lift"] is not None  # support=4 meets default min_support=3

    code, out = _run(capsys, [
        "compare", "mirror-study", "--object", "mirror",
        "--field", "poet:sample1", "--field", "poet:sample2",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["incidence_a_field1"] > 0

    code, out = _run(capsys, [
        "ablate", "mirror-study", "--remove", "poet:sample1", "--rerun", "relation:mirror-rust",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["original_poem_scale"] == 4
    assert result["remaining_poem_scale"] == 1  # matches manifest.json anchor-level ablation ground truth

    code, out = _run(capsys, [
        "release", "mirror-study", "--version", "0.1.0",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["tag"] == "v0.1.0"


# --- P5.2: no search/query verbs anywhere in the CLI ---

def test_help_contains_no_search_or_query_verb(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "search" not in out.lower()
    assert "query" not in out.lower()


# --- P5.3: explicit failure modes ---

def test_bad_input_missing_required_flag_exits_nonzero(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["census", "some-study", "--workspaces-dir", str(tmp_path)])  # missing --object, --corpus-root
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert err  # argparse writes its usage/error message to stderr


def test_missing_workspace_exits_nonzero_with_stderr_message(tmp_path, capsys):
    code = main([
        "census", "no-such-study", "--object", "mirror",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(tmp_path / "ontograph-workspaces"),
    ])
    captured = capsys.readouterr()
    assert code != 0
    assert "workspace not found" in captured.err
    assert captured.out == ""  # never a silent empty-JSON success


def test_malformed_field_spec_category_rejected(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    main(["study", "new", "mirror-study", "--workspaces-dir", str(ws_dir)])
    capsys.readouterr()
    code = main([
        "field", "build", "mirror-study", "--category", "ghazal",
        "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir),
    ])
    captured = capsys.readouterr()
    assert code != 0
    assert "category" in captured.err.lower()
    assert captured.out == ""
