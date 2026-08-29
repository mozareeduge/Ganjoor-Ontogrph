"""Tests for ontograph.census (ledger rows P2.1-P2.4)."""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import (
    accepted_poem_ids,
    ambiguous_only_poem_ids,
    assessed_full_prevalence,
    calibration_sample,
    estimate_incidence,
    open_context_ladder,
)
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "manifest.json", encoding="utf-8") as f:
    GROUND_TRUTH = json.load(f)["_fixture_ground_truth"]
with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
HEART_ANCHOR = [LexicalAnchor(object_address="heart", form="دل")]


def _mirror_hits():
    return census(scan_corpus(FIXTURE_ROOT), MIRROR_ANCHORS)


def _mirror_assessments():
    return {int(k): v for k, v in CANON["mirror"].items()}


# --- P2.1 ---

def test_calibration_sample_reproducible_with_same_seed():
    hits = _mirror_hits()
    assert len(hits) == 7
    a = calibration_sample(hits, sample_size=5, seed=20260827)
    b = calibration_sample(hits, sample_size=5, seed=20260827)
    assert [h.poem_id for h in a] == [h.poem_id for h in b]
    assert len(a) == 5


def test_calibration_sample_different_seeds_can_differ():
    hits = _mirror_hits()
    a = calibration_sample(hits, sample_size=5, seed=1)
    b = calibration_sample(hits, sample_size=5, seed=2)
    assert [h.poem_id for h in a] != [h.poem_id for h in b] or len(hits) <= 5


def test_context_ladder_shows_couplet_not_just_match():
    hits = _mirror_hits()
    hit = next(h for h in hits if h.poem_id == 9101)
    records = {r.poem_id: r for r in scan_corpus(FIXTURE_ROOT)}
    ctx = open_context_ladder(hit, records[9101].path)
    assert ctx["match"] == "آینه"
    assert len(ctx["couplet"]) == 2  # Right + Left of couplet 0


# --- P2.2 ---

def test_mirror_assessment_counts_5_accepted_1_ambiguous_1_rejected():
    hits = _mirror_hits()
    assessments = _mirror_assessments()
    accepted = accepted_poem_ids(hits, assessments)
    assert len(accepted) == 5
    ambiguous = {pid for pid, dec in assessments.items() if dec == "ambiguous"}
    rejected = {pid for pid, dec in assessments.items() if dec == "rejected"}
    assert ambiguous == {9105}
    assert rejected == {9106}


# --- P2.3 ---

def test_assessed_full_prevalence_denominator_is_27_not_26():
    hits = _mirror_hits()
    assessments = _mirror_assessments()
    all_poem_ids = {r.poem_id for r in scan_corpus(FIXTURE_ROOT)}
    prevalence = assessed_full_prevalence(all_poem_ids, hits, assessments)
    assert prevalence.denominator == 27
    assert prevalence.numerator == 5
    assert prevalence.ambiguous_only_count == 1  # poem 9105
    assert f"{prevalence.numerator}/{prevalence.denominator}" == GROUND_TRUTH["assessed_level"]["mirror_prevalence_poem_scale"]


# --- P2.4: estimator, tested on HEART (41 hits, 11 poems) not the 7-hit mirror object ---

def test_estimator_wilson_interval_brackets_truth_across_seeds():
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, HEART_ANCHOR)
    heart_poems = {h.poem_id for h in heart_hits}
    assert len(heart_poems) == GROUND_TRUTH["heart_object"]["field_total_poems_with_heart"] == 11

    true_prevalence = len(heart_poems) / len(all_poem_ids)

    brackets = 0
    trials = 30
    for seed in range(trials):
        sample = calibration_sample(
            [type("H", (), {"poem_id": pid})() for pid in all_poem_ids],
            sample_size=15,  # >10% of 27 -> exercises the FPC branch
            seed=seed,
        )
        sample_ids = [h.poem_id for h in sample]
        accepted_in_sample = {pid for pid in sample_ids if pid in heart_poems}
        est = estimate_incidence(all_poem_ids, sample_ids, accepted_in_sample, seed=seed)
        assert est.fpc_applied is True  # 15/27 > 10%
        if est.wilson_lo <= true_prevalence <= est.wilson_hi:
            brackets += 1

    # measured independently at 200 seeds before fixing this threshold:
    # 194/200 = 0.97 -- so >=0.9 across this smaller 30-seed run is not a
    # coin flip away from failing, it is the expected behaviour.
    assert brackets / trials >= 0.9, f"only {brackets}/{trials} seeds bracketed truth"


def test_100_percent_sample_reduces_to_exact_point_estimate():
    """Sanity check the original (pre-review) P2.4 target as a special
    case, not the only case: at 100% sampling, estimate == census exactly."""
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, HEART_ANCHOR)
    heart_poems = {h.poem_id for h in heart_hits}
    est = estimate_incidence(all_poem_ids, all_poem_ids, heart_poems, seed=0)
    assert est.point_estimate == len(heart_poems) / len(all_poem_ids)
