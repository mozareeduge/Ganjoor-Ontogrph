"""Ledger row W01 (Amendment §19.3): InquiryCatalog and InquiryReview
schemas + isolated candidate stores.

Discriminating targets:

1. InquiryCatalog round-trips: situation/snapshot/field/scope IDs,
   parameters, limitations, and candidates (kinds: seed-object,
   lexical-anchor, authored-contrast, non-object-note, lexical-neighbor),
   each with proposer type/id + rationale, and lexical candidates with
   support status (supported|unsupported|not-applicable) + counts +
   evidence refs.
2. InquiryReview round-trips: decisions accept|accept-unsupported|
   reject|defer|revise|split with stable candidate id, human actor,
   rationale, receipt, predecessor, outputs.
3. Candidate stores are INVISIBLE to the active-object/anchor loaders —
   a promoted object lives in the normal object-addresses store; a
   candidate that was never reviewed never appears there.
4. Generic `record add` refuses machine-managed inquiry/review stores.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.inquiry import (
    CandidateEvidenceRef,
    InquiryCandidate,
    InquiryCatalog,
    InquiryReview,
    persist_catalog,
    persist_review,
    read_catalogs,
    read_reviews,
)


def _evidence() -> CandidateEvidenceRef:
    return CandidateEvidenceRef(
        path="poets/ferdousi/shahname/kkavoos/sh4.json", poem_id=1433,
        verse_order=30, couplet_index=15, match_span=[0, 3],
        corpus_snapshot_id="cs1-test",
    )


def _candidate(**over) -> InquiryCandidate:
    base = dict(
        candidate_id="cand-lasso", kind="lexical-anchor",
        form="کمند", proposer_type="human", proposer_id="mz",
        rationale="rope trick is the signature", support_status="supported",
        hit_count=12, poem_count=9, poet_count=5,
        evidence=[_evidence()],
    )
    base.update(over)
    return InquiryCandidate(**base)


def _catalog(**over) -> InquiryCatalog:
    base = dict(
        study_id="s", situation_id="rs-1", corpus_snapshot_id="cs1-test",
        field_id="field-1", scope_spec={"kind": "all"},
        parameters={"probe": "v1"}, limitations=["raw retrieval order only"],
        candidates=[_candidate()],
    )
    base.update(over)
    return InquiryCatalog(**base)


def test_catalog_round_trip(tmp_path: Path) -> None:
    persist_catalog(tmp_path, _catalog())
    loaded = read_catalogs(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].candidates[0].candidate_id == "cand-lasso"
    assert loaded[0].candidates[0].support_status == "supported"
    assert loaded[0].candidates[0].evidence[0].poem_id == 1433
    assert loaded[0].id.startswith("ic-")


def test_candidate_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _candidate(kind="invented-kind")
    with pytest.raises(ValueError):
        _candidate(support_status="assumed")  # never silently upgraded
    with pytest.raises(ValueError):
        _candidate(proposer_type="agent", proposer_id="")  # attribution required
    with pytest.raises(ValueError):
        _candidate(support_status="supported", evidence=[])  # supported needs evidence
    assert read_catalogs(tmp_path) == []


def test_review_round_trip_and_statuses(tmp_path: Path) -> None:
    persist_catalog(tmp_path, _catalog())
    review = InquiryReview(
        catalog_id=read_catalogs(tmp_path)[0].id,
        situation_id="rs-1", candidate_id="cand-lasso",
        decision="accept", actor="mz", rationale="corpus-verified",
        receipt="human-confirm-1", outputs=["object:lasso", "anchor:کمند"],
    )
    persist_review(tmp_path, review)
    loaded = read_reviews(tmp_path)
    assert loaded[0].decision == "accept"
    assert loaded[0].actor == "mz"
    with pytest.raises(ValueError):
        InquiryReview(
            catalog_id="ic-x", situation_id="rs-1", candidate_id="c",
            decision="auto-accept",  # not in the decision space
            actor="mz", rationale="r", receipt="rc",
        )


def test_candidate_stores_invisible_to_active_loaders(tmp_path: Path) -> None:
    """A catalog candidate is NOT an object: the active object-addresses
    store knows nothing of it until a human review promotes it (W05)."""
    persist_catalog(tmp_path, _catalog())
    from ontograph.workspace import read_study_config  # sanity import

    objects_file = tmp_path / "objects" / "object-addresses.jsonl"
    assert not objects_file.exists(), "candidate store must not touch active objects"


def test_generic_record_add_refuses_inquiry_stores(tmp_path: Path) -> None:
    from ontograph.inquiry import generic_record_add_allowed

    assert generic_record_add_allowed("profile") is True
    assert generic_record_add_allowed("inquiry-catalogs") is False
    assert generic_record_add_allowed("inquiry-reviews") is False
    assert generic_record_add_allowed("occurrence-assessments") is False
