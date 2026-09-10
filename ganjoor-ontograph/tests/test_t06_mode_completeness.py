"""Ledger row T06: mode names and completeness enforcement.

Discriminating targets (execution spec §6.5, T06 + Gate B):

1. `--mode assessed` is an alias for `assessed-full` and WARNS on stderr
   -- it never means partial review.
2. assessed-full with incomplete coverage FAILS with coverage counts and
   the legal alternatives listed -- never silently computes.
3. Coverage = active assessed eligible hits / eligible hits (the
   poem-keyed legacy calculation is removed from the per-hit path).
4. Partial review is never reported as assessed-full.
"""
from __future__ import annotations

import io
import contextlib

import pytest

from ontograph.census import (
    HitOccurrenceAssessment,
    assessed_full_coverage,
    enforce_mode_completeness,
    new_hit_assessment_id,
)
from ontograph.anchors import AnchorHit


def _hit(poem_id: int, verse_order: int) -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=0, position="Right",
        original_text="آینه در دست من است امشب",
        normalized_text="آینه در دست من است امشب",
        token_start=0, token_end=4,
        verse_order=verse_order, corpus_snapshot_id="cs1-test",
    )


def _assess(hit: AnchorHit, decision: str) -> HitOccurrenceAssessment:
    return HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id=hit.id,
        object_address_id=hit.object_address, decision=decision,
        assessor_type="human", assessor_id="mz",
    )


def test_alias_maps_to_assessed_full_with_warning() -> None:
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        mode, warned = resolve_mode_alias("assessed")
    assert mode == "assessed-full"
    assert warned and "assessed" in err.getvalue()


def test_modes_are_the_four_canonical_names() -> None:
    from ontograph.census import CANONICAL_MODES

    assert CANONICAL_MODES == ("anchor", "assessed-full", "assessed-rule", "estimated")


def test_incomplete_coverage_refused_with_counts_and_alternatives() -> None:
    h1, h2, h3 = _hit(9101, 1), _hit(9101, 3), _hit(9102, 1)
    ledger = [_assess(h1, "accepted"), _assess(h2, "rejected")]
    # h3 unassessed -> coverage 2/3
    cov = assessed_full_coverage([h1, h2, h3], ledger)
    assert cov == (2, 3)
    with pytest.raises(IncompleteAssessmentError) as exc:
        enforce_mode_completeness("assessed-full", [h1, h2, h3], ledger)
    assert exc.value.coverage == (2, 3)
    assert "assessed-rule" in exc.value.legal_alternatives
    assert "estimated" in exc.value.legal_alternatives
    assert "walk" in exc.value.legal_alternatives


def test_full_coverage_passes() -> None:
    h1, h2 = _hit(9101, 1), _hit(9101, 3)
    ledger = [_assess(h1, "accepted"), _assess(h2, "ambiguous")]
    enforce_mode_completeness("assessed-full", [h1, h2], ledger)  # no raise


def test_anchor_mode_never_requires_assessments() -> None:
    h1 = _hit(9101, 1)
    enforce_mode_completeness("anchor", [h1], [])  # no raise


def test_legacy_poem_keyed_assessments_do_not_count_as_coverage() -> None:
    # the forbidden shortcut: a poem-keyed legacy row fanned across hits
    # would fake full coverage. Per-hit coverage ignores them entirely.
    h1, h2 = _hit(9101, 1), _hit(9101, 3)
    legacy_rows = [
        HitOccurrenceAssessment(
            id="oa-legacy", anchor_hit_id="", object_address_id="mirror",
            decision="accepted", assessor_type="legacy-poem-decision",
        )
    ]
    cov = assessed_full_coverage([h1, h2], legacy_rows)
    assert cov == (0, 2)
    with pytest.raises(IncompleteAssessmentError):
        enforce_mode_completeness("assessed-full", [h1, h2], legacy_rows)


from ontograph.census import resolve_mode_alias, IncompleteAssessmentError  # noqa: E402
