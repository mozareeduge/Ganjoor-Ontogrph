"""Gap G15: walk/assess write REAL OccurrencePosition rows via --as,
not just the F06 legacy bridge.
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


def _seed(capsys, tmp_path: Path, study_id: str):
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    assert _run(capsys, [
        "object", "add", study_id, "--address", "mirror", "--label", "Mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", ws_dir,
    ])[0] == 0
    return ws_dir, base


def test_walk_as_registered_assessor_writes_real_position(tmp_path: Path, capsys) -> None:
    study_id = "g15-walk"
    ws_dir, base = _seed(capsys, tmp_path, study_id)
    ws = Path(ws_dir) / study_id

    assert _run(capsys, [
        "assessor", "add", study_id, "--id", "as-mz", "--label", "Mohammad Zare",
        "--type", "human", "--apparatus", "researcher, full context",
        "--independence-class", "human-mz", "--workspaces-dir", ws_dir,
    ])[0] == 0

    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    code, out, err = _run(capsys, [
        "walk", study_id, "--object", "mirror", "--script", str(sp),
        "--as", "as-mz", *base, "--json",
    ])
    assert code == 0, err or out

    from ontograph.positions import read_positions

    real = read_positions(ws)
    assert len(real) == 7
    assert all(p.assessor_object_id == "as-mz" for p in real)
    assert all(p.stance == "occurs" for p in real)  # accepted -> occurs
    assert all(not p.id.startswith("bridge-") for p in real)  # genuinely real, not synthesized


def test_walk_as_unregistered_assessor_refuses(tmp_path: Path, capsys) -> None:
    study_id = "g15-refuse"
    ws_dir, base = _seed(capsys, tmp_path, study_id)
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    code, out, err = _run(capsys, [
        "walk", study_id, "--object", "mirror", "--script", str(sp),
        "--as", "as-does-not-exist", *base, "--json",
    ])
    assert code == 1
    assert "not registered" in err


def test_walk_without_as_reproduces_old_behavior(tmp_path: Path, capsys) -> None:
    """Omitting --as: zero real positions written, old ledger only
    (bridged live, as it always has been)."""
    study_id = "g15-omit"
    ws_dir, base = _seed(capsys, tmp_path, study_id)
    ws = Path(ws_dir) / study_id
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    code, out, err = _run(capsys, [
        "walk", study_id, "--object", "mirror", "--script", str(sp), *base, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["summary"]["accepted"] == 7  # unchanged fixture arithmetic

    from ontograph.positions import read_positions

    assert read_positions(ws) == []  # no real positions -- old ledger only


def test_walk_real_position_visible_to_positioned_full_without_bridge(tmp_path: Path, capsys) -> None:
    """--as writes are additive, not a replacement (documented in
    walk.py): the old ledger write still happens under whatever
    --assessor says (default "human"), so census sees BOTH the real
    "as-mz" position AND a legacy:human:human bridge entry for the same
    hits -- two distinct assessor identities the tool has no way to
    consider "the same fact" unless they're literally the same id.
    A researcher who wants exactly one identity to appear should pass a
    matching --assessor value, or (once it exists) a future --no-legacy-write
    flag; not attempted here."""
    study_id = "g15-census"
    ws_dir, base = _seed(capsys, tmp_path, study_id)
    ws = Path(ws_dir) / study_id
    assert _run(capsys, [
        "assessor", "add", study_id, "--id", "as-mz", "--label", "mz", "--type", "human",
        "--apparatus", "researcher", "--independence-class", "human-mz", "--workspaces-dir", ws_dir,
    ])[0] == 0
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    assert _run(capsys, [
        "walk", study_id, "--object", "mirror", "--script", str(sp),
        "--as", "as-mz", *base, "--json",
    ])[0] == 0
    assert _run(capsys, ["policy", "declare", study_id, "--kind", "concordance", "--workspaces-dir", ws_dir, "--json"])[0] == 0

    code, out, err = _run(capsys, ["census", study_id, "--object", "mirror", "--mode", "positioned-full", *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    by_assessor = result["positioning"]["by_assessor"]
    assert by_assessor["as-mz"] == 7  # the REAL id is present and correctly counted
    assert "legacy:human:human" in by_assessor  # the old ledger's default identity, also present (additive)


def test_assess_hit_as_registered_assessor_writes_real_position(tmp_path: Path, capsys) -> None:
    study_id = "g15-assess"
    ws_dir, base = _seed(capsys, tmp_path, study_id)
    ws = Path(ws_dir) / study_id
    assert _run(capsys, [
        "assessor", "add", study_id, "--id", "as-rule", "--label", "a rule", "--type", "rule",
        "--apparatus", "rule id=x version=1", "--independence-class", "apparatus-x", "--workspaces-dir", ws_dir,
    ])[0] == 0

    from ontograph.cli import _anchors_for
    from ontograph.index_cache import census_from_index, get_or_build_index, records_from_index

    conn, _m, _c = get_or_build_index(FIXTURE_ROOT)
    records = records_from_index(conn)
    hits = census_from_index(conn, records, _anchors_for(ws, "mirror"))
    conn.close()
    hit_id = hits[0].id

    # `assess`'s parser uses the `common` parent, not `with_corpus` -- it
    # never takes --corpus-root (same as `record add`, see F11's tests)
    code, out, err = _run(capsys, [
        "assess", study_id, "--object", "mirror", "--hit-id", hit_id,
        "--decision", "rejected", "--as", "as-rule",
        "--workspaces-dir", ws_dir, "--json",
    ])
    assert code == 0, err or out
    assert json.loads(out)["position_written_for"] == "as-rule"

    from ontograph.positions import read_positions

    real = read_positions(ws)
    assert len(real) == 1
    assert real[0].assessor_object_id == "as-rule"
    assert real[0].stance == "does-not-occur"  # rejected -> does-not-occur
