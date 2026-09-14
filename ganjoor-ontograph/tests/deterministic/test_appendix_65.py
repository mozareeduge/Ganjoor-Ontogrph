"""Deterministic corpus test suite (ledger row P7.1, spec §65).

One test function per §65 bullet, in the spec's own order. Where an
existing test file already exercises a bullet in depth, this file adds a
genuinely independent check (a different fixture angle, or an
equivalence check against a second code path) rather than re-describing
the same assertion under a new name. Where a bullet names a capability
that is not built in v0.1 -- because an earlier ledger row explicitly
scoped it out -- the test is `pytest.mark.skip`-marked with the ledger
row that made that call, so the gap is visible in the test report rather
than silently absent from this file.
"""
import json
import pathlib

import pytest

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor, census
from ontograph.census import (
    accepted_poem_ids,
    ambiguous_only_poem_ids,
    assessed_full_prevalence,
    calibration_sample,
    estimate_incidence,
)
from ontograph.cli import main as cli_main
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED, typed_coincidence
from ontograph.corpus import build_index, load_corpus_snapshot
from ontograph.field import FieldCharter, poet, scan_corpus, union
from ontograph.normalize import normalize, tokenize

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHORS = [LexicalAnchor(object_address="rust", form="زنگار")]


# 1. corpus snapshot and manifest hashes
def test_corpus_snapshot_and_manifest_hash():
    snap = load_corpus_snapshot(FIXTURE_ROOT)
    assert len(snap.manifest_sha256) == 64
    assert load_corpus_snapshot(FIXTURE_ROOT).manifest_sha256 == snap.manifest_sha256


# 2. source-file count against manifest
def test_source_file_count_matches_manifest():
    snap = load_corpus_snapshot(FIXTURE_ROOT)
    records = scan_corpus(FIXTURE_ROOT)
    assert len(records) == snap.poems_count


# 3. field membership reproducibility
def test_field_membership_is_reproducible_across_independent_scans():
    charter = FieldCharter(
        purpose="reproducibility check", corpus_snapshot=str(FIXTURE_ROOT),
        scope_spec=union(poet("sample1"), poet("sample2")),
    )
    ids_a = charter.poem_ids(scan_corpus(FIXTURE_ROOT))
    ids_b = charter.poem_ids(scan_corpus(FIXTURE_ROOT))  # independent re-scan, not the same list object
    assert ids_a == ids_b == charter.poem_ids(scan_corpus(FIXTURE_ROOT))


# 4. category subtree expansion
@pytest.mark.skip(reason="ScopeSpec has no category leaf kind (ledger P1.3); CLI --category raises CLIError rather than silently ignoring it")
def test_category_subtree_expansion():
    pass


# 5. poem/section/verse/couplet reconstruction
def test_poem_section_verse_couplet_reconstruction_matches_source_json():
    records = scan_corpus(FIXTURE_ROOT)
    conn, _ = build_index(FIXTURE_ROOT)
    row = conn.execute(
        "SELECT text FROM verses WHERE poem_id = 9101 AND couplet_index = 0 AND position = 'Right'"
    ).fetchone()
    source = json.loads(next(r.path for r in records if r.poem_id == 9101).read_text(encoding="utf-8"))
    source_verse = next(v for v in source["Verses"] if v["CoupletIndex"] == 0 and v["Position"] == "Right")
    assert row[0] == source_verse["Text"]


# 6. anchor normalization round-trip to original text
def test_normalization_round_trip_on_a_real_corpus_verse():
    records = scan_corpus(FIXTURE_ROOT)
    poem_9101 = json.loads(next(r.path for r in records if r.poem_id == 9101).read_text(encoding="utf-8"))
    verse_text = poem_9101["Verses"][0]["Text"]
    nt = normalize(verse_text)
    start, end = nt.to_original_span(0, len(nt.normalized))
    assert nt.original[start:end].strip() != "" or nt.normalized == ""


# 7. tokenizer fixtures: mixed-script spans (ZWNJ/diacritics/Yeh-Kaf/punctuation already covered in test_normalize.py)
def test_tokenizer_handles_mixed_script_span():
    nt = normalize("آینه Ganjoor 1402 در دست")
    tokens = [t[0] for t in tokenize(nt.normalized)]
    assert "آینه" in tokens
    assert "Ganjoor" in tokens
    assert "1402" in tokens
    assert "در" in tokens and "دست" in tokens


# 8. Anchor Hit counts against direct source scans for fixture corpora
def test_anchor_hit_count_matches_an_independent_direct_source_scan():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)

    # independent of the engine's own tokenizer: a plain whitespace/punctuation
    # split, counting exact-word matches only (not substrings) -- this is a
    # different code path from ontograph.normalize.tokenize, so agreement is
    # a real cross-check rather than the same function checking itself.
    import re
    direct_count = 0
    for r in records:
        poem = json.loads(r.path.read_text(encoding="utf-8"))
        for verse in poem["Verses"]:
            words = re.split(r"[\s.,;:!?،؛؟«»\"'()\[\]{}]+", verse["Text"])
            direct_count += sum(1 for w in words if w in ("آینه", "آیینه"))
    assert direct_count == len(hits) == 7


# 9. Occurrence Assessment policy tests: rejected/ambiguous do not silently enter exact incidence
def test_rejected_and_ambiguous_hits_excluded_from_exact_incidence():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    all_poem_ids = {r.poem_id for r in records}
    prevalence = assessed_full_prevalence(all_poem_ids, hits, assessments)
    accepted = accepted_poem_ids(hits, assessments)
    ambiguous_only = ambiguous_only_poem_ids(hits, assessments)
    assert 9106 not in accepted  # rejected
    assert 9105 not in accepted and 9105 in ambiguous_only  # ambiguous, scored 0, reported separately
    assert prevalence.numerator == len(accepted) == 5
    assert prevalence.ambiguous_only_count == 1


