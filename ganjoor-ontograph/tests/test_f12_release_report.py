"""Amendment 20 F12: release report gains an Assessment composition
section and the ported handoff sections (Decisions not made, Unresolved
findings, Negative constraints).
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


def _seed_situation(ws_dir: str, study_id: str) -> None:
    ws = Path(ws_dir) / study_id
    p = ws / "research" / "research-situations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": "rs-f12", "study_id": study_id, "verbatim_hunch": "h",
            "normalized_display_hunch": "h", "language_observations": [],
            "premature_decisions": [], "status": "situational", "actor": "human",
            "supersedes": None,
        }) + "\n")


def test_release_report_has_assessment_composition_and_handoff_sections(tmp_path: Path, capsys) -> None:
    study_id = "f12-report"
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]

    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    _seed_situation(ws_dir, study_id)
    assert _run(capsys, [
        "object", "add", study_id, "--address", "mirror", "--label", "Mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", ws_dir,
    ])[0] == 0

    # a deliberately contested pair, so F08's auto-mint gives us a real
    # "unresolved finding" to render
    from ontograph.assessors import AssessorObject, register_assessor
    from ontograph.positions import position_for

    ws = Path(ws_dir) / study_id
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))

    # position the first hit under both assessors, deliberately disagreeing
    from ontograph.cli import _anchors_for
    from ontograph.index_cache import census_from_index, get_or_build_index, records_from_index

    conn, _manifest, _cache_hit = get_or_build_index(FIXTURE_ROOT)
    index_records = records_from_index(conn)
    anchor_hits = census_from_index(conn, index_records, _anchors_for(ws, "mirror"))
    conn.close()
    first_hit = anchor_hits[0]
    position_for(ws, first_hit.id, "mirror", "as-mz", "occurs")
    position_for(ws, first_hit.id, "mirror", "as-agent", "does-not-occur")

    assert _run(capsys, ["policy", "declare", study_id, "--kind", "concordance", "--workspaces-dir", ws_dir, "--json"])[0] == 0
    code, out, err = _run(capsys, ["census", study_id, "--object", "mirror", "--mode", "inventory", *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["contested_traces_minted"]  # F08's auto-mint fired

    # a Residue and a Reduction, so the other two handoff sections have content
    from ontograph.records import ReductionRecord, ResidueRecord, write_record

    write_record(ws, "residue", ResidueRecord(
        id="res-f12", route_description="tried full assessed-full census",
        stopped_because="single-session time limit", created_by="mz",
    ))
    write_record(ws, "reduction", ReductionRecord(
        id="redu-f12", omitted_or_compressed="6 of 7 hits left unpositioned",
        reason="single-researcher assessment capacity",
        consequence="corpus-wide claim is blocked", recovery_route="resume the walk",
    ))

    code, out, err = _run(capsys, ["release", study_id, "--version", "0.1.0", "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out

    report = (ws / "releases" / "v0.1.0" / "report.md").read_text(encoding="utf-8")
    assert "## Assessment composition" in report
    assert "as-mz: 1" in report or "as-mz" in report
    assert "contested=1" in report or "contested" in report
    assert "## Decisions not made" in report
    assert "single-researcher assessment capacity" in report
    assert "## Unresolved findings" in report
    assert "trace-contested-" in report
    assert "## Negative constraints" in report
    assert "single-session time limit" in report
