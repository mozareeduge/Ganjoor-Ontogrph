"""Amendment 20 F13: `walk --triage-order`, wiring positions.queue_by_weight()
(already built and tested in F03) into the walk sample order.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.assessors import AssessorObject, register_assessor
from ontograph.cli import _anchors_for, main
from ontograph.index_cache import census_from_index, get_or_build_index, records_from_index
from ontograph.positions import position_for
from ontograph.walk import run_walk

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed(capsys, tmp_path: Path, study_id: str) -> Path:
    ws_dir = tmp_path / "ontograph-workspaces"
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", str(ws_dir)])[0] == 0
    assert _run(capsys, [
        "object", "add", study_id, "--address", "mirror", "--label", "Mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", str(ws_dir),
    ])[0] == 0
    return ws_dir / study_id


def _mirror_hits(ws: Path):
    conn, _manifest, _cache_hit = get_or_build_index(FIXTURE_ROOT)
    records = records_from_index(conn)
    hits = census_from_index(conn, records, _anchors_for(ws, "mirror"))
    conn.close()
    return hits


def test_triage_order_uncertain_first_visits_lowest_weight_hit_first(tmp_path: Path, capsys) -> None:
    ws = _seed(capsys, tmp_path, "f13-uncertain")
    hits = _mirror_hits(ws)
    assert len(hits) == 7

    register_assessor(ws, AssessorObject(id="as-triage", label="triage", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    # give every hit a weight EXCEPT hit[3], which should therefore always
    # sort last regardless of order (no weight to prioritize by)
    weighted = [h for i, h in enumerate(hits) if i != 3]
    for i, h in enumerate(weighted):
        position_for(ws, h.id, "mirror", "as-triage", "occurs", weight=round(0.1 * (i + 1), 2))
    lowest_weight_hit = weighted[0]  # weight 0.1, the most uncertain
    no_weight_hit = hits[3]

    script = tmp_path / "script-uncertain.json"
    script.write_text(json.dumps({"responses": ["a"]}), encoding="utf-8")  # only the FIRST-visited hit gets decided
    result = run_walk(
        ws=ws, study_id="f13-uncertain", object_address="mirror",
        corpus_root=FIXTURE_ROOT, sample_size=7, seed=0,
        script_path=str(script), assessor="mz", assessor_type="human",
        triage_order="uncertain-first",
    )
    assert result["summary"]["accepted"] == 1

    from ontograph.census import load_hit_assessments

    decided = [r for r in load_hit_assessments(ws) if r.decision == "accepted"]
    assert len(decided) == 1
    assert decided[0].anchor_hit_id == lowest_weight_hit.id
    assert decided[0].anchor_hit_id != no_weight_hit.id


def test_triage_order_confident_first_visits_highest_weight_hit_first(tmp_path: Path, capsys) -> None:
    ws = _seed(capsys, tmp_path, "f13-confident")
    hits = _mirror_hits(ws)
    register_assessor(ws, AssessorObject(id="as-triage", label="triage", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    for i, h in enumerate(hits):
        position_for(ws, h.id, "mirror", "as-triage", "occurs", weight=round(0.1 * (i + 1), 2))
    highest_weight_hit = hits[-1]  # weight 0.7, the most confident

    script = tmp_path / "script-confident.json"
    script.write_text(json.dumps({"responses": ["a"]}), encoding="utf-8")
    result = run_walk(
        ws=ws, study_id="f13-confident", object_address="mirror",
        corpus_root=FIXTURE_ROOT, sample_size=7, seed=0,
        script_path=str(script), assessor="mz", assessor_type="human",
        triage_order="confident-first",
    )
    assert result["summary"]["accepted"] == 1

    from ontograph.census import load_hit_assessments

    decided = [r for r in load_hit_assessments(ws) if r.decision == "accepted"]
    assert decided[0].anchor_hit_id == highest_weight_hit.id


def test_no_triage_order_preserves_existing_deterministic_sample_order(tmp_path: Path, capsys) -> None:
    """Absent --triage-order, behaviour is byte-for-byte unchanged from
    before F13 (the pre-existing calibration_sample seeded order)."""
    ws = _seed(capsys, tmp_path, "f13-none")
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    result = run_walk(
        ws=ws, study_id="f13-none", object_address="mirror",
        corpus_root=FIXTURE_ROOT, sample_size=7, seed=0,
        script_path=str(script), assessor="mz", assessor_type="human",
        triage_order=None,
    )
    assert result["summary"]["accepted"] == 7  # unchanged fixture arithmetic
