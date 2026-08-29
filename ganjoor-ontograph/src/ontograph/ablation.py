"""Ablation and AblationRetention.

Spec §31: deliberately remove a component (poet, poem, category, lexical
anchor variant, object address, Relation-Object, derived field rule) and
recompute a declared result; `AblationRetention = M(after) / M(before)`.
Names what was removed and what remained -- never explains *why* without a
Finding (spec §16, Appendix A: "conditional association != causation"
applies here too).

Per EXTERNAL_REVIEW.md Finding 1, ablation retention must be computed and
reported at both the anchor level and the assessed level when they differ.
On the mini-ganjoor fixture's `ablation_remove_sample1` case (removing
poems 9101-9107), anchor-level retention is 1/4 poem-scale, 1/3
couplet-scale; assessed-level retention is 1/3 poem-scale, 1/2
couplet-scale -- an engine that only ever computes one level cannot show
this divergence.

Implemented in ledger row P3.8.
"""
from __future__ import annotations

from dataclasses import dataclass

from ontograph.anchors import AnchorHit
from ontograph.compare import typed_coincidence


@dataclass(frozen=True)
class AblationRetention:
    mode: str
    original_poem_scale: int
    remaining_poem_scale: int
    original_couplet_scale: int
    remaining_couplet_scale: int

    @property
    def poem_scale_retention(self) -> float:
        return self.remaining_poem_scale / self.original_poem_scale if self.original_poem_scale else 0.0

    @property
    def couplet_scale_retention(self) -> float:
        return self.remaining_couplet_scale / self.original_couplet_scale if self.original_couplet_scale else 0.0


def _remove_poems(hits: list[AnchorHit], removed_poem_ids: set[int]) -> list[AnchorHit]:
    return [h for h in hits if h.poem_id not in removed_poem_ids]


def ablation_retention(
    hits_a: list[AnchorHit], hits_b: list[AnchorHit], mode: str,
    removed_poem_ids: set[int],
    accepted_a: set[int] | None = None, accepted_b: set[int] | None = None,
) -> AblationRetention:
    """spec §31: `M(after) / M(before)` for typed co-incidence at the given
    mode (anchor or assessed), where the ablated component is a set of
    poems removed from the field. Reports raw before/after counts at both
    poem-scale and couplet-scale alongside the ratio -- never a bare
    percentage -- and never phrases the result as an explanation of why
    the object appears where it does."""
    original = typed_coincidence(hits_a, hits_b, mode, accepted_a, accepted_b)

    remaining_hits_a = _remove_poems(hits_a, removed_poem_ids)
    remaining_hits_b = _remove_poems(hits_b, removed_poem_ids)
    remaining_accepted_a = accepted_a - removed_poem_ids if accepted_a is not None else None
    remaining_accepted_b = accepted_b - removed_poem_ids if accepted_b is not None else None
    remaining = typed_coincidence(
        remaining_hits_a, remaining_hits_b, mode,
        remaining_accepted_a, remaining_accepted_b,
    )

    return AblationRetention(
        mode=mode,
        original_poem_scale=len(original.poem_scale),
        remaining_poem_scale=len(remaining.poem_scale),
        original_couplet_scale=len(original.couplet_scale),
        remaining_couplet_scale=len(remaining.couplet_scale),
    )
