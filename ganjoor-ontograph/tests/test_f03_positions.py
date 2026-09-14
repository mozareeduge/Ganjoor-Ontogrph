"""Amendment 20 F03: OccurrencePosition ledger + Standing computation.

Discriminating targets (Plans.md F03 DoD): unit tests covering all five
Standing values, including the independence-class distinction between
`concordant` and `corroborated-weak`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.assessors import AssessorObject, register_assessor
from ontograph.positions import (
    OccurrencePosition,
    active_positions,
    contested_trace_candidates,
    new_position_id,
    position_coverage,
    position_for,
    queue_by_weight,
    read_positions,
    standing_distribution,
    standing_of,
)

HIT = "ah1-mirror-9101"
OBJ = "mirror"


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "study"
    ws.mkdir()
    return ws


def _register(ws: Path, aid: str, itype: str, iclass: str) -> AssessorObject:
    a = AssessorObject(id=aid, label=aid, assessor_type=itype, apparatus="x", independence_class=iclass)
    register_assessor(ws, a)
    return a


def test_standing_unpositioned(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert standing_of(ws, {}) == "unpositioned"


def test_standing_single_position(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    p = position_for(ws, HIT, OBJ, "as-mz", "occurs")
    active = active_positions([p], HIT, OBJ)
    assert standing_of(ws, active) == "single-position"


def test_standing_concordant_two_independent_classes_agree(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    p1 = position_for(ws, HIT, OBJ, "as-mz", "occurs")
    p2 = position_for(ws, HIT, OBJ, "as-agent", "occurs")
    active = active_positions([p1, p2], HIT, OBJ)
    assert standing_of(ws, active) == "concordant"


def test_standing_corroborated_weak_same_class_agree(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    # a rule authored by an agent shares that agent's independence_class
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    _register(ws, "as-rule", "rule", "apparatus-opus5")
    p1 = position_for(ws, HIT, OBJ, "as-agent", "occurs")
    p2 = position_for(ws, HIT, OBJ, "as-rule", "occurs")
    active = active_positions([p1, p2], HIT, OBJ)
    assert standing_of(ws, active) == "corroborated-weak"


def test_standing_contested_differing_stances(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    p1 = position_for(ws, HIT, OBJ, "as-mz", "occurs")
    p2 = position_for(ws, HIT, OBJ, "as-agent", "does-not-occur")
    active = active_positions([p1, p2], HIT, OBJ)
    assert standing_of(ws, active) == "contested"


def test_non_erasure_second_position_from_same_assessor_supersedes(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    p1 = position_for(ws, HIT, OBJ, "as-mz", "undecidable")
    p2 = position_for(ws, HIT, OBJ, "as-mz", "occurs")  # revision, self-scoped
    assert p2.supersedes == p1.id
    active = active_positions([p1, p2], HIT, OBJ)
    assert len(active) == 1
    assert active["as-mz"].stance == "occurs"


def test_non_erasure_different_assessors_both_stay_active(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    p1 = position_for(ws, HIT, OBJ, "as-mz", "does-not-occur")
    p2 = position_for(ws, HIT, OBJ, "as-agent", "occurs")
    # neither position's supersedes points at the other -- non-erasure
    assert p1.supersedes is None and p2.supersedes is None
    active = active_positions([p1, p2], HIT, OBJ)
    assert set(active) == {"as-mz", "as-agent"}


def test_invalid_stance_rejected() -> None:
    with pytest.raises(ValueError, match="stance"):
        OccurrencePosition(
            id=new_position_id(), anchor_hit_id=HIT, object_address_id=OBJ,
            assessor_object_id="as-mz", stance="accepted",  # old adjudication word
        )


def test_missing_assessor_object_id_rejected() -> None:
    with pytest.raises(ValueError, match="assessor_object_id"):
        OccurrencePosition(
            id=new_position_id(), anchor_hit_id=HIT, object_address_id=OBJ,
            assessor_object_id="", stance="occurs",
        )


def test_position_coverage_and_standing_distribution(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    hits = ["ah1-a", "ah1-b", "ah1-c"]
    position_for(ws, "ah1-a", OBJ, "as-mz", "occurs")
    position_for(ws, "ah1-a", OBJ, "as-agent", "occurs")  # concordant
    position_for(ws, "ah1-b", OBJ, "as-mz", "occurs")  # single-position
    # ah1-c: unpositioned
    cov = position_coverage(ws, hits, OBJ)
    assert cov == {
        "eligible_hits": 3, "positioned_hits": 2, "unpositioned_hits": 1,
        "by_assessor": {"as-mz": 2, "as-agent": 1},
    }
    dist = standing_distribution(ws, hits, OBJ)
    assert dist == {
        "unpositioned": 1, "single_position": 1, "concordant": 1,
        "corroborated_weak": 0, "contested": 0,
    }


def test_contested_hit_mints_trace_candidate(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    position_for(ws, HIT, OBJ, "as-mz", "occurs")
    position_for(ws, HIT, OBJ, "as-agent", "does-not-occur")
    candidates = contested_trace_candidates(ws, [HIT], OBJ)
    assert len(candidates) == 1
    assert candidates[0]["anchor_hit_id"] == HIT
    assert len(candidates[0]["positions"]) == 2


def test_queue_by_weight_orders_and_handles_missing_weight(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-agent", "agent", "apparatus-opus5")
    p_low = position_for(ws, "ah1-low", OBJ, "as-agent", "occurs", weight=0.2)
    p_high = position_for(ws, "ah1-high", OBJ, "as-agent", "occurs", weight=0.9)
    p_none = position_for(ws, "ah1-none", OBJ, "as-agent", "occurs")
    positions = [p_low, p_high, p_none]
    hit_ids = ["ah1-low", "ah1-high", "ah1-none"]

    uncertain_first = queue_by_weight(positions, hit_ids, OBJ, order="uncertain-first")
    assert uncertain_first == ["ah1-low", "ah1-high", "ah1-none"]

    confident_first = queue_by_weight(positions, hit_ids, OBJ, order="confident-first")
    assert confident_first == ["ah1-high", "ah1-low", "ah1-none"]


def test_weight_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="weight"):
        OccurrencePosition(
            id=new_position_id(), anchor_hit_id=HIT, object_address_id=OBJ,
            assessor_object_id="as-mz", stance="occurs", weight=1.5,
        )
