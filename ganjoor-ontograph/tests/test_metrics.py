"""Tests for ontograph.metrics (ledger rows P3.1, P3.2)."""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import accepted_poem_ids, assessed_full_prevalence
from ontograph.field import scan_corpus
from ontograph.metrics import concentration, gries_dp, spread, unit_incidence

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]


def _setup():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    accepted = accepted_poem_ids(hits, assessments)
    accepted_hits = [h for h in hits if h.poem_id in accepted]
    return records, hits, assessments, accepted, accepted_hits


def test_prevalence_is_5_of_27_matching_p23():
    records, hits, assessments, accepted, _ = _setup()
    all_poem_ids = {r.poem_id for r in records}
    prev = assessed_full_prevalence(all_poem_ids, hits, assessments)
    assert prev.numerator == 5 and prev.denominator == 27


def test_unit_incidence_binary():
    _, _, _, accepted, _ = _setup()
    assert unit_incidence(9101, accepted) == 1
    assert unit_incidence(9202, accepted) == 0  # unrelated filler poem


def test_spread_across_two_poets():
    records, _, _, accepted, _ = _setup()
    s = spread(accepted, records)
    assert s.distinct_poems == 5
    assert s.distinct_poets == 2  # sample1 and sample2
    assert s.total_poems == 27
    assert s.total_poets == 4


def test_concentration_top_poet_is_sample1_at_80_percent():
    records, _, _, _, accepted_hits = _setup()
    c = concentration(accepted_hits, records)
    assert c.total_hits == 5
    assert c.top_poet == "sample1"
    assert c.top_share == 4 / 5
    assert c.counts_by_poet == {"sample1": 4, "sample2": 1}


def test_dispersion_is_concentrated_and_carries_raw_counts():
    records, _, _, _, accepted_hits = _setup()
    d = gries_dp(accepted_hits, records)
    assert d.measure == "gries-2008-dp"
    assert 0.5 < d.value < 0.6  # concentrated in one poet relative to corpus size
    # never a bare float -- raw counts and partition sizes travel with it
    assert d.raw_counts_by_poet == {"sample1": 4, "sample2": 1}
    assert d.partition_sizes_by_poet == {"sample1": 7, "sample2": 5, "sample3": 5, "sample4": 10}
