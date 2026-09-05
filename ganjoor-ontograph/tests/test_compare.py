"""Tests for ontograph.compare (ledger rows P3.3-P3.7).

Ground truth drawn from fixtures/mini-ganjoor/manifest.json's
_fixture_ground_truth (anchor_level / assessed_level / divergence_note /
couplet_scale_broad_only_case blocks) -- see EXTERNAL_REVIEW.md Finding 1.
"""
import json
import pathlib
from dataclasses import fields

import pytest

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import accepted_poem_ids
from ontograph.compare import (
    MODE_ANCHOR,
    MODE_ASSESSED,
    ConditionalAssociation,
    InsufficientSupportError,
    compare_fields,
    conditional_association,
    lift,
    relation_scale_profile,
    typed_coincidence,
)
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHORS = [LexicalAnchor(object_address="rust", form="زنگار")]


def _setup():
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    mirror_assessments = {int(k): v for k, v in CANON["mirror"].items()}
    rust_assessments = {int(k): v for k, v in CANON["rust"].items()}
    accepted_mirror = accepted_poem_ids(mirror_hits, mirror_assessments)
    accepted_rust = accepted_poem_ids(rust_hits, rust_assessments)
    return mirror_hits, rust_hits, accepted_mirror, accepted_rust


# --- P3.3: typed_coincidence ---

def test_anchor_mode_coincidence_is_4_poems_3_couplets():
    mirror_hits, rust_hits, _, _ = _setup()
    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assert result.poem_scale == frozenset({9101, 9102, 9106, 9201})
    assert result.couplet_scale == frozenset({(9101, 0), (9106, 0), (9201, 0)})


def test_assessed_mode_coincidence_is_3_poems_2_couplets():
    mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    result = typed_coincidence(
        mirror_hits, rust_hits, mode=MODE_ASSESSED,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert result.poem_scale == frozenset({9101, 9102, 9201})
    assert result.couplet_scale == frozenset({(9101, 0), (9201, 0)})


def test_anchor_and_assessed_coincidence_diverge_on_poem_9106():
    """The direct Finding-1 regression guard: an engine that reads raw
    anchors where it should read assessed occurrences would silently
    report the anchor-level numbers for both calls. 9106's mirror hit is
    assessed rejected while its rust hit is accepted, so it must appear
    in the anchor-mode result and must NOT appear in the assessed-mode
    result."""
    mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    anchor_result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assessed_result = typed_coincidence(
        mirror_hits, rust_hits, mode=MODE_ASSESSED,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert anchor_result.poem_scale != assessed_result.poem_scale
    assert 9106 in anchor_result.poem_scale
    assert 9106 not in assessed_result.poem_scale


def test_assessed_mode_without_accepted_sets_raises():
    mirror_hits, rust_hits, _, _ = _setup()
    with pytest.raises(ValueError):
        typed_coincidence(mirror_hits, rust_hits, mode=MODE_ASSESSED)


# --- P3.4: conditional_association ---

def test_conditional_association_is_asymmetric_and_never_called_causation():
    _, _, accepted_mirror, accepted_rust = _setup()
    assoc = conditional_association(accepted_mirror, accepted_rust)
    assert assoc.incidence_a == 5  # accepted mirror poems
    assert assoc.incidence_b == 4  # accepted rust poems
    assert assoc.coincidence_count == 3
    assert assoc.p_b_given_a == pytest.approx(3 / 5)
    assert assoc.p_a_given_b == pytest.approx(3 / 4)
    assert assoc.p_b_given_a != assoc.p_a_given_b
    # the result must never be *labelled* causation -- field names stay
    # purely conditional-probability language (the docstring itself
    # legitimately says "not causation" to warn callers off relabelling it)
    for field_name in (f.name for f in fields(ConditionalAssociation)):
        assert "cause" not in field_name.lower()


# --- P3.5: lift ---

def test_lift_below_minimum_support_raises():
    _, _, accepted_mirror, accepted_rust = _setup()
    with pytest.raises(InsufficientSupportError):
        lift(accepted_mirror, accepted_rust, field_size=27, minimum_support=5)


def test_lift_computes_when_support_meets_guard():
    _, _, accepted_mirror, accepted_rust = _setup()
    result = lift(accepted_mirror, accepted_rust, field_size=27, minimum_support=3)
    assert result.support == 3
    p_a = 5 / 27
    p_b = 4 / 27
    p_a_and_b = 3 / 27
    assert result.value == pytest.approx(p_a_and_b / (p_a * p_b))


# --- P3.6: relation_scale_profile ---

def test_scale_profile_assessed_mode_isolates_9102_as_poem_only():
    mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    profile = relation_scale_profile(
        mirror_hits, rust_hits, mode=MODE_ASSESSED,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert profile.poem_scale == 3
    assert profile.couplet_scale == 2
    assert profile.poem_only_poem_ids == frozenset({9102})


# --- P3.7: compare_fields ---

def test_compare_fields_carries_raw_incidence_alongside_prevalence():
    _, _, accepted_mirror, _ = _setup()
    sample1_mirror = {pid for pid in accepted_mirror if pid < 9200}
    sample2_mirror = {pid for pid in accepted_mirror if 9200 <= pid < 9300}
    result = compare_fields(sample1_mirror, 7, sample2_mirror, 5)
    assert result.incidence_a_field1 == len(sample1_mirror)
    assert result.incidence_a_field2 == len(sample2_mirror)
    assert result.prevalence_a_field1 == pytest.approx(len(sample1_mirror) / 7)
    assert result.prevalence_a_field2 == pytest.approx(len(sample2_mirror) / 5)
