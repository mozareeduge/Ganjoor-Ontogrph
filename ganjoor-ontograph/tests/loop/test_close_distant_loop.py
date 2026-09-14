"""Close-distant loop tests A-F (ledger row P7.3, spec §67).

The mini-ganjoor fixture IS the "crafted miniature corpus where the true
distribution is known" spec §67 asks for -- it was built with exactly
these pressure cases in mind (poem 9102 for scale collapse, 9105/9106 for
lexical ambiguity, sample1's dominance for ablation false centre), so
these tests reuse it directly rather than building six more fixtures.
"""
import json
import pathlib

import pytest

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor, census
from ontograph.census import accepted_poem_ids, calibration_sample, open_context_ladder
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED, relation_scale_profile, typed_coincidence
from ontograph.field import scan_corpus
from ontograph.metrics import concentration, gries_dp, spread
from ontograph.records import TraceRecord, read_records, write_record
from ontograph.workspace import new_study

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHORS = [LexicalAnchor(object_address="rust", form="زنگار")]


def _mirror_setup():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    accepted = accepted_poem_ids(hits, assessments)
    accepted_hits = [h for h in hits if h.poem_id in accepted]
    return records, hits, assessments, accepted, accepted_hits


# --- Test A: concentrated frequency ---

def test_a_concentrated_frequency_is_not_described_as_broadly_recurrent():
    records, _, _, _, accepted_hits = _mirror_setup()
    s = spread({h.poem_id for h in accepted_hits}, records)
    c = concentration(accepted_hits, records)
    d = gries_dp(accepted_hits, records)
    # spread alone (2 of 4 poets touched) could misleadingly read as "fairly
    # broad"; concentration/dispersion must be consulted alongside it, not
    # silently dropped once a spread number exists
    assert s.distinct_poets == 2
    assert c.top_share == pytest.approx(4 / 5)  # 4 of 5 accepted hits in one poet
    assert d.value > 0.5  # concentrated, not evenly dispersed
    assert d.raw_counts_by_poet and d.partition_sizes_by_poet  # raw counts always travel with the ratio


# --- Test B: scale collapse ---

def test_b_scale_collapse_is_visible_and_both_classes_source_return():
    records = scan_corpus(FIXTURE_ROOT)
    records_by_id = {r.poem_id: r for r in records}
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    profile = relation_scale_profile(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assert profile.poem_scale == 4
    assert profile.couplet_scale == 3
    assert profile.poem_only_poem_ids == frozenset({9102})  # co-occurs in-poem, never in-couplet

    # both classes of example must be source-returnable: the poem-only case
    # (9102) and a genuine couplet-level case (9101)
    mirror_hit_9102 = next(h for h in mirror_hits if h.poem_id == 9102)
    mirror_hit_9101 = next(h for h in mirror_hits if h.poem_id == 9101)
    ctx_9102 = open_context_ladder(mirror_hit_9102, records_by_id[9102].path)
    ctx_9101 = open_context_ladder(mirror_hit_9101, records_by_id[9101].path)
    assert ctx_9102["poem_id"] == 9102 and ctx_9101["poem_id"] == 9101


# --- Test C: lexical ambiguity ---

def test_c_lexical_ambiguity_lets_researcher_narrow_before_field_wide_interpretation():
    records, hits, assessments, accepted, _ = _mirror_setup()
    records_by_id = {r.poem_id: r for r in records}
    ambiguous_hit = next(h for h in hits if h.poem_id == 9105)
    rejected_hit = next(h for h in hits if h.poem_id == 9106)
    ctx_ambiguous = open_context_ladder(ambiguous_hit, records_by_id[9105].path)
    ctx_rejected = open_context_ladder(rejected_hit, records_by_id[9106].path)
    assert ctx_ambiguous["poem_id"] == 9105 and ctx_rejected["poem_id"] == 9106

    # field-wide interpretation (accepted incidence) excludes both once the
    # researcher has reviewed and decided, rather than counting every anchor
    # match as settled presence
    all_poem_ids = {r.poem_id for r in records}
    raw_anchor_poems = {h.poem_id for h in hits}
    assert 9105 in raw_anchor_poems and 9106 in raw_anchor_poems  # anchor still matched
    assert 9105 not in accepted and 9106 not in accepted  # excluded once assessed


# --- Test D: ablation false centre ---

def test_d_ablation_exposes_the_single_poet_dependence():
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    before = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    result = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, {9101, 9102, 9103, 9104, 9105, 9106, 9107})
    assert len(before.poem_scale) == 4
    assert result.remaining_poem_scale == 1  # only 9201 survives -- sample1 supplied the "strength"
    assert result.poem_scale_retention == pytest.approx(1 / 4)


# --- Test E: local close-reading insight ---

def test_e_recurrence_test_does_not_rewrite_a_local_reading(tmp_path):
    ws = new_study(tmp_path, "local-insight-study")
    trace = TraceRecord(
        id="trace-local-9101", initiating_encounters=["poem:9101#couplet:0"],
        what_appeared="mirror and rust share couplet 0 of poem 9101",
        candidate_descriptions=["literal material pairing"], status="active", created_by="human",
    )
    write_record(ws, "trace", trace)

    # testing corpus-wide recurrence is a separate, non-destructive read
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assert 9101 in result.poem_scale  # the relation does recur elsewhere in the field

    # the local trace is untouched by having run that field-wide test
    assert read_records(ws, "trace") == [trace]


# --- Test F: research-made mediation ---

@pytest.mark.xfail(
    reason="Mediational Incidence / research-attention-vs-corpus-recurrence "
           "distinction (spec §32, §72) is explicitly v0.2 scope -- "
           "mediation.py is an unimplemented stub in v0.1, per its own "
           "module docstring and IMPLEMENTATION_LEDGER.md P3.9's note",
    strict=True,
)
def test_f_research_made_mediation_distinguishes_recurrence_from_attention():
    from ontograph.mediation import mediation_incidence  # does not exist yet
    mediation_incidence()
