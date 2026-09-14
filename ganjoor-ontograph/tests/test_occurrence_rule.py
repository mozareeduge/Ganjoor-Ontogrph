"""Tests for ontograph.census's validated-rule route (ledger row P7.5,
spec §70 route 2)."""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import apply_occurrence_rule, validate_rule_against_reviewed_material
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]


def _mirror_hits():
    return census(scan_corpus(FIXTURE_ROOT), MIRROR_ANCHORS)


def test_rule_rejects_the_two_figurative_hits_and_accepts_the_rest():
    decisions = apply_occurrence_rule(_mirror_hits())
    by_poem = {d.poem_id: d for d in decisions}
    assert by_poem[9105].decision == "rejected" and "دل" in by_poem[9105].matched_stoplist_terms
    assert by_poem[9106].decision == "rejected" and "خاطره" in by_poem[9106].matched_stoplist_terms
    for pid in (9101, 9102, 9103, 9104, 9201):
        assert by_poem[pid].decision == "accepted"
        assert by_poem[pid].matched_stoplist_terms == frozenset()


def test_rule_correctly_excludes_the_mirror_rust_divergence_case_9106():
    """The specific demonstration P7.5 requires: the rule must be shown
    to correctly exclude poem 9106 (the anchor-level mirror/rust
    co-incidence that is NOT assessed-level co-incidence, per
    EXTERNAL_REVIEW.md Finding 1) from acceptance."""
    decisions = apply_occurrence_rule(_mirror_hits())
    assert next(d for d in decisions if d.poem_id == 9106).decision == "rejected"


def test_rule_agrees_with_human_review_on_every_reviewed_hit():
    decisions = apply_occurrence_rule(_mirror_hits())
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    report = validate_rule_against_reviewed_material(decisions, assessments)
    assert report.total_reviewed == 7
    assert report.agreement_count == 7  # perfect agreement on this fixture -- not assumed to generalize
    assert report.disagreement_poem_ids == frozenset()
