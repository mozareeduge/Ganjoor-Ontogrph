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


# --- assess flow + assessed-full census (T06: the per-hit ledger is the
# only coverage source; poem-keyed rows are legacy v0.1 compatibility and
# provide ZERO assessed-full coverage -- execution-spec lock T04-T06) ---

def _walk_canonical(capsys, tmp_path, study_id, object_address, ws_dir):
    """Walk one object with the canonical fixture decisions as per-hit
    walk responses (coverage enters ONLY through the per-hit ledger)."""
    code, out = _run(capsys, ["calibrate", study_id, "--object", object_address,
                              "--sample", "50", "--seed", "0",
                              "--corpus-root", FIXTURE_ROOT,
                              "--workspaces-dir", str(ws_dir), "--json"])
    assert code == 0
    sample_poems = [e["poem_id"] for e in json.loads(out)["context"]]
    canon = json.loads(
        (pathlib.Path(FIXTURE_ROOT) / "canonical-study-assessments.json").read_text(encoding="utf-8")
    )["assessments"][object_address]
    letter = {"accepted": "a", "rejected": "r", "ambiguous": "u"}
    sp = tmp_path / f"{study_id}-{object_address}-walk.json"
    sp.write_text(json.dumps({"responses": [letter[canon[str(p)]] for p in sample_poems]}), encoding="utf-8")
    code, out = _run(capsys, ["walk", study_id, "--object", object_address,
                              "--sample", "50", "--script", str(sp),
                              "--corpus-root", FIXTURE_ROOT,
                              "--workspaces-dir", str(ws_dir), "--json"])
    assert code == 0, out
    return json.loads(out)


