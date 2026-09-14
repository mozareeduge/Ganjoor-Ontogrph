"""Unit incidence, prevalence, spread, concentration, dispersion.

Spec §27.3 (unit incidence I(u,o)), §27.4 (prevalence, denominator always
displayed), §27.5 (spread), §27.6 (concentration/top-source share), §27.7
(dispersion -- a named, versioned Gries DP-family measure, never rendered
without raw counts and partition sizes alongside, spec §27.7 and Appendix
A: "high frequency != wide dispersion").
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ontograph.anchors import AnchorHit
from ontograph.field import PoemRecord

DISPERSION_MEASURE = "gries-2008-dp"


def unit_incidence(poem_id: int, accepted_poem_ids: set[int]) -> int:
    """spec §27.3: I(u,o) = 1 only when u has an accepted occurrence."""
    return 1 if poem_id in accepted_poem_ids else 0


@dataclass(frozen=True)
class Spread:
    distinct_poems: int
    distinct_poets: int
    total_poems: int
    total_poets: int

    @property
    def poem_share(self) -> float:
        return self.distinct_poems / self.total_poems if self.total_poems else 0.0

    @property
    def poet_share(self) -> float:
        return self.distinct_poets / self.total_poets if self.total_poets else 0.0


def spread(accepted_poem_ids: set[int], records: list[PoemRecord]) -> Spread:
    """spec §27.5: distinct poems/poets containing the object. Descriptive
    only -- must not be conflated with dispersion (see `gries_dp` below)."""
    in_scope = [r for r in records if r.poem_id in accepted_poem_ids]
    return Spread(
        distinct_poems=len({r.poem_id for r in in_scope}),
        distinct_poets=len({r.poet_slug for r in in_scope}),
        total_poems=len(records),
        total_poets=len({r.poet_slug for r in records}),
    )


@dataclass(frozen=True)
class Concentration:
    counts_by_poet: dict[str, int]
    total_hits: int

    @property
    def top_poet(self) -> str | None:
        if not self.counts_by_poet:
            return None
        return max(self.counts_by_poet, key=self.counts_by_poet.get)

    @property
    def top_share(self) -> float:
        if not self.total_hits or not self.counts_by_poet:
            return 0.0
        return max(self.counts_by_poet.values()) / self.total_hits


def concentration(accepted_hits: list[AnchorHit], records: list[PoemRecord]) -> Concentration:
    """spec §27.6: top-source share. A high total count with extreme
    concentration must be showable as such -- `counts_by_poet` is always
    carried alongside `top_share`, never dropped."""
    poet_by_poem = {r.poem_id: r.poet_slug for r in records}
    counts = Counter(poet_by_poem[h.poem_id] for h in accepted_hits if h.poem_id in poet_by_poem)
    return Concentration(counts_by_poet=dict(counts), total_hits=sum(counts.values()))


@dataclass(frozen=True)
class Dispersion:
    measure: str
    value: float
    raw_counts_by_poet: dict[str, int]
    partition_sizes_by_poet: dict[str, int]


def gries_dp(accepted_hits: list[AnchorHit], records: list[PoemRecord]) -> Dispersion:
    """Gries (2008) deviation-of-proportions DP: 0.5 * sum(|observed_share_i
    - expected_share_i|) over partitions i (here, poets), where
    expected_share is each poet's share of eligible corpus size and
    observed_share is each poet's share of accepted hits. 0 = perfectly
    even distribution relative to corpus size; 1 = maximally concentrated.
    Always returned with raw counts and partition sizes attached (spec
    §27.7) -- never a bare float."""
    poet_by_poem = {r.poem_id: r.poet_slug for r in records}
    partition_sizes = Counter(r.poet_slug for r in records)
    total_poems = len(records)
    hit_counts = Counter(poet_by_poem[h.poem_id] for h in accepted_hits if h.poem_id in poet_by_poem)
    total_hits = sum(hit_counts.values())

    dp = 0.0
    for poet_slug, size in partition_sizes.items():
        expected_share = size / total_poems if total_poems else 0.0
        observed_share = hit_counts.get(poet_slug, 0) / total_hits if total_hits else 0.0
        dp += abs(observed_share - expected_share)
    dp /= 2

    return Dispersion(
        measure=DISPERSION_MEASURE,
        value=dp,
        raw_counts_by_poet=dict(hit_counts),
        partition_sizes_by_poet=dict(partition_sizes),
    )
