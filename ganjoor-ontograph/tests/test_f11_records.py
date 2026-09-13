"""Amendment 20 F11: ResidueRecord, ReductionRecord, ClaimRecord, and
required unsupported_zones/counter_evidence on FindingRecord.

Discriminating targets (Plans.md F11 DoD):
1. `record add --type finding` with an empty unsupported_zones is refused.
2. New residue/reduction record types are reachable via `record add`.
3. relation/claim remain machine-managed (not silently opened up).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.records import ClaimRecord, FindingRecord, ReductionRecord, ResidueRecord

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed(capsys, tmp_path: Path, study_id: str):
    # `record add`'s parser uses the `common` parent, not `with_corpus` --
    # it never takes --corpus-root (unlike census/walk/etc.)
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir]
    code, out, err = _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    return ws_dir, base


def test_finding_record_requires_unsupported_zones() -> None:
    with pytest.raises(ValueError, match="unsupported_zones"):
        FindingRecord(id="f-1", counter_evidence=["x"])


def test_finding_record_requires_counter_evidence() -> None:
    with pytest.raises(ValueError, match="counter_evidence"):
        FindingRecord(id="f-1", unsupported_zones=["x"])


def test_finding_record_valid_with_both_fields() -> None:
    f = FindingRecord(id="f-1", unsupported_zones=["x"], counter_evidence=["y"])
    assert f.unsupported_zones == ["x"]


def test_claim_record_requires_both_fields() -> None:
    with pytest.raises(ValueError, match="unsupported_zones"):
        ClaimRecord(id="c-1", counter_evidence=["x"])
    with pytest.raises(ValueError, match="counter_evidence"):
        ClaimRecord(id="c-1", unsupported_zones=["x"])
    claim = ClaimRecord(id="c-1", unsupported_zones=["x"], counter_evidence=["y"])
    assert claim.id == "c-1"


def test_residue_record_requires_both_fields() -> None:
    with pytest.raises(ValueError, match="stopped_because"):
        ResidueRecord(id="r-1", route_description="tried X")
    with pytest.raises(ValueError, match="route_description"):
        ResidueRecord(id="r-1", stopped_because="corpus lacked Y")
    residue = ResidueRecord(id="r-1", route_description="tried X", stopped_because="corpus lacked Y")
    assert residue.id == "r-1"


def test_reduction_record_requires_all_four_fields() -> None:
    with pytest.raises(ValueError):
        ReductionRecord(id="red-1", omitted_or_compressed="177 of 218 hits")
    reduction = ReductionRecord(
        id="red-1", omitted_or_compressed="177 of 218 hits",
        reason="assessment capacity", consequence="corpus-wide claim blocked",
        recovery_route="resume the walk in a future session",
    )
    assert reduction.recovery_route


def test_cli_record_add_finding_empty_unsupported_zones_refused(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed(capsys, tmp_path, "f11-empty")
    payload = tmp_path / "finding.json"
    payload.write_text(json.dumps({"id": "f-1", "pressure": "p", "observation": "o"}), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "f11-empty", "--type", "finding", "--file", str(payload), *base, "--json"])
    assert code == 1
    assert "unsupported_zones" in err


def test_cli_record_add_residue_and_reduction_round_trip(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed(capsys, tmp_path, "f11-new-types")

    residue_file = tmp_path / "residue.json"
    residue_file.write_text(json.dumps({
        "id": "res-1", "route_description": "tried assessing all 218 hits solo",
        "stopped_because": "exceeded available research time this session",
        "created_by": "mz",
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "f11-new-types", "--type", "residue", "--file", str(residue_file), *base, "--json"])
    assert code == 0, err or out

    reduction_file = tmp_path / "reduction.json"
    reduction_file.write_text(json.dumps({
        "id": "redu-1", "omitted_or_compressed": "177 of 218 hits left unpositioned",
        "reason": "single-researcher assessment capacity",
        "consequence": "corpus-wide claim is blocked; only inventory mode is available",
        "recovery_route": "declare a stratified estimate, or resume the walk",
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "f11-new-types", "--type", "reduction", "--file", str(reduction_file), *base, "--json"])
    assert code == 0, err or out

    code, out, err = _run(capsys, ["record", "list", "f11-new-types", *base, "--json"])
    assert code == 0, err or out
    listed = json.loads(out)
    assert listed["count"] == 2
    assert set(listed["by_type"]["residue"][0].keys()) >= {"id", "route_description", "stopped_because"}


def test_relation_and_claim_remain_machine_managed(tmp_path: Path, capsys) -> None:
    """Widening RECORD_CLASSES to include ClaimRecord must NOT silently
    reopen the generic `record add` route for relation/claim -- both stay
    behind their existing, deliberate governed-writer boundary."""
    ws_dir, base = _seed(capsys, tmp_path, "f11-blocked")
    for rtype in ("relation", "claim"):
        payload = tmp_path / f"{rtype}.json"
        payload.write_text(json.dumps({"id": f"{rtype}-1"}), encoding="utf-8")
        code, out, err = _run(capsys, ["record", "add", "f11-blocked", "--type", rtype, "--file", str(payload), *base, "--json"])
        assert code == 1
        assert "machine-managed" in err
