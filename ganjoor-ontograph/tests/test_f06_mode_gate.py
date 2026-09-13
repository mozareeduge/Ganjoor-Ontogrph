"""Amendment 20 F06: the flat-assessment mode gate + legacy-ledger bridge.

Discriminating targets (Plans.md F06 DoD):
1. No-policy aggregate refuses and names declarable policies.
2. positioned-concordant refuses on any contested/single-position/
   corroborated-weak hit.
3. The legacy-poem-decision zero-coverage rule still holds.
4. A workspace that never ran an explicit migration still computes
   correctly through the bridge.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from types import SimpleNamespace

from ontograph.assessors import AssessorObject, register_assessor
from ontograph.census import (
    HitOccurrenceAssessment,
    IncompletePositioningError,
    NoResolutionPolicyError,
    append_hit_assessment,
    enforce_mode_requirements,
    full_position_set,
    new_hit_assessment_id,
)
from ontograph.positions import position_for
from ontograph.resolution import ResolutionPolicy, declare_policy, new_policy_id

OBJ = "mirror"


def _hit_via_kwargs(hid: str, poem_id: int):
    """`enforce_mode_requirements` only reads `.id` off each hit -- a
    lightweight stand-in avoids AnchorHit's `id` being a derived
    (read-only) property that cannot be forced to an arbitrary test value."""
    return SimpleNamespace(id=hid, poem_id=poem_id)


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "study"
    ws.mkdir()
    return ws


def test_no_policy_declared_refuses_positioned_full(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1)]
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
        object_address_id=OBJ, decision="accepted", assessor_type="human", assessor_id="mz",
    ))
    with pytest.raises(NoResolutionPolicyError) as exc_info:
        enforce_mode_requirements("positioned-full", hits, ws, OBJ)
    msg = str(exc_info.value)
    assert "concordance" in msg and "named-assessor" in msg and "weighted" in msg


def test_no_policy_declared_refuses_positioned_concordant_too(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1)]
    with pytest.raises(NoResolutionPolicyError):
        enforce_mode_requirements("positioned-concordant", hits, ws, OBJ)


def test_anchor_and_inventory_never_refuse(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1)]
    enforce_mode_requirements("anchor", hits, ws, OBJ)  # must not raise
    enforce_mode_requirements("inventory", hits, ws, OBJ)  # must not raise


def test_positioned_full_via_bridge_no_explicit_migration(tmp_path: Path) -> None:
    """A workspace that only ever used walk/assess (writing to the OLD
    ledger) and never ran migrate_to_positions() must still satisfy
    positioned-full through the live bridge."""
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1), _hit_via_kwargs("ah1-2", 2)]
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
        object_address_id=OBJ, decision="accepted", assessor_type="human", assessor_id="mz",
    ))
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-2",
        object_address_id=OBJ, decision="rejected", assessor_type="human", assessor_id="mz",
    ))
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    enforce_mode_requirements("positioned-full", hits, ws, OBJ)  # must not raise

    positions = full_position_set(ws, OBJ)
    assert len(positions) == 2
    assert {p.assessor_object_id for p in positions} == {"legacy:human:mz"}


def test_positioned_full_refuses_on_partial_coverage(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1), _hit_via_kwargs("ah1-2", 2)]
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
        object_address_id=OBJ, decision="accepted", assessor_type="human", assessor_id="mz",
    ))
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    with pytest.raises(IncompletePositioningError) as exc_info:
        enforce_mode_requirements("positioned-full", hits, ws, OBJ)
    assert exc_info.value.coverage["positioned_hits"] == 1
    assert exc_info.value.coverage["eligible_hits"] == 2


def test_legacy_poem_decision_rows_still_provide_zero_coverage(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = [_hit_via_kwargs("ah1-1", 1)]
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
        object_address_id=OBJ, decision="accepted",
        assessor_type="legacy-poem-decision", assessor_id="",
    ))
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    with pytest.raises(IncompletePositioningError) as exc_info:
        enforce_mode_requirements("positioned-full", hits, ws, OBJ)
    assert exc_info.value.coverage["positioned_hits"] == 0  # the legacy-poem-decision row does NOT count


def test_positioned_concordant_refuses_on_contested_hit(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    hits = [_hit_via_kwargs("ah1-1", 1)]
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")
    position_for(ws, "ah1-1", OBJ, "as-agent", "does-not-occur")  # contested
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    with pytest.raises(IncompletePositioningError) as exc_info:
        enforce_mode_requirements("positioned-concordant", hits, ws, OBJ)
    assert exc_info.value.standing["contested"] == 1


def test_positioned_concordant_refuses_on_single_position_hit(tmp_path: Path) -> None:
    """A hit positioned by exactly one assessor is single-position, not
    concordant -- concordant strictly requires >=2 independence classes."""
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    hits = [_hit_via_kwargs("ah1-1", 1)]
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    with pytest.raises(IncompletePositioningError) as exc_info:
        enforce_mode_requirements("positioned-concordant", hits, ws, OBJ)
    assert exc_info.value.standing["single_position"] == 1


def test_positioned_concordant_passes_when_truly_concordant(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    hits = [_hit_via_kwargs("ah1-1", 1)]
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")
    position_for(ws, "ah1-1", OBJ, "as-agent", "occurs")
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance"))
    enforce_mode_requirements("positioned-concordant", hits, ws, OBJ)  # must not raise


def test_real_position_takes_precedence_over_bridge_for_same_hit(tmp_path: Path) -> None:
    """Once a hit has a real position, it is never also bridged from the
    legacy ledger -- avoids a redundant synthetic duplicate."""
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    append_hit_assessment(ws, HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
        object_address_id=OBJ, decision="rejected", assessor_type="human", assessor_id="someone-else",
    ))
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")  # a REAL position on the same hit

    positions = full_position_set(ws, OBJ)
    assert len(positions) == 1  # not 2 -- the bridge did not also synthesize one
    assert positions[0].assessor_object_id == "as-mz"
