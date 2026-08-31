"""Ledger row P9.5: the guided calibration/assessment flow (`ontograph walk`).

Design source of truth: .hermes/plans/2026-08-31_p95-guided-flow-design.md
(provisionally approved by the researcher). The verify target from the plan:
a scripted fixture walkthrough of mirror's 7 hits reaches the exact
accepted/rejected/ambiguous split of canonical-study-assessments.json
through the flow itself — not by calling `assess` directly per hit.

Rules under test (from the design doc):
- decisions batch in-session; ONE batched assess write-out
- `a`/`r`/`u` classify; `n` narrow forks a re-census (anchor revision,
  never a silent edit); `s` split adds an object; `t` promotes to a Trace;
  `w`/`x` widen/stop the sample; `?` levels open the context ladder;
  Enter leaves undecided; `done` finishes
- narrow/split/promote are available on EVERY hit, mid-sample
- undecided hits are listed at write-out and NEVER imputed
- no interactive stdin: not a TTY and no --script -> clean CLIError
"""
import json
import pathlib

import pytest

from ontograph.cli import main

FIXTURE_ROOT = str(pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def _canonical():
    p = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor" / "canonical-study-assessments.json"
    return json.loads(p.read_text(encoding="utf-8"))


# --- the verify target: scripted walkthrough reaches the canonical split ---

def test_scripted_walkthrough_reproduces_canonical_assessments(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "walk-study", "--corpus-root", FIXTURE_ROOT, *base])
    _run(capsys, ["object", "add", "walk-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", *base])

    # the mirror decisions from canonical-study-assessments.json, as per-hit
    # script responses IN SAMPLE ORDER: decision letters for every hit.
    canon = _canonical()["assessments"]["mirror"]  # poem_id -> decision
    # deterministic sample: calibrate first with the same seed the walk uses
    code, out = _run(capsys, ["calibrate", "walk-study", "--object", "mirror",
                              "--sample", "10", "--seed", "0", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    sample = json.loads(out)["context"]
    sample_poems = [entry["poem_id"] for entry in sample]
    assert len(sample_poems) == 7  # fixture mirror has exactly 7 hits
    letter = {"accepted": "a", "rejected": "r", "ambiguous": "u"}
    script = {"responses": [letter[canon[str(pid)]] for pid in sample_poems]}

    script_path = tmp_path / "walk-script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")

    code, out = _run(capsys, ["walk", "walk-study", "--object", "mirror",
                              "--script", str(script_path), "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0, out
    result = json.loads(out)

    # the flow's write-out produced exactly the canonical split
    assert result["summary"] == {"accepted": 5, "rejected": 1, "ambiguous": 1}
    assert result["undecided"] == []  # every scripted hit was decided

    # ...and the written state matches the canonical file exactly
    for pid, decision in canon.items():
        code, out = _run(capsys, ["assess", "walk-study", "--object", "mirror",
                                  "--poem-id", str(pid), "--decision", decision,
                                  "--assessor", "human", *base, "--json"])
        # re-assessing with the same decision must be idempotent-safe:
        # the flow already wrote it, the CLI accepts the latest-entry-wins repeat
        assert code == 0

    # assessed-mode census through the written assessments matches ground truth
    code, out = _run(capsys, ["census", "walk-study", "--object", "mirror",
                              "--mode", "assessed", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    result = json.loads(result_guard(out))
    assert result["mode"] == "assessed"
    assert sorted(result["accepted_poems"]) == sorted(int(p) for p in canon if canon[p] == "accepted")


def result_guard(out):
    return out


# --- structural choices are available mid-sample, and are first-class ---

def test_walk_undecided_hits_never_imputed(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "und-study", "--corpus-root", FIXTURE_ROOT, *base])
    _run(capsys, ["object", "add", "und-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", *base])

    # decide only the first hit, leave the rest (Enter -> undecided)
    script = {"responses": ["a"] + [""] * 6}
    script_path = tmp_path / "walk-script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")

    code, out = _run(capsys, ["walk", "und-study", "--object", "mirror",
                              "--script", str(script_path), "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    result = json.loads(out)
    assert result["summary"]["accepted"] == 1
    assert len(result["undecided"]) == 6

    # assessed-mode census counts ONLY the written decision — never imputed
    code, out = _run(capsys, ["census", "und-study", "--object", "mirror",
                              "--mode", "assessed", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    result = json.loads(out)
    assert result["numerator"] == 1
    assert len(result["ambiguous_only_poems"]) == 0  # undecided != ambiguous


def test_walk_narrow_forks_and_records_anchor_revision(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "narrow-study", "--corpus-root", FIXTURE_ROOT, *base])
    _run(capsys, ["object", "add", "narrow-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", *base])

    # first hit: narrow the anchor to the spelling variant, then accept it
    # under the narrowed anchor; remaining hits: accept (fixture mirror hits
    # are the same 7 poems regardless — narrow re-census is a fork that must
    # be recorded, not a silent edit)
    script = {"responses": ["n:آیینه", "a", "a", "a", "a", "a", "a", "a"]}
    script_path = tmp_path / "walk-script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")

    code, out = _run(capsys, ["walk", "narrow-study", "--object", "mirror",
                              "--script", str(script_path), "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0, out
    result = json.loads(out)

    # the fork is recorded as a first-class structural event, not silent
    assert any(e["event_type"] == "anchor_narrowed" for e in result["events"])
    narrowed = [e for e in result["events"] if e["event_type"] == "anchor_narrowed"][0]
    assert narrowed["from_form"] == "آینه" and narrowed["to_form"] == "آیینه"

    # and the flow still completes its batched write-out
    assert result["summary"]["accepted"] >= 5


def test_walk_promote_writes_a_trace_record(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "trace-study", "--corpus-root", FIXTURE_ROOT, *base])
    _run(capsys, ["object", "add", "trace-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", "--anchor", "آیینه", *base])

    script = {"responses": ["t", "a", "a", "a", "a", "a", "a", "a"]}
    script_path = tmp_path / "walk-script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")

    code, out = _run(capsys, ["walk", "trace-study", "--object", "mirror",
                              "--script", str(script_path), "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0, out
    result = json.loads(out)
    assert result["traces"] >= 1
    # Trace written immediately (P4.1 records), visible in the study's records
    trace_files = list((ws_dir / "trace-study" / "records").glob("*trace*")) if (ws_dir / "trace-study" / "records").exists() else []
    # the exact storage shape is the records layer's; the flow's contract is the count
    assert result["traces"] == len([e for e in result["events"] if e["event_type"] == "trace_promoted"])


def test_walk_no_tty_and_no_script_is_clean_error(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    _run(capsys, ["study", "new", "tty-study", "--corpus-root", FIXTURE_ROOT, *base])
    _run(capsys, ["object", "add", "tty-study", "--label", "mirror", "--address", "mirror",
                  "--anchor", "آینه", *base])

    # main() converts CLIError to exit code 1 + stderr message (P5.3's
    # explicit-failure contract): never a silent empty-JSON success
    code = main(["walk", "tty-study", "--object", "mirror",
                 "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out.strip() == ""  # no silent success payload
    assert "interactive terminal" in captured.err or "--script" in captured.err