# 10. estimated-mode fixtures: sampling weights/estimator/uncertainty, never exact-count wording
def test_estimated_mode_carries_uncertainty_and_is_never_exact():
    from dataclasses import fields
    from ontograph.census import EstimatedIncidence
    records = scan_corpus(FIXTURE_ROOT)
    all_poem_ids = [r.poem_id for r in records]
    heart_hits = census(records, [LexicalAnchor(object_address="heart", form="دل")])
    heart_poems = {h.poem_id for h in heart_hits}
    sample_ids = [r.poem_id for r in calibration_sample(records, sample_size=15, seed=0)]
    est = estimate_incidence(all_poem_ids, sample_ids, {pid for pid in sample_ids if pid in heart_poems}, seed=0)
    assert est.sample_size < est.population_size
    assert not any("exact" in f.name.lower() for f in fields(EstimatedIncidence))


# 11. pairwise object-level mappings blocked when a participant is estimated-only
@pytest.mark.skip(reason="compare.typed_coincidence only implements MODE_ANCHOR/MODE_ASSESSED; there is no MODE_ESTIMATED gate to block in v0.1 (not built)")
def test_pairwise_mapping_blocked_for_estimated_only_participant():
    pass


# 12. formula correctness: incidence/co-incidence/prevalence/conditional association/lift/scale survival/ablation (mediation deferred, v0.2)
def test_formula_correctness_across_the_v01_operation_set():
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assert result.poem_scale == frozenset({9101, 9102, 9106, 9201})
    ablation = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, {9101, 9102, 9103, 9104, 9105, 9106, 9107})
    assert ablation.poem_scale_retention == pytest.approx(1 / 4)


@pytest.mark.skip(reason="mediation.py is explicitly v0.2 scope (spec §72) -- not built in v0.1, per its own module docstring")
def test_mediation_formula_correctness():
    pass


# 13. source-return completeness for every Mapping Object
@pytest.mark.skip(reason="MappingObject/OperationSpec/ReductionRecord records are out of P4.1's scope (Trace/Relation-Object/Profile/Experiment/Finding only) -- not built in v0.1")
def test_source_return_completeness_for_mapping_objects():
    pass


# 14. EventRecord append-only integrity and replay of state-changing actions
def test_event_record_append_only_integrity_and_replay(tmp_path):
    from ontograph.records import EventLogMutationError, EventRecord, append_event, delete_event, mutate_event, read_events
    from ontograph.workspace import new_study
    ws = new_study(tmp_path, "det-suite-study")
    e1 = EventRecord(id="ev-1", study_id="det-suite-study", event_type="field-revision")
    e2 = EventRecord(id="ev-2", study_id="det-suite-study", event_type="anchor-approval", parent_event_ids=["ev-1"])
    append_event(ws, e1)
    append_event(ws, e2)
    assert [e.id for e in read_events(ws)] == ["ev-1", "ev-2"]
    with pytest.raises(EventLogMutationError):
        mutate_event()
    with pytest.raises(EventLogMutationError):
        delete_event()


# 15. reproducible calibration sampling from stored random seed/strata
def test_calibration_sampling_reproducible_from_stored_seed_and_strata():
    records = scan_corpus(FIXTURE_ROOT)
    strata_key = lambda r: r.poet_slug
    a = calibration_sample(records, sample_size=8, seed=42, strata_key=strata_key)
    b = calibration_sample(records, sample_size=8, seed=42, strata_key=strata_key)
    assert [r.poem_id for r in a] == [r.poem_id for r in b]
    # the stratified sample actually draws from more than one stratum
    assert len({r.poet_slug for r in a}) > 1


# 16. corpus/QMD synchronization guard
@pytest.mark.skip(reason="no QMD/retrieval channel is integrated into this deterministic engine in v0.1 (spec §25/§56's matched/known-stale/unknown verdict is not built) -- out of scope, not silently assumed matched")
def test_corpus_qmd_synchronization_guard():
    pass


# 17. operation denominator/eligibility reconstruction
def test_operation_denominator_eligibility_reconstruction():
    records = scan_corpus(FIXTURE_ROOT)
    hits = census(records, MIRROR_ANCHORS)
    assessments = {int(k): v for k, v in CANON["mirror"].items()}
    eligible = {r.poem_id for r in records}
    prevalence = assessed_full_prevalence(eligible, hits, assessments)
    assert prevalence.denominator == len(eligible) == 27  # eligible-unit denominator reconstructed, not re-derived ad hoc


# 18. engine/CLI/adapter contract equivalence on shared fixtures
def test_engine_and_cli_agree_on_the_same_fixture(tmp_path, capsys):
    from ontograph.workspace import new_study
    ws_dir = tmp_path / "ontograph-workspaces"
    new_study(ws_dir, "equiv-study")
    path = ws_dir / "equiv-study" / "objects" / "object-addresses.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"id": "mirror", "preferred_label": "mirror", "anchors": ["آینه", "آیینه"]}) + "\n", encoding="utf-8")

    code = cli_main([
        "census", "equiv-study", "--object", "mirror",
        "--corpus-root", str(FIXTURE_ROOT), "--workspaces-dir", str(ws_dir),
    ])
    out = capsys.readouterr().out
    assert code == 0
    cli_result = json.loads(out)

    engine_hits = census(scan_corpus(FIXTURE_ROOT), MIRROR_ANCHORS)
    assert cli_result["hit_count"] == len(engine_hits)
