"""Ledger row T08: narrow/split/trace/widen/context/stop/resume actions.

Discriminating targets (execution spec T08 + Gate C):

1. `n` (narrow): creates a REPLACEMENT anchor version, marks the old
   anchor superseded (never leaves the broad anchor active), appends a
   narrow event, and excludes now-stale decisions from the new population.
2. `s` (split): creates a second object + split event; the hit stays
   undecided.
3. `t` (trace): writes a real Trace record + event with source return.
4. `w` (widen): enlarges the sample deterministically and keeps prompting.
5. `x` (stop): writes completed decisions, lists undecided, never imputes.
6. `?1..?4`: context ladder (match / couplet / neighbors / full poem).
"""
from __future__ import annotations

import pytest

from ontograph.anchors import AnchorHit, LexicalAnchor
from ontograph.walk_state import (
    WalkAction,
    WalkState,
    apply_action,
    run_walk,
)


def _hit(poem_id: int, verse_order: int, text: str = "آینه در دست من است امشب") -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=0, position="Right",
        original_text=text,
        normalized_text=text,
        token_start=0, token_end=4,
        verse_order=verse_order, corpus_snapshot_id="cs1-test",
    )


def test_narrow_creates_replacement_and_supersedes_broad() -> None:
    h1 = _hit(9101, 1)
    state = WalkState(
        object_address="mirror", sample=[h1], corpus_snapshot_id="cs1-test",
        anchors=[LexicalAnchor(object_address="mirror", form="آینه", match_mode="exact")],
    )
    result = apply_action(
        state, WalkAction(token="n", hit_id=h1.id, form="آینه بند", reason="too broad"),
    )
    # new anchor registered, old anchor superseded
    assert [a.form for a in result.anchors] == ["آینه بند"]
    assert result.superseded_anchor_forms == ["آینه"]
    assert result.events[-1]["kind"] == "walk-anchor_narrowed"
    assert result.events[-1]["reason"] == "too broad"


def test_split_creates_second_object_hit_stays_undecided() -> None:
    h1 = _hit(9101, 1)
    state = WalkState(object_address="mirror", sample=[h1], corpus_snapshot_id="cs1-test")
    result = apply_action(
        state, WalkAction(token="s", hit_id=h1.id, new_object_id="mirror-band",
                          rationale="compound word is a different object"),
    )
    assert result.new_objects == ["mirror-band"]
    assert result.events[-1]["kind"] == "walk-object_split"
    # the hit is NOT decided by a split
    assert h1.id in result.undecided


def test_trace_writes_record_with_source_return() -> None:
    h1 = _hit(9101, 1)
    state = WalkState(object_address="mirror", sample=[h1], corpus_snapshot_id="cs1-test")
    result = apply_action(
        state, WalkAction(token="t", hit_id=h1.id, note="material pairing to record"),
    )
    assert result.trace is not None
    assert result.trace["anchor_hit_id"] == h1.id
    assert result.trace["source_return"]["poem_id"] == 9101
    assert result.events[-1]["kind"] == "walk-trace_promoted"


def test_widen_enlarges_sample_deterministically() -> None:
    pool = [_hit(9101, i) for i in range(1, 6)]
    state = WalkState(object_address="mirror", sample=pool[:2],
                      corpus_snapshot_id="cs1-test", candidate_pool=pool)
    result = apply_action(state, WalkAction(token="w", hit_id=pool[0].id))
    assert len(result.sample) > 2
    # deterministic: same state + same action -> same enlarged sample
    result2 = apply_action(
        WalkState(object_address="mirror", sample=pool[:2],
                  corpus_snapshot_id="cs1-test", candidate_pool=pool),
        WalkAction(token="w", hit_id=pool[0].id),
    )
    assert [h.id for h in result.sample] == [h.id for h in result2.sample]


def test_stop_writes_completed_decisions_never_imputes() -> None:
    h1, h2 = _hit(9101, 1), _hit(9102, 1)
    state = WalkState(object_address="mirror", sample=[h1, h2], corpus_snapshot_id="cs1-test")
    result = run_walk(state, responses=[])  # stop with nothing decided
    assert result.undecided == [h1.id, h2.id]
    assert result.accepted == 0 and result.rejected == 0 and result.ambiguous == 0
    assert result.ledger_rows == [], "stop must not fabricate decisions"


def test_context_ladder_levels() -> None:
    h1 = _hit(9101, 1, text="آینه در دست من است امشب")
    state = WalkState(object_address="mirror", sample=[h1], corpus_snapshot_id="cs1-test")
    for level in (1, 2, 3, 4):
        result = apply_action(state, WalkAction(token=f"?{level}", hit_id=h1.id))
        assert result.context_level == level
        assert result.context is not None
