"""Ledger row T07: walk state machine separated from terminal I/O,
context rendering, stable identity-based scripts.

Discriminating targets (execution spec §6.3, T07/T08 locks + Gate C):

1. The state machine is a pure function over (sample hits, responses,
   ledger) -> WalkResult; no stdin anywhere in the module.
2. Scripted responses are IDENTITY-based: each response names its
   anchor_hit_id; array order is not identity. A response for an
   unknown/stale hit ID fails atomically (nothing written).
3. Context display: every presented hit carries hit ID, progress,
   poet/title/poem/category/source, highlighted verse, couplet,
   neighboring couplets, and available actions (§7 walk contract).
4. Resume on the same snapshot selects the active unassessed hits.
5. Undecided hits are never imputed.
"""
from __future__ import annotations

import pytest

from ontograph.anchors import AnchorHit
from ontograph.census import HitOccurrenceAssessment, new_hit_assessment_id
from ontograph.walk_state import (
    WalkResponse,
    WalkState,
    build_script_template,
    hit_context,
    run_walk,
)


def _hit(poem_id: int, verse_order: int) -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=0, position="Right",
        original_text="آینه در دست من است امشب",
        normalized_text="آینه در دست من است امشب",
        token_start=0, token_end=4,
        verse_order=verse_order, corpus_snapshot_id="cs1-test",
    )


def test_run_walk_is_pure_no_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    # any attempt to read stdin inside run_walk must explode: the state
    # machine is separated from terminal I/O (T07 lock)
    monkeypatch.setattr(
        "sys.stdin", property(lambda self: (_ for _ in ()).throw(AssertionError("no stdin in walk_state")))
    )
    hits = [_hit(9101, 1), _hit(9102, 1)]
    result = run_walk(
        WalkState(object_address="mirror", sample=hits, corpus_snapshot_id="cs1-test"),
        responses=[],
    )
    assert result.accepted == 0 and result.rejected == 0 and result.ambiguous == 0
    assert len(result.undecided) == 2


def test_identity_based_responses_order_irrelevant() -> None:
    h1, h2 = _hit(9101, 1), _hit(9102, 1)
    a, b = WalkResponse(anchor_hit_id=h1.id, action="accepted"), WalkResponse(anchor_hit_id=h2.id, action="rejected")
    r1 = run_walk(WalkState(object_address="mirror", sample=[h1, h2], corpus_snapshot_id="cs1-test"), [a, b])
    r2 = run_walk(WalkState(object_address="mirror", sample=[h1, h2], corpus_snapshot_id="cs1-test"), [b, a])
    assert r1.accepted == r2.accepted == 1
    assert r1.rejected == r2.rejected == 1


def test_stale_hit_id_fails_atomically() -> None:
    h1 = _hit(9101, 1)
    stale = WalkResponse(anchor_hit_id="ah1-doesnotexist0000000000000000", action="accepted")
    with pytest.raises(ValueError, match="unknown|stale"):
        run_walk(WalkState(object_address="mirror", sample=[h1], corpus_snapshot_id="cs1-test"), [stale])


def test_context_display_contract() -> None:
    h1 = _hit(9101, 1)
    ctx = hit_context(h1, sample_size=2, position=1, poet="آزمایشی۱",
                      title="غزل آزمایشی ۱-۱", category="/sample1/ghazal",
                      source="/fixture/9101")
    assert ctx["anchor_hit_id"] == h1.id
    assert ctx["progress"] == "1/2"
    assert ctx["poet"] == "آزمایشی۱" and ctx["title"] == "غزل آزمایشی ۱-۱"
    assert ctx["category"] == "/sample1/ghazal" and ctx["source"] == "/fixture/9101"
    assert "آینه" in ctx["verse"]
    assert set(ctx["actions"]) >= {"a", "r", "u", "n", "s", "t", "w", "x", "?"}


def test_resume_selects_unassessed_on_same_snapshot() -> None:
    h1, h2 = _hit(9101, 1), _hit(9102, 1)
    ledger = [HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id=h1.id,
        object_address_id="mirror", decision="accepted",
        assessor_type="human", assessor_id="mz",
    )]
    result = run_walk(
        WalkState(object_address="mirror", sample=[h1, h2],
                  corpus_snapshot_id="cs1-test", resume_ledger=ledger),
        responses=[],
    )
    assert result.accepted == 0  # h1 already assessed; resume does not re-ask
    assert result.undecided == [h2.id]


def test_script_template_is_identity_shaped() -> None:
    h1 = _hit(9101, 1)
    template = build_script_template("mirror", "cs1-test", [h1])
    assert template["schema_version"] == "1.0"
    assert template["object_address_id"] == "mirror"
    assert template["corpus_snapshot_id"] == "cs1-test"
    assert template["responses"] == [{"anchor_hit_id": h1.id, "action": ""}]
