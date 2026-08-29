"""Live invariant audit against Appendix A's mandatory non-equivalence
list (ledger row P3.9, added per Finding 4 of the external review).

Appendix A lists ~28 non-equivalences a finished study must never
silently collapse. Only the items with a real, testable counterpart in
the v0.1 engine as it exists at this point in the build (corpus, normalize,
field, anchors, census, metrics, compare, ablation, workspace) are
checked here. Everything Appendix A names that depends on Phase 4+
concepts not yet built -- Profile, Finding, Relation-Object, Mapping
Object, Trace, Experiment, graph projection, Reduction Record -- is out
of scope for this row and is NOT silently claimed as covered; this file
must be extended (not just re-run) as those modules land, and re-checked
again at P7.4 before the implementation gates are declared green.
"""
import json
import pathlib

import pytest

from ontograph.ablation import AblationRetention, ablation_retention
import ontograph.ablation as ablation_module
from ontograph.anchors import LexicalAnchor, census
from ontograph.census import EstimatedIncidence, accepted_poem_ids, calibration_sample, estimate_incidence
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED, ConditionalAssociation, conditional_association, typed_coincidence
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHORS = [LexicalAnchor(object_address="rust", form="زنگار")]
HEART_ANCHOR = [LexicalAnchor(object_address="heart", form="دل")]

SAMPLE1_POEM_IDS = {9101, 9102, 9103, 9104, 9105, 9106, 9107}


def _setup():
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    mirror_assessments = {int(k): v for k, v in CANON["mirror"].items()}
    rust_assessments = {int(k): v for k, v in CANON["rust"].items()}
    accepted_mirror = accepted_poem_ids(mirror_hits, mirror_assessments)
    accepted_rust = accepted_poem_ids(rust_hits, rust_assessments)
    return records, mirror_hits, rust_hits, accepted_mirror, accepted_rust


# --- "Anchor Hit != object occurrence" / "co-incidence != relation" ---

def test_anchor_hit_count_differs_from_coincidence_numerator():
    """Appendix A: 'Anchor Hit != object occurrence', 'co-incidence !=
    relation'. The raw mirror anchor hit count (P1.5: 7, token-aware) must
    not equal either co-incidence numerator computed from it -- if it did
    on this fixture, that would be a coincidence of the fixture's numbers,
    not evidence the two concepts have been kept distinct, so this checks
    against both the anchor-level and assessed-level numerators."""
    _, mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    mirror_anchor_hit_count = len(mirror_hits)
    assert mirror_anchor_hit_count == 7

    anchor_coincidence = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assessed_coincidence = typed_coincidence(
        mirror_hits, rust_hits, mode=MODE_ASSESSED,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert mirror_anchor_hit_count != len(anchor_coincidence.poem_scale)
    assert mirror_anchor_hit_count != len(assessed_coincidence.poem_scale)


# --- "estimated incidence != exact census" ---

def test_estimated_incidence_never_labelled_exact():
    """Appendix A: 'estimated incidence != exact census'. Structural
    check: EstimatedIncidence has no field or output claiming exactness,
    and always carries a (possibly wide) Wilson interval alongside the
    point estimate -- there is no code path that can report an estimate
    as a bare number."""
    from dataclasses import fields
    field_names = [f.name for f in fields(EstimatedIncidence)]
    assert not any("exact" in name.lower() for name in field_names)
    assert "wilson_lo" in field_names and "wilson_hi" in field_names

    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, HEART_ANCHOR)
    heart_poems = {h.poem_id for h in heart_hits}
    sample = calibration_sample(
        [type("H", (), {"poem_id": pid})() for pid in all_poem_ids],
        sample_size=15, seed=0,
    )
    sample_ids = [h.poem_id for h in sample]
    accepted_in_sample = {pid for pid in sample_ids if pid in heart_poems}
    est = estimate_incidence(all_poem_ids, sample_ids, accepted_in_sample, seed=0)
    assert est.sample_size < est.population_size  # not a full census
    assert est.wilson_hi > est.wilson_lo  # a genuine interval, not a collapsed point


def test_estimate_reduces_to_but_never_replaces_exact_census():
    """The 100%-sample special case (already covered in test_census.py) is
    reasserted here as an Appendix-A framing: even where the estimate
    happens to equal the exact value, the function still returns an
    EstimatedIncidence with an interval, never an unqualified figure."""
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, HEART_ANCHOR)
    heart_poems = {h.poem_id for h in heart_hits}
    est = estimate_incidence(all_poem_ids, all_poem_ids, heart_poems, seed=0)
    assert est.point_estimate == len(heart_poems) / len(all_poem_ids)
    assert hasattr(est, "wilson_lo") and hasattr(est, "wilson_hi")


# --- "conditional association != causation" ---

def test_conditional_association_never_phrased_as_causation():
    from dataclasses import fields
    field_names = [f.name for f in fields(ConditionalAssociation)]
    assert not any("cause" in name.lower() for name in field_names)
    doc = (conditional_association.__doc__ or "").lower()
    assert "causes" not in doc and "caused by" not in doc


# --- ablation retention never phrased as an explanation ---

def test_ablation_retention_never_phrased_as_caused_by():
    """Appendix A doesn't name ablation directly, but §31 (ablation.py's
    own docstring) draws the same 'conditional association != causation'
    line around retention ratios: a retention number describes what
    remained, not why."""
    from dataclasses import fields
    field_names = [f.name for f in fields(AblationRetention)]
    assert not any("cause" in name.lower() for name in field_names)
    module_doc = (ablation_module.__doc__ or "").lower()
    function_doc = (ablation_retention.__doc__ or "").lower()
    assert "caused by" not in module_doc
    assert "caused by" not in function_doc


# --- "high frequency != wide dispersion" ---

def test_high_hit_count_does_not_imply_wide_dispersion():
    """Appendix A: 'high frequency != wide dispersion'. On this fixture,
    mirror's 5 accepted hits are concentrated 4/5 in a single poet
    (sample1, DP > 0.5 -- see test_metrics.py) rather than evenly spread;
    a Dispersion result that only ever reported a total count would hide
    this. Structural guard: Dispersion always carries raw counts and
    partition sizes, never a bare aggregate figure standing in for spread."""
    from ontograph.metrics import concentration, gries_dp
    _, mirror_hits, _, accepted_mirror, _ = _setup()
    records = scan_corpus(FIXTURE_ROOT)
    accepted_hits = [h for h in mirror_hits if h.poem_id in accepted_mirror]
    d = gries_dp(accepted_hits, records)
    c = concentration(accepted_hits, records)
    assert d.raw_counts_by_poet and d.partition_sizes_by_poet
    assert c.top_share > 0.5  # concentrated, not evenly dispersed
    assert d.value > 0.5  # the fixture's actual dispersion is high, not low
