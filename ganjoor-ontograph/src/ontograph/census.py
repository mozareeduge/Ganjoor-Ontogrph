"""Occurrence assessment and occurrence-policy orchestration.

Spec §8.1 (object-incidence modes: anchor/assessed-full/assessed-rule/
estimated), §8.1.1 (v2.3.0: ambiguous-hit denominator rule -- a unit with
only ambiguous hits stays in the eligible-unit denominator, scored 0, and
is reported separately rather than silently folded into presence or
absence), §9 (Close Calibration), §27.2 (estimator default: stratified
proportion + Wilson score interval, spec Appendix C.3 as amended in
v2.3.0).

`OccurrencePolicy` records here are what every later co-incidence/scale/
ablation calculation must read from -- never raw Anchor Hits directly
(spec §27.2, §28.1; this is the exact distinction EXTERNAL_REVIEW.md
Finding 1 found untested in the original fixture).
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field as _dc_field

from ontograph.anchors import AnchorHit


# --- P2.1: Close Calibration sampler (spec §9) ---

def calibration_sample(
    hits: list[AnchorHit], sample_size: int, seed: int, strata_key=None
) -> list[AnchorHit]:
    """Seeded sample over Anchor Hits (spec §9: "random or stratified
    cases ... Top-ranked search results alone are not an adequate
    calibration set"). Reproducible: the same `hits`/`sample_size`/`seed`
    always returns the same sample, in the same order.

    `strata_key`, when given, groups hits by `strata_key(hit)` and draws
    (as evenly as the remainder allows) from each stratum rather than one
    unstratified draw -- still fully deterministic given `seed`."""
    n = min(sample_size, len(hits))
    if strata_key is None:
        rng = random.Random(seed)
        return rng.sample(hits, n)

    strata: dict = {}
    for h in hits:
        strata.setdefault(strata_key(h), []).append(h)
    keys = sorted(strata.keys(), key=str)
    per_stratum = max(1, n // len(keys)) if keys else 0
    rng = random.Random(seed)
    sample: list[AnchorHit] = []
    for k in keys:
        bucket = strata[k]
        take = min(per_stratum, len(bucket))
        sample.extend(rng.sample(bucket, take))
    # top up to n from whatever remains, deterministically
    remaining = [h for h in hits if h not in sample]
    if len(sample) < n and remaining:
        sample.extend(rng.sample(remaining, min(n - len(sample), len(remaining))))
    return sample[:n]


def open_context_ladder(hit: AnchorHit, poem_path) -> dict:
    """Spec §35: match -> verse -> couplet -> section -> poem. Returns the
    immediate context around one Anchor Hit for a calibration reviewer to
    read before deciding accepted/rejected/ambiguous -- never just the
    matched span alone (spec §9's rejection of "top search result" review)."""
    poem = json.loads(poem_path.read_text(encoding="utf-8"))
    couplet_verses = [
        v for v in poem["Verses"] if v["CoupletIndex"] == hit.couplet_index
    ]
    return {
        "match": hit.lexical_anchor,
        "verse": hit.original_text,
        "couplet": couplet_verses,
        "poem_title": poem.get("Title"),
        "poem_id": poem["Id"],
    }


# --- P2.2: OccurrenceAssessment + OccurrencePolicy ---

@dataclass(frozen=True)
class OccurrenceAssessment:
    anchor_hit_poem_id: int
    object_address: str
    decision: str  # accepted | rejected | ambiguous
    rationale: str = ""
    assessor: str = "human"


def apply_assessments(
    hits: list[AnchorHit], assessments: dict[int, str]
) -> list[tuple[AnchorHit, str]]:
    """Pairs each hit with its decision from `assessments` (poem_id ->
    decision). A hit with no entry in `assessments` is NOT silently
    treated as accepted -- it is returned with decision `None`, and
    callers (§8.1's mode-specific functions below) must decide what an
    unassessed hit means for their mode rather than this function
    guessing."""
    return [(h, assessments.get(h.poem_id)) for h in hits]


def accepted_poem_ids(hits: list[AnchorHit], assessments: dict[int, str]) -> set[int]:
    return {h.poem_id for h in hits if assessments.get(h.poem_id) == "accepted"}


def ambiguous_only_poem_ids(hits: list[AnchorHit], assessments: dict[int, str]) -> set[int]:
    """Poems whose hits for this object are ALL ambiguous (none accepted)
    -- the set that spec §8.1.1 says must stay in the eligible-unit
    denominator, scored 0, and be reported separately rather than folded
    into either presence or absence."""
    by_poem: dict[int, list[str]] = {}
    for h in hits:
        by_poem.setdefault(h.poem_id, []).append(assessments.get(h.poem_id))
    return {
        poem_id for poem_id, decisions in by_poem.items()
        if decisions and all(d == "ambiguous" for d in decisions)
    }


# --- P2.3: ambiguous-hit denominator rule (spec §8.1.1, v2.3.0) ---

@dataclass(frozen=True)
class Prevalence:
    numerator: int
    denominator: int
    ambiguous_only_count: int

    @property
    def value(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0


def assessed_full_prevalence(
    eligible_poem_ids: set[int], hits: list[AnchorHit], assessments: dict[int, str]
) -> Prevalence:
    """spec §8.1.1: a unit whose only hits are ambiguous stays in the
    denominator (never dropped), scored 0 in the numerator, and its count
    is reported separately -- never silently folded into either presence
    or absence."""
    accepted = accepted_poem_ids(hits, assessments) & eligible_poem_ids
    ambiguous_only = ambiguous_only_poem_ids(hits, assessments) & eligible_poem_ids
    return Prevalence(
        numerator=len(accepted),
        denominator=len(eligible_poem_ids),
        ambiguous_only_count=len(ambiguous_only),
    )


# --- P2.4: default estimator (spec §27.2, Appendix C.3 v2.3.0) ---

@dataclass(frozen=True)
class EstimatedIncidence:
    point_estimate: float
    wilson_lo: float
    wilson_hi: float
    sample_size: int
    population_size: int
    fpc_applied: bool


def wilson_score_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Standard Wilson score interval for a binomial proportion (no
    external stats dependency -- spec Appendix C.3 names this as the
    provisional default, not a hard requirement to use a particular
    library)."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = p + z ** 2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * n)) / n)
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (max(0.0, lo), min(1.0, hi))


def estimate_incidence(
    population_poem_ids: list[int],
    sample_poem_ids: list[int],
    accepted_in_sample: set[int],
    seed: int,
) -> EstimatedIncidence:
    """Stratified-proportion estimator + Wilson interval (spec §27.2). The
    "stratified" part is the caller's responsibility (pass a
    `sample_poem_ids` already drawn per-stratum, e.g. via
    `calibration_sample(..., strata_key=...)`); this function computes the
    proportion and interval from whatever sample it is given, and applies
    a finite-population correction to the interval width once the sample
    is >10% of the population (spec Appendix C.3)."""
    n = len(sample_poem_ids)
    N = len(population_poem_ids)
    successes = len(accepted_in_sample)
    point = successes / n if n else 0.0
    lo, hi = wilson_score_interval(successes, n)

    fpc_applied = False
    if N > 0 and n / N > 0.10:
        fpc = math.sqrt((N - n) / (N - 1)) if N > 1 else 1.0
        half_width_lo = point - lo
        half_width_hi = hi - point
        lo = max(0.0, point - half_width_lo * fpc)
        hi = min(1.0, point + half_width_hi * fpc)
        fpc_applied = True

    return EstimatedIncidence(
        point_estimate=point, wilson_lo=lo, wilson_hi=hi,
        sample_size=n, population_size=N, fpc_applied=fpc_applied,
    )