def test_assess_flow_and_assessed_full_matches_fixture_ground_truth(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    common = ["--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "mirror-study", "--workspaces-dir", str(ws_dir)])
    _run(capsys, ["field", "build", "mirror-study", *common])
    _run(capsys, ["object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir)])
    _run(capsys, ["object", "add", "mirror-study", "--label", "rust", "--address", "rust",
                  "--anchor", "زنگار", "--workspaces-dir", str(ws_dir)])

    _walk_canonical(capsys, tmp_path, "mirror-study", "mirror", ws_dir)
    _walk_canonical(capsys, tmp_path, "mirror-study", "rust", ws_dir)

    # census --mode assessed-full must match the canonical split exactly
    code, out = _run(capsys, ["census", "mirror-study", "--object", "mirror", "--mode", "assessed-full", *common, "--json"])
    assert code == 0
    result = json.loads(out)
    assert result["mode"] == "assessed-full"
    assert result["numerator"] == 5 and result["denominator"] == 27
    assert result["ambiguous_only_count"] == 1
    assert result["accepted_poems"] == [9101, 9102, 9103, 9104, 9201]

    # legacy poem-keyed rows still write (v0.1 compatibility verb) but
    # never change assessed-full coverage
    code, out = _run(capsys, ["assess", "mirror-study", "--object", "mirror",
                              "--poem-id", "9105", "--decision", "accepted",
                              "--workspaces-dir", str(ws_dir), "--json"])
    assert code == 0
    assert json.loads(out)["decision"] == "accepted"
    code, out = _run(capsys, ["census", "mirror-study", "--object", "mirror", "--mode", "assessed-full", *common, "--json"])
    assert code == 0
    assert json.loads(out)["numerator"] == 5  # unchanged

    # companions --mode assessed-full keeps the Finding-1 divergence: 3
    # poems, not the anchor-level 4 (poem 9106's mirror hit is rejected)
    code, out = _run(capsys, [
        "companions", "mirror-study", "--object", "mirror", "--with", "rust",
        "--mode", "assessed-full", *common, "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["mode"] == "assessed-full"
    assert result["poem_scale"] == [9101, 9102, 9201]

    # ablate --mode assessed-full: relation-scale retention (3 poems -> 1,
    # 2 couplets -> 1), the same ground truth as P3.8's assessed level
    code, out = _run(capsys, [
        "ablate", "mirror-study", "--remove", "poet:sample1", "--rerun", "relation:mirror-rust",
        "--mode", "assessed-full", *common, "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["mode"] == "assessed-full"
    assert result["original_poem_scale"] == 3 and result["remaining_poem_scale"] == 1
    assert result["original_couplet_scale"] == 2 and result["remaining_couplet_scale"] == 1


def test_mode_assessed_full_without_hit_rows_refuses_not_falls_back(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    common = ["--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir)]
    _run(capsys, ["study", "new", "mirror-study", "--workspaces-dir", str(ws_dir)])
    _run(capsys, ["field", "build", "mirror-study", *common])
    _run(capsys, ["object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir)])

    code = main(["census", "mirror-study", "--object", "mirror", "--mode", "assessed-full", *common])
    captured = capsys.readouterr()
    assert code != 0
    assert "0/7" in captured.err          # coverage counts, never a silent zero
    assert "assessed-full" in captured.err
    assert captured.out == ""


# --- P9.1: a study that stored a corpus root lets later verbs omit
# --corpus-root; explicit flag still wins; neither → clean CLIError ---

def test_p91_stored_corpus_root_lets_verbs_omit_the_flag(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"

    # `study new --corpus-root` persists the root into study.yml
    code, out = _run(capsys, [
        "study", "new", "mirror-study", "--corpus-root", FIXTURE_ROOT,
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["corpus_root"] == FIXTURE_ROOT

    _run(capsys, ["object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir)])

    # census with NO --corpus-root must succeed and match the explicit-flag result
    code, out = _run(capsys, [
        "census", "mirror-study", "--object", "mirror",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["hit_count"] == 7  # same P1.5 anchor-level ground truth as the explicit-flag run

    # field build (also rewired onto the resolver) behaves the same way
    code, out = _run(capsys, [
        "field", "build", "mirror-study", "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["poem_count"] == 27

    # assess never touches the corpus, so it must run with neither a flag
    # nor a stored root (the resolver is simply not in its path)
    code, out = _run(capsys, [
        "assess", "mirror-study", "--object", "mirror", "--poem-id", "9101",
        "--decision", "accepted", "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["decision"] == "accepted"


def test_p91_explicit_corpus_root_overrides_the_stored_value(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    bogus = str(tmp_path / "not-a-corpus")

    # store a WRONG root, then prove the explicit flag wins
    code, _ = _run(capsys, [
        "study", "new", "mirror-study", "--corpus-root", bogus,
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    _run(capsys, ["object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir)])

    code, out = _run(capsys, [
        "census", "mirror-study", "--object", "mirror", "--corpus-root", FIXTURE_ROOT,
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["hit_count"] == 7  # scanned the explicit root, not the stored bogus one


def test_p91_no_stored_root_and_no_flag_is_a_clean_clierror(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    _run(capsys, ["study", "new", "mirror-study", "--workspaces-dir", str(ws_dir)])
    _run(capsys, ["object", "add", "mirror-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--workspaces-dir", str(ws_dir)])

    code = main(["census", "mirror-study", "--object", "mirror",
                 "--workspaces-dir", str(ws_dir), "--json"])
    captured = capsys.readouterr()
    assert code == 1  # CLIError, not an argparse usage error or a traceback
    assert "no --corpus-root" in captured.err
    assert captured.out == ""


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


# --- P9.4: field/scope.json is a real filter other verbs respect ---
# Regression: a field scoped to sample1 must make an object that exists
# corpus-wide (garden/باغ — present ONLY in sample2's poem 9202) return
# 0 hits inside the scoped study, while an unscoped study still sees it.

def test_p94_scope_filters_census_to_the_stored_field(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"

    # P9.1 flow stays intact: stored root, no explicit flags below
    code, _ = _run(capsys, [
        "study", "new", "garden-study", "--corpus-root", FIXTURE_ROOT,
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0

    code, out = _run(capsys, [
        "field", "build", "garden-study", "--poet", "sample1",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    assert json.loads(out)["poem_count"] == 7  # sample1's 7 poems

    scope = json.loads(
        (ws_dir / "garden-study" / "field" / "scope.json").read_text(encoding="utf-8")
    )
    assert scope["kind"] == "poet" and scope["poet_slug"] == "sample1"

    code, _ = _run(capsys, [
        "object", "add", "garden-study", "--label", "garden", "--address", "garden",
        "--anchor", "باغ", "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0

    # garden exists only in sample2's poems — outside this study's field
    code, out = _run(capsys, [
        "census", "garden-study", "--object", "garden",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["hit_count"] == 0 and result["poem_count"] == 0 and result["poems"] == []

    # ...but the object is real corpus-wide: an unscoped study sees it
    _run(capsys, ["study", "new", "unscoped", "--corpus-root", FIXTURE_ROOT,
                  "--workspaces-dir", str(ws_dir)])
    _run(capsys, ["object", "add", "unscoped", "--label", "garden", "--address", "garden",
                  "--anchor", "باغ", "--workspaces-dir", str(ws_dir)])
    code, out = _run(capsys, [
        "census", "unscoped", "--object", "garden",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result = json.loads(out)
    assert result["hit_count"] > 0 and 9202 in result["poems"]

    # an all-poems scope (field build with no --poet) changes nothing
    _run(capsys, ["field", "build", "unscoped", "--corpus-root", FIXTURE_ROOT,
                  "--workspaces-dir", str(ws_dir)])
    code, out = _run(capsys, [
        "census", "unscoped", "--object", "garden",
        "--workspaces-dir", str(ws_dir), "--json",
    ])
    assert code == 0
    result_all = json.loads(out)
    assert result_all == result  # identical numbers, scope=all is a no-op
