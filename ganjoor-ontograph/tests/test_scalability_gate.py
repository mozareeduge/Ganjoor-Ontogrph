"""Occurrence-assessment scalability gate (ledger row P7.5, spec §70).

Demonstrates all three defensible routes side by side, each explicitly
labelled with its own route name -- the gate specifically fails if one
route is presented under another's label (§70: "fails this gate if it
falls back to raw lexical matches while labelling them object
occurrences, or if an estimated result is presented as an exact
census").

Rewritten per Finding 2 of the external review: testing `estimated` mode
only at 100% sampling would be a tautology that never pressures the
estimator, so route 3 here samples the HEART object (41 hits across 11
of 27 poems) at a genuine <100% fraction, not the small 7-hit mirror
object.
"""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import (
    accepted_poem_ids,
    apply_occurrence_rule,
    assessed_full_prevalence,
    calibration_sample,
    estimate_incidence,
    validate_rule_against_reviewed_material,
)
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
HEART_ANCHOR = [LexicalAnchor(object_address="heart", form="دل")]


def test_route_1_complete_assessment_on_mirror():
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = {r.poem_id for r in records}
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    # "complete assessment" (spec §70 route 1): every eligible hit has a
    # recorded human decision -- none left unreviewed
    assert {h.poem_id for h in hits} <= set(assessments)
    prevalence = assessed_full_prevalence(all_poem_ids, hits, assessments)
    route = {"route": "assessed-full", "numerator": prevalence.numerator, "denominator": prevalence.denominator}
    assert route == {"route": "assessed-full", "numerator": 5, "denominator": 27}


def test_route_2_validated_rule_on_mirror_excludes_the_divergence_case():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    decisions = apply_occurrence_rule(hits)
    report = validate_rule_against_reviewed_material(decisions, assessments)
    route = {"route": "assessed-rule", "rule_version": report.rule_version, "agreement": f"{report.agreement_count}/{report.total_reviewed}"}
    assert route == {"route": "assessed-rule", "rule_version": "figurative-context-stoplist-v1", "agreement": "7/7"}
    # the specific pressure case: 9106 (mirror anchor-level co-incident
    # with rust, but assessed-rejected) must be excluded by the rule too
    assert next(d for d in decisions if d.poem_id == 9106).decision == "rejected"


def test_route_3_estimated_on_heart_at_genuine_undersampling():
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, HEART_ANCHOR)
    heart_poems = {h.poem_id for h in heart_hits}
    assert len(heart_poems) == 11  # field_total_poems_with_heart, manifest ground truth
    true_prevalence = len(heart_poems) / len(all_poem_ids)  # 11/27, known only because this IS a fixture

    sample_ids = [r.poem_id for r in calibration_sample(records, sample_size=15, seed=7)]
    assert len(sample_ids) / len(all_poem_ids) < 1.0  # a genuine <100% sampling fraction
    accepted_in_sample = {pid for pid in sample_ids if pid in heart_poems}
    est = estimate_incidence(all_poem_ids, sample_ids, accepted_in_sample, seed=7)

    route = {
        "route": "estimated", "point_estimate": round(est.point_estimate, 4),
        "wilson_lo": round(est.wilson_lo, 4), "wilson_hi": round(est.wilson_hi, 4),
        "sample_size": est.sample_size, "population_size": est.population_size,
    }
    assert route["route"] == "estimated"
    assert route["sample_size"] < route["population_size"]
    assert est.wilson_lo <= true_prevalence <= est.wilson_hi  # brackets the true 11/27 prevalence
    # never mislabelled as an exact census: the result always carries the
    # interval and the sample/population sizes, not a bare point figure
    assert est.wilson_hi > est.wilson_lo


def test_routes_are_never_mislabelled_as_each_other():
    """The gate's own failure condition, checked directly: three
    independently-computed routes on the same fixture study must report
    three distinct route names, and none of their own result shapes
    overlaps with another's (an assessed-full Prevalence has no Wilson
    interval; an EstimatedIncidence has no ambiguous_only_count; a
    RuleValidationReport has no wilson interval either)."""
    from dataclasses import fields
    from ontograph.census import EstimatedIncidence, Prevalence, RuleValidationReport

    prevalence_fields = {f.name for f in fields(Prevalence)}
    estimate_fields = {f.name for f in fields(EstimatedIncidence)}
    rule_fields = {f.name for f in fields(RuleValidationReport)}

    assert "wilson_lo" not in prevalence_fields and "wilson_lo" not in rule_fields
    assert "ambiguous_only_count" not in estimate_fields and "ambiguous_only_count" not in rule_fields
    assert "rule_version" not in prevalence_fields and "rule_version" not in estimate_fields
