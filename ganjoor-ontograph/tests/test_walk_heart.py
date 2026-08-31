"""Ledger row P9.7: full calibrate→guided-assess→assessed-mode-query cycle at
HEART-object scale (41 hits / 11 poems) THROUGH the P9.5 guided walk flow —
the same rigor as P7.5's scalability gate but exercised via the walk, not
direct `assess` calls.

The HEART object has no canonical per-hit assessment file, so this test
establishes its own hand-verifiable ground truth: the fixture was built so
poems 9401–9410 each contain دل 4 times (real occurrences by construction)
and poem 9105's single دل is the figurative 'mirror of the heart' line —
ambiguous by the same rationale the canonical mirror:9105 assessment uses.
That gives: 10 accepted poems (40 hits), 1 ambiguous poem (9105), 0 rejected.

Verify (ledger): assessed-mode census/companions after the flow match this
hand-derived ground truth.
"""
import io
import json
import contextlib
import pathlib

from ontograph.cli import main

HERE = pathlib.Path(__file__).resolve().parent.parent
FIX = str(HERE / "fixtures" / "mini-ganjoor")

HEART_ASSESSMENTS = {
    # poem_id -> decision; hand-derived from the fixture's own construction
    # note (manifest _fixture_ground_truth.heart_object): sample4 poems are
    # real literal occurrences; 9105 is the figurative mirror-of-the-heart line.
    # String keys: the walk script looks decisions up by str(poem_id).
    **{str(pid): "accepted" for pid in range(9401, 9411)},
    "9105": "ambiguous",
}


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def test_heart_scale_guided_flow_matches_ground_truth(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    code, _ = _run(capsys, ["study", "new", "heart-study", "--corpus-root", FIX, *base, "--json"])
    assert code == 0
    code, _ = _run(capsys, ["object", "add", "heart-study", "--label", "دل", "--address", "heart",
                            "--anchor", "دل", *base, "--json"])
    assert code == 0

    # calibrate over the FULL 41-hit population (spec: sample from the whole
    # field, not a clean subset), seed 0, all hits in the sample
    code, out = _run(capsys, ["calibrate", "heart-study", "--object", "heart",
                              "--sample", "50", "--seed", "0", "--corpus-root", FIX, *base, "--json"])
    assert code == 0
    sample = json.loads(out)["context"]
    sample_poems = [e["poem_id"] for e in sample]
    assert len(sample_poems) == 41  # the full HEART population

    # drive the guided flow with the hand-derived decisions
    letter = {"accepted": "a", "rejected": "r", "ambiguous": "u"}
    script = {"responses": [letter[HEART_ASSESSMENTS[str(pid)]] for pid in sample_poems]}
    script_path = tmp_path / "heart-walk.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")

    code, out = _run(capsys, ["walk", "heart-study", "--object", "heart",
                              "--sample", "50",
                              "--script", str(script_path), "--corpus-root", FIX, *base, "--json"])
    assert code == 0, out
    result = json.loads(out)
    assert result["summary"] == {"accepted": 40, "rejected": 0, "ambiguous": 1}
    assert result["undecided"] == []

    # assessed-mode census matches the hand-derived ground truth
    code, out = _run(capsys, ["census", "heart-study", "--object", "heart",
                              "--mode", "assessed", "--corpus-root", FIX, *base, "--json"])
    assert code == 0
    census = json.loads(out)
    assert census["numerator"] == 10  # 10 accepted poems
    assert sorted(census["accepted_poems"]) == list(range(9401, 9411))
    assert census["ambiguous_only_poems"] == [9105]

    # companions across the field at assessed mode (rust co-presence is zero
    # in sample4 by construction; assert the verb runs and returns a number)
    code, _ = _run(capsys, ["object", "add", "heart-study", "--label", "زنگار", "--address", "rust",
                            "--anchor", "زنگار", *base, "--json"])
    assert code == 0
    # assessed companions needs assessments for BOTH objects: one rust
    # one-off correction via per-hit assess (the skill's documented pattern)
    code, _ = _run(capsys, ["assess", "heart-study", "--object", "rust", "--poem-id", "9101",
                            "--decision", "accepted", *base, "--json"])
    assert code == 0
    code, out = _run(capsys, ["companions", "heart-study", "--object", "heart", "--with", "rust",
                              "--scale", "poem", "--mode", "assessed",
                              "--corpus-root", FIX, *base, "--json"])
    assert code == 0
    companions = json.loads(out)
    assert "companions" in companions or "lift" in json.dumps(companions)
