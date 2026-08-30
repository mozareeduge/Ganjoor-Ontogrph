"""Typed co-incidence, conditional association, lift, scale profile, field comparison.

Spec Part V operation packs A-D: §28.1 (typed co-incidence matrix built
from assessed occurrences, never raw anchors -- with a separate,
explicitly-labelled anchor-level view for lexical exploration), §28.2
(conditional association P(B|A)/P(A|B), never "causation"), §28.3 (lift
with a minimum-support guard, never "statistical significance" without a
declared reference condition), §29 (Relation Scale Profile / ScaleSurvival
across the scale ladder), §30 (Compare Fields).

Every co-incidence/scale result here can be computed at EITHER the anchor
level or the assessed level -- callers must say which, and this module
never silently defaults one to the other. See EXTERNAL_REVIEW.md Finding 1
and the mini-ganjoor fixture's poem 9106, which exists specifically so a
test can catch a co-incidence function that reads raw anchors when it
should read assessed occurrences.
"""
from __future__ import annotations

from dataclasses import dataclass

from ontograph.anchors import AnchorHit

MODE_ANCHOR = "anchor"
MODE_ASSESSED = "assessed"


@dataclass(frozen=True)
class CoincidenceResult:
    mode: str
    poem_scale: frozenset
    couplet_scale: frozenset  # of (poem_id, couplet_index) tuples


def _poem_ids(hits: list[AnchorHit], accepted: set[int] | None, mode: str) -> set[int]:
    if mode == MODE_ANCHOR:
        return {h.poem_id for h in hits}
    if mode == MODE_ASSESSED:
        if accepted is None:
            raise ValueError("assessed mode requires an accepted-poem-id set")
        return set(accepted)
    raise ValueError(f"unknown mode: {mode!r}")


def _couplets(hits: list[AnchorHit], accepted: set[int] | None, mode: str) -> set[tuple[int, int]]:
    poem_ids = _poem_ids(hits, accepted, mode)
    # a hit with couplet_index=None (a Position="Comment" prose-commentary
    # verse in the real corpus, see anchors.census()'s own note) has no
    # couplet at all and can never participate in couplet-scale
    # co-incidence -- two such hits sharing "no couplet" are not the same
    # couplet, so None is excluded here rather than silently grouped.
    return {
        (h.poem_id, h.couplet_index) for h in hits
        if h.poem_id in poem_ids and h.couplet_index is not None
    }


def typed_coincidence(
    hits_a: list[AnchorHit], hits_b: list[AnchorHit], mode: str,
    accepted_a: set[int] | None = None, accepted_b: set[int] | None = None,
) -> CoincidenceResult:
    """spec §28.1. `mode=MODE_ANCHOR` builds the separate, explicitly-
    labelled A_anchor matrix (lexical exploration only); `mode=MODE_ASSESSED`
    builds the real co-incidence matrix from `OccurrencePolicy`-derived
    accepted-poem-id sets, which callers must supply -- this function never
    falls back to raw anchors when assessed sets are missing."""
    poems_a = _poem_ids(hits_a, accepted_a, mode)
    poems_b = _poem_ids(hits_b, accepted_b, mode)
    couplets_a = _couplets(hits_a, accepted_a, mode)
    couplets_b = _couplets(hits_b, accepted_b, mode)
    return CoincidenceResult(
        mode=mode,
        poem_scale=frozenset(poems_a & poems_b),
        couplet_scale=frozenset(couplets_a & couplets_b),
    )


@dataclass(frozen=True)
class ConditionalAssociation:
    p_b_given_a: float
    p_a_given_b: float
    coincidence_count: int
    incidence_a: int
    incidence_b: int


def conditional_association(poems_a: set[int], poems_b: set[int]) -> ConditionalAssociation:
    """spec §28.2: P(B|A) and P(A|B), computed from assessed-level poem-id
    sets a caller supplies. Named "conditional association" precisely
    because it is not causation or direction of influence -- callers must
    not relabel it as either."""
    coincidence = poems_a & poems_b
    return ConditionalAssociation(
        p_b_given_a=len(coincidence) / len(poems_a) if poems_a else 0.0,
        p_a_given_b=len(coincidence) / len(poems_b) if poems_b else 0.0,
        coincidence_count=len(coincidence),
        incidence_a=len(poems_a),
        incidence_b=len(poems_b),
    )


class InsufficientSupportError(ValueError):
    """Raised by `lift()` below the configured minimum-support guard (spec
    §28.3) -- lift is not computed at all below the guard, rather than
    computed and left for a caller to notice it's unstable."""


@dataclass(frozen=True)
class Lift:
    value: float
    support: int
    field_size: int
    minimum_support: int


def lift(poems_a: set[int], poems_b: set[int], field_size: int, minimum_support: int = 5) -> Lift:
    """spec §28.3. Refuses (raises) below `minimum_support`, rather than
    returning an unstable number silently. Never itself labelled
    "statistical significance" -- that requires a declared reference
    condition this function does not provide (spec §28.3's own caution)."""
    coincidence = poems_a & poems_b
    support = len(coincidence)
    if support < minimum_support:
        raise InsufficientSupportError(
            f"support {support} below minimum_support {minimum_support}; lift not computed"
        )
    p_a = len(poems_a) / field_size
    p_b = len(poems_b) / field_size
    p_a_and_b = support / field_size
    value = p_a_and_b / (p_a * p_b) if p_a and p_b else 0.0
    return Lift(value=value, support=support, field_size=field_size, minimum_support=minimum_support)


@dataclass(frozen=True)
class ScaleProfile:
    poem_scale: int
    couplet_scale: int
    poem_only_poem_ids: frozenset  # poems where co-incidence survives at poem scale but not couplet scale


def relation_scale_profile(
    hits_a: list[AnchorHit], hits_b: list[AnchorHit], mode: str,
    accepted_a: set[int] | None = None, accepted_b: set[int] | None = None,
) -> ScaleProfile:
    """spec §29: poem-scale and couplet-scale co-incidence side by side,
    plus which poems survive only at the broader scale. Verse-scale and
    token-window scale are not implemented in v0.1 (no ledger row before
    Phase 7 needs them) -- this is a partial scale ladder, not the full
    one, and is named as such rather than silently presented as complete."""
    result = typed_coincidence(hits_a, hits_b, mode, accepted_a, accepted_b)
    poem_only = result.poem_scale - {pid for pid, _ in result.couplet_scale}
    return ScaleProfile(
        poem_scale=len(result.poem_scale),
        couplet_scale=len(result.couplet_scale),
        poem_only_poem_ids=frozenset(poem_only),
    )


@dataclass(frozen=True)
class FieldComparison:
    incidence_a_field1: int
    incidence_a_field2: int
    prevalence_a_field1: float
    prevalence_a_field2: float


def compare_fields(
    poems_with_a_field1: set[int], field1_size: int,
    poems_with_a_field2: set[int], field2_size: int,
) -> FieldComparison:
    """spec §30: raw incidence and prevalence in both fields, side by
    side -- a smoothed ratio is never the only number shown (spec §30:
    "always subordinate to raw support")."""
    return FieldComparison(
        incidence_a_field1=len(poems_with_a_field1),
        incidence_a_field2=len(poems_with_a_field2),
        prevalence_a_field1=len(poems_with_a_field1) / field1_size if field1_size else 0.0,
        prevalence_a_field2=len(poems_with_a_field2) / field2_size if field2_size else 0.0,
    )
