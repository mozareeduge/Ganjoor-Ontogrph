"""Epistemic contract test suite (ledger row P7.2, spec §66).

One test per §66 "does NOT" scenario, in the spec's own order. As in
tests/deterministic/test_appendix_65.py, a bullet naming a capability
that an earlier ledger row explicitly scoped out of v0.1 is
`pytest.mark.skip`-marked with that row named, rather than silently
absent.
"""
import json
import pathlib
from dataclasses import fields

import pytest

from ontograph.anchors import AnchorHit, LexicalAnchor, census
from ontograph.census import EstimatedIncidence, accepted_poem_ids, assessed_full_prevalence, calibration_sample, estimate_incidence
from ontograph.compare import ConditionalAssociation, conditional_association
from ontograph.field import FieldCharter, poet_life_proxy_charter, scan_corpus
from ontograph.metrics import Spread, unit_incidence
from ontograph.normalize import NormalizedText, normalize
from ontograph.records import ProfileRecord, TraceRecord, read_records, write_record
from ontograph.workspace import new_study

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]


# 1. lexical anchor / raw Anchor Hit is not automatically settled object occurrence
def test_anchor_hit_never_asserts_settled_occurrence():
    hit_fields = {f.name for f in fields(AnchorHit)}
    assert not any("occur" in name.lower() for name in hit_fields)  # no "occurred"/"is_occurrence" field
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    # a rejected hit (9106) is still just an AnchorHit here -- census() has no
    # concept of "settled", only apply_assessments()/accepted_poem_ids() do
    assert any(h.poem_id == 9106 for h in hits)


# 2. candidate companion not promoted to Object Address without a decision
@pytest.mark.skip(reason="candidate-anchor promotion workflow (spec §28.4) has no dedicated gate in v0.1 -- object-address registration in this phase is a flat CLI/records write, not yet a reviewed-decision pipeline")
def test_candidate_companion_promotion_requires_a_decision():
    pass


# 3. co-incidence is never labelled causation/influence
def test_coincidence_never_labelled_causation_or_influence():
    # field names stay pure conditional-probability language; the docstring
    # legitimately says "not causation or ... influence" as a caller
    # warning, so the guard checks labelling (field names), not the prose
    assoc_fields = {f.name for f in fields(ConditionalAssociation)}
    assert not any("cause" in n.lower() or "influence" in n.lower() for n in assoc_fields)


# 4. a chronological proxy is never called a poem date
def test_chronological_proxy_never_presented_as_a_poem_date():
    charter = poet_life_proxy_charter(FIXTURE_ROOT, 700, 800)
    assert charter.derived is True
    assert charter.derivation_rule is not None and "poet-life" in charter.derivation_rule
    charter_fields = {f.name for f in fields(FieldCharter)}
    assert not any("date" in n.lower() for n in charter_fields)


# 5. category title is not called a genre unless the mapping is declared
@pytest.mark.skip(reason="no category/genre mapping concept exists in v0.1 (ScopeSpec has no category leaf, ledger P1.3) -- there is nothing yet that could silently call a category a genre")
def test_category_title_not_called_genre_without_declared_mapping():
    pass


# 6. zero count is not converted into ontological absence
def test_zero_count_is_a_count_not_an_absence_claim():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    sample3_poems = {r.poem_id for r in records if r.poet_slug == "sample3"}
    hit_poems = {h.poem_id for h in hits}
    assert not (sample3_poems & hit_poems)  # zero_incidence_control_poet, per manifest ground truth
    for pid in sample3_poems:
        assert unit_incidence(pid, hit_poems) == 0  # a count of 0, not a field claiming absence
    spread_fields = {f.name for f in fields(Spread)}
    assert not any("absen" in n.lower() for n in spread_fields)


# 7. textual and Relation-Object networks are not merged into one centrality score
@pytest.mark.skip(reason="no graph/centrality module exists in v0.1 (spec §33 multiplex graph diagnostics is not built) -- there is no centrality score to have merged networks in the first place")
def test_no_merged_centrality_score_across_networks():
    pass


# 8. a scholarly claim is not created directly from an AI proposal
@pytest.mark.skip(reason="ClaimRecord (spec §55) is out of P4.1's scope (Trace/Relation-Object/Profile/Experiment/Finding only) -- not built in v0.1, so there is no claim-creation path to guard yet; the nearest built guard is ProfileRecord's ai-summary provenance requirement (P4.2), which is a different record type")
def test_claim_not_created_directly_from_ai_proposal():
    pass


# 9. normalization or field reduction is never hidden
def test_normalization_and_field_reduction_are_always_visible():
    nt = normalize("آینه در دست")
    nt_fields = {f.name for f in fields(NormalizedText)}
    assert "profile_version" in nt_fields and "strip_diacritics" in nt_fields
    charter = FieldCharter(purpose="x", corpus_snapshot=str(FIXTURE_ROOT), scope_spec=None)
    charter_fields = {f.name for f in fields(FieldCharter)}
    assert "derived" in charter_fields and "derivation_rule" in charter_fields


# 10. a metric is never produced without source return
def test_metric_always_carries_source_return_fields():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    hit_fields = {f.name for f in fields(AnchorHit)}
    assert {"poem_id", "couplet_index", "original_text", "normalized_text"} <= hit_fields
    assert all(h.original_text for h in hits)  # every hit actually carries source text, not just a count


# 11. an estimate is never presented as a complete census
def test_estimate_never_presented_as_complete_census():
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, [LexicalAnchor(object_address="heart", form="دل")])
    heart_poems = {h.poem_id for h in heart_hits}
    sample_ids = [r.poem_id for r in calibration_sample(records, sample_size=15, seed=0)]
    est = estimate_incidence(all_poem_ids, sample_ids, {p for p in sample_ids if p in heart_poems}, seed=0)
    assert est.sample_size < est.population_size  # a real estimate, not a full census
    est_fields = {f.name for f in fields(EstimatedIncidence)}
    assert "sample_size" in est_fields and "population_size" in est_fields  # incompleteness is visible in the result itself


# 12. a stale retrieval snapshot is never combined with a newer deterministic corpus silently
@pytest.mark.skip(reason="no QMD/retrieval channel is integrated in v0.1 (same gap as the deterministic suite's item 16) -- there is no second snapshot to silently combine with yet")
def test_stale_retrieval_snapshot_combination_guard():
    pass


# 13. earlier Profiles are never overwritten when conditions change
def test_profiles_are_never_overwritten_only_appended(tmp_path):
    ws = new_study(tmp_path, "profile-history-study")
    p1 = ProfileRecord(id="profile-1", addressed_object_or_relation="mirror", source_or_witness="poem 9101", access_apparatus="original-text")
    p2 = ProfileRecord(id="profile-1-revised", addressed_object_or_relation="mirror", source_or_witness="poem 9101", access_apparatus="original-text", uncertainty="revised after recalibration")
    write_record(ws, "profile", p1)
    write_record(ws, "profile", p2)
    stored = read_records(ws, "profile")
    assert stored == [p1, p2]  # p1 is still there, not clobbered by p2


# 14. rejected traces are never deleted from research history
def test_rejected_traces_are_never_deleted(tmp_path):
    import ontograph.records as records_module
    assert not hasattr(records_module, "delete_record")  # no delete-by-key API exists on the records module surface at all

    ws = new_study(tmp_path, "trace-history-study")
    rejected = TraceRecord(id="trace-1", what_appeared="a false lead", status="residue", created_by="human")
    write_record(ws, "trace", rejected)
    assert read_records(ws, "trace") == [rejected]  # still present, exactly as written -- nothing removed it
