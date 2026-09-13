"""Amendment 20 F10: Claim Permission ceiling (claims.py) + enforcement
in `record add`.

Discriminating targets (Plans.md F10 DoD):
1. A Finding declaring `argue` against a single-assessor `positioned-full`
   result is refused.
2. The same result under `positioned-concordant` with corroboration passes.
3. A result whose contested share exceeds the (default zero) threshold is
   capped at "describe locally" even at 100% positioning coverage.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.claims import ClaimPermissionError, ceiling_for, exceeds_ceiling

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- unit tests on claims.py directly ---

def test_exceeds_ceiling_ordering() -> None:
    assert exceeds_ceiling("argue", "describe locally") is True
    assert exceeds_ceiling("describe locally", "argue") is False
    assert exceeds_ceiling("argue", "argue") is False
    assert exceeds_ceiling("blocked", "preserve only") is False  # blocked never exceeds anything


def test_ceiling_for_anchor_mode() -> None:
    op = {"result": {"mode": "anchor"}}
    assert ceiling_for(None, op) == "preserve only"


def test_ceiling_for_inventory_mode() -> None:
    op = {"result": {"mode": "inventory"}}
    assert ceiling_for(None, op) == "describe locally"


def test_ceiling_for_positioned_full_partial_coverage() -> None:
    op = {"result": {
        "mode": "positioned-full",
        "positioning": {"eligible_hits": 5, "positioned_hits": 4, "unpositioned_hits": 1, "by_assessor": {"as-mz": 4}},
        "standing": {"contested": 0},
    }}
    assert ceiling_for(None, op) == "describe locally"


def test_ceiling_for_positioned_full_single_assessor(tmp_path: Path) -> None:
    op = {"result": {
        "mode": "positioned-full",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0, "by_assessor": {"as-mz": 5}},
        "standing": {"contested": 0},
    }}
    assert ceiling_for(tmp_path, op) == "describe distribution under declared conditions"


def test_ceiling_for_positioned_full_two_independent_assessors(tmp_path: Path) -> None:
    from ontograph.assessors import AssessorObject, register_assessor

    ws = tmp_path
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    op = {"result": {
        "mode": "positioned-full",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0,
                         "by_assessor": {"as-mz": 5, "as-agent": 5}},
        "standing": {"contested": 0},
    }}
    assert ceiling_for(ws, op) == "argue cautiously"


def test_ceiling_for_positioned_full_two_assessors_same_class_no_better_than_one(tmp_path: Path) -> None:
    """The anti-gaming guard: two assessors sharing an independence class
    do not corroborate each other -- no better than a single voice."""
    from ontograph.assessors import AssessorObject, register_assessor

    ws = tmp_path
    register_assessor(ws, AssessorObject(id="as-agent-v1", label="a1", assessor_type="agent", apparatus="x", independence_class="apparatus-opus5"))
    register_assessor(ws, AssessorObject(id="as-rule-v1", label="r1", assessor_type="rule", apparatus="x", independence_class="apparatus-opus5"))
    op = {"result": {
        "mode": "positioned-full",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0,
                         "by_assessor": {"as-agent-v1": 5, "as-rule-v1": 5}},
        "standing": {"contested": 0},
    }}
    assert ceiling_for(ws, op) == "describe distribution under declared conditions"


def test_ceiling_for_positioned_concordant_is_argue() -> None:
    op = {"result": {
        "mode": "positioned-concordant",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0, "by_assessor": {"as-mz": 5, "as-agent": 5}},
        "standing": {"contested": 0},
    }}
    assert ceiling_for(None, op) == "argue"


def test_ceiling_for_any_contestation_caps_at_describe_locally() -> None:
    op = {"result": {
        "mode": "positioned-concordant",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0, "by_assessor": {"as-mz": 5, "as-agent": 5}},
        "standing": {"contested": 1},  # even one contested hit, at 100% coverage
    }}
    assert ceiling_for(None, op) == "describe locally"


def test_ceiling_for_weighted_policy_is_one_level_below(tmp_path: Path) -> None:
    from ontograph.assessors import AssessorObject, register_assessor

    ws = tmp_path
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    op = {"result": {
        "mode": "positioned-full",
        "positioning": {"eligible_hits": 5, "positioned_hits": 5, "unpositioned_hits": 0,
                         "by_assessor": {"as-mz": 5, "as-agent": 5}},
        "standing": {"contested": 0},
        "resolution_policy": {"id": "rp1-x", "kind": "weighted"},
    }}
    # base would be "argue cautiously"; weighted drops it one level
    assert ceiling_for(ws, op) == "describe distribution under declared conditions"


# --- CLI end-to-end: the exact two DoD scenarios ---

def _seed_situation(ws_dir: str, study_id: str) -> None:
    """A minimal ResearchSituation written directly (bypassing the full
    inquire/review flow, which this test doesn't need) so governed
    operations get a real operation_record_id -- mirrors the lightweight
    `_sit()` helper pattern used elsewhere in this test suite."""
    ws = Path(ws_dir) / study_id
    p = ws / "research" / "research-situations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": "rs-f10", "study_id": study_id, "verbatim_hunch": "h",
            "normalized_display_hunch": "h", "language_observations": [],
            "premature_decisions": [], "status": "situational", "actor": "human",
            "supersedes": None,
        }) + "\n")


def _seed_and_walk(capsys, tmp_path: Path, study_id: str):
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]
    assert _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])[0] == 0
    _seed_situation(ws_dir, study_id)
    assert _run(capsys, [
        "object", "add", study_id, "--address", "mirror", "--label", "Mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", ws_dir,
    ])[0] == 0
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    assert _run(capsys, ["walk", study_id, "--object", "mirror", "--script", str(sp), *base, "--json"])[0] == 0
    return ws_dir, base


def test_finding_declaring_argue_on_single_assessor_positioned_full_refused(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed_and_walk(capsys, tmp_path, "f10-refuse")
    assert _run(capsys, ["policy", "declare", "f10-refuse", "--kind", "concordance", "--workspaces-dir", ws_dir, "--json"])[0] == 0

    code, out, err = _run(capsys, ["census", "f10-refuse", "--object", "mirror", "--mode", "positioned-full", *base, "--json"])
    assert code == 0, err or out
    op_id = json.loads(out)["operation_record_id"]

    payload = tmp_path / "finding.json"
    payload.write_text(json.dumps({
        "id": "f-refuse", "pressure": "p", "observation": "o",
        "operation_or_construction": op_id, "claim_permission": "argue",
        "unsupported_zones": ["none recorded -- fixture test"],
        "counter_evidence": ["none recorded -- fixture test"],
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "f10-refuse", "--type", "finding", "--file", str(payload), "--workspaces-dir", ws_dir, "--json"])
    assert code == 1
    assert "exceeds the ceiling" in err


def test_finding_declaring_argue_on_positioned_concordant_with_corroboration_passes(tmp_path: Path, capsys) -> None:
    from ontograph.assessors import AssessorObject, register_assessor
    from ontograph.positions import position_for

    ws_dir, base = _seed_and_walk(capsys, tmp_path, "f10-pass")
    ws = Path(ws_dir) / "f10-pass"

    # bridge the walk's legacy positions, then add a second, independent
    # assessor agreeing on every hit -- making every hit concordant
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))

    # fetch the actual hit ids via an inventory census, then corroborate each
    code, out, err = _run(capsys, ["census", "f10-pass", "--object", "mirror", "--mode", "inventory", *base, "--json"])
    assert code == 0, err or out
    from ontograph.census import full_position_set
    for p in full_position_set(ws, "mirror"):
        position_for(ws, p.anchor_hit_id, "mirror", "as-agent", p.stance)

    assert _run(capsys, ["policy", "declare", "f10-pass", "--kind", "concordance", "--workspaces-dir", ws_dir, "--json"])[0] == 0

    code, out, err = _run(capsys, ["census", "f10-pass", "--object", "mirror", "--mode", "positioned-concordant", *base, "--json"])
    assert code == 0, err or out
    op_id = json.loads(out)["operation_record_id"]

    payload = tmp_path / "finding.json"
    payload.write_text(json.dumps({
        "id": "f-pass", "pressure": "p", "observation": "o",
        "operation_or_construction": op_id, "claim_permission": "argue",
        "unsupported_zones": ["none recorded -- fixture test"],
        "counter_evidence": ["none recorded -- fixture test"],
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "f10-pass", "--type", "finding", "--file", str(payload), "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
