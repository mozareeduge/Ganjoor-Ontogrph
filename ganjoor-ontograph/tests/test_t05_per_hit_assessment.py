"""Ledger row T05: per-hit OccurrenceAssessment and supersession.

Discriminating targets (execution spec §6.4, §13 T05 + Gate B):

1. Different decisions for two hits in ONE poem are representable and
   aggregate differently — the poem-keyed legacy model could not.
2. Supersession per hit: a reassessment names its predecessor; the
   active decision is the latest valid row per (object, hit); the
   superseded row remains in the ledger (append-only).
3. Mixed-poem aggregation: a poem with one accepted + one rejected hit
   counts once as present (at least one accepted), and its rejected hit
   is not silently promoted.
4. Invalid reassessment (superseding an already-superseded row) is refused.

The legacy poem-keyed `apply_assessments` (P2.2) is untouched; these
tests exercise ONLY the T05 per-hit API (`HitOccurrenceAssessment`,
`supersede`, `active_decision`, `hit_decisions`).
"""
from __future__ import annotations

import pytest

from ontograph.census import (
    HitOccurrenceAssessment,
    active_decision,
    hit_decisions,
    supersede,
    new_hit_assessment_id,
)
from ontograph.anchors import AnchorHit


def _hit(poem_id: int, verse_order: int, cs: str = "cs1-test") -> AnchorHit:
    return AnchorHit(
        object_address="mirror",
        lexical_anchor="آینه",
        poem_id=poem_id,
        couplet_index=0,
        position="Right",
        original_text="آینه در دست من است امشب",
        normalized_text="آینه در دست من است امشب",
        token_start=0,
        token_end=4,
        verse_order=verse_order,
        corpus_snapshot_id=cs,
    )


def _assess(hit: AnchorHit, decision: str, row_id: str | None = None,
            supersedes: str | None = None) -> HitOccurrenceAssessment:
    return HitOccurrenceAssessment(
        id=row_id or new_hit_assessment_id(),
        anchor_hit_id=hit.id,
        object_address_id=hit.object_address,
        decision=decision,
        assessor_type="human",
        assessor_id="mz",
        supersedes=supersedes,
    )


def test_two_hits_one_poem_two_decisions() -> None:
    h1, h2 = _hit(9101, 1), _hit(9101, 3)
    ledger = [_assess(h1, "accepted"), _assess(h2, "rejected")]
    decisions = hit_decisions([h1, h2], ledger)
    assert decisions[h1.id] == "accepted"
    assert decisions[h2.id] == "rejected"


def test_supersession_names_predecessor_and_latest_wins() -> None:
    h1 = _hit(9101, 1)
    first = _assess(h1, "rejected")
    second = supersede(first, decision="accepted", rationale="missed the literal reading",
                       assessor_type="human", assessor_id="mz")
    assert second.supersedes == first.id
    assert second.anchor_hit_id == first.anchor_hit_id
    ledger = [first, second]
    assert active_decision(ledger, h1.id).decision == "accepted"
    # append-only: the superseded row is still there
    assert any(r.id == first.id and r.decision == "rejected" for r in ledger)


def test_active_decision_latest_valid_per_hit() -> None:
    ha, hb = _hit(9101, 1), _hit(9102, 1)
    rows = [
        _assess(ha, "ambiguous", row_id="oa-1"),
        _assess(hb, "accepted", row_id="oa-2"),
        _assess(ha, "accepted", row_id="oa-3", supersedes="oa-1"),
    ]
    assert active_decision(rows, ha.id).id == "oa-3"
    assert active_decision(rows, hb.id).id == "oa-2"
    assert active_decision(rows, "ah1-nonexistent") is None


def test_double_supersession_of_one_row_refused() -> None:
    h1 = _hit(9101, 1)
    first = _assess(h1, "rejected")
    supersede(first, decision="accepted", assessor_type="human", assessor_id="mz")
    with pytest.raises(ValueError, match="superseded"):
        supersede(first, decision="ambiguous", assessor_type="human", assessor_id="mz")


def test_mixed_poem_aggregates_once_present() -> None:
    h1, h2 = _hit(9101, 1), _hit(9101, 3)
    ledger = [_assess(h1, "accepted"), _assess(h2, "rejected")]
    decisions = hit_decisions([h1, h2], ledger)
    accepted_poems = {h.poem_id for h in (h1, h2) if decisions[h.id] == "accepted"}
    assert accepted_poems == {9101}
    # the rejected hit is visible as rejected, never silently promoted
    assert decisions[h2.id] == "rejected"
