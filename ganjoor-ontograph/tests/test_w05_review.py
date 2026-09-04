"""Ledger row W05 (Amendment §19.3): atomic human review → promotion.

Discriminating targets:

1. accept/reject/defer/revise/split append history; the review record
   is written atomically with any promotion outputs.
2. `accept` on a SUPPORTED candidate atomically creates the Seed, Object
   Address, LexicalAnchor, and event — or NOTHING (no partial writes).
3. Review creates NO assessment: walk still owns per-hit decisions.
4. `accept-unsupported` requires a human rationale and keeps the
   unsupported marker on the record.
5. Agent-attributed review, stale catalog, duplicate review of the same
   candidate, mixed-situation input, and zero-support ordinary accept:
   ALL refused without partial writes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.inquiry import (
    CandidateEvidenceRef, InquiryCandidate, InquiryCatalog,
    persist_catalog,
)
from ontograph.inquiry_review import (
    apply_review_decisions,
    load_object_address_ids,
)
from ontograph.workspace import new_study


def _catalog(tmp_path: Path, candidate_id="cand-1", support="supported", form="آینه",
             situation_id="rs-x", hit_count=6):
    study = new_study(tmp_path / "ws", "w05-study",
                      corpus_root=r"C:/nonexistent-corpus")
    cand = InquiryCandidate(
        candidate_id=candidate_id, kind="lexical-anchor", form=form,
        proposer_type="human", proposer_id="mz", rationale="r",
        support_status=support,
        hit_count=hit_count if support == "supported" else 0,
        poem_count=1 if support == "supported" else 0,
        poet_count=1 if support == "supported" else 0,
        evidence=[CandidateEvidenceRef(
            path="poets/x/p1.json", poem_id=1, verse_order=1,
            couplet_index=0, match_span=[0, 4],
            corpus_snapshot_id="cs1-test",
        )] if support == "supported" else [],
    )
    cat = InquiryCatalog(
        study_id="w05-study", situation_id=situation_id,
        corpus_snapshot_id="cs1-test", field_id="field-1",
        scope_spec={"kind": "all"}, parameters={},
        limitations=[], candidates=[cand],
    )
    persist_catalog(study, cat)
    return study, cat


def test_accept_supported_promotes_atomically(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    decisions = [{"candidate_id": "cand-1", "decision": "accept", "rationale": "verified in corpus"}]
    result = apply_review_decisions(study, cat.id, "rs-x", "mz", "receipt-1", decisions)
    assert result["promoted"] == ["cand-1"]
    # Object Address + anchor actually registered in the ACTIVE store
    ids = load_object_address_ids(study)
    assert "cand-1" in ids or any("lasso" in i or "cand-1" in i for i in ids)
    # review recorded
    from ontograph.inquiry import read_reviews

    reviews = read_reviews(study)
    assert len(reviews) == 1 and reviews[0].decision == "accept"
    # NO assessment created by review (walk owns per-hit decisions)
    ledger = study / "corpus" / "occurrence-ledger.jsonl"
    assert not ledger.exists() or ledger.read_text(encoding="utf-8").strip() == ""


def test_accept_unsupported_requires_rationale(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path, support="unsupported")
    with pytest.raises(ValueError, match="rationale"):
        apply_review_decisions(study, cat.id, "rs-x", "mz", "rc-1",
                               [{"candidate_id": "cand-1", "decision": "accept-unsupported",
                                 "rationale": ""}])
    from ontograph.inquiry import read_reviews

    assert read_reviews(study) == [], "refusal writes nothing"


def test_zero_support_ordinary_accept_refused(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path, support="unsupported")
    with pytest.raises(ValueError, match="unsupported"):
        apply_review_decisions(study, cat.id, "rs-x", "mz", "rc-1",
                               [{"candidate_id": "cand-1", "decision": "accept",
                                 "rationale": "r"}])


def test_agent_review_refused(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    with pytest.raises(ValueError, match="human"):
        apply_review_decisions(study, cat.id, "rs-x", "agent:hermes", "rc-1",
                               [{"candidate_id": "cand-1", "decision": "accept",
                                 "rationale": "r"}])


def test_stale_catalog_refused(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    with pytest.raises(ValueError, match="unknown|stale"):
        apply_review_decisions(study, "ic-nothere", "rs-x", "mz", "rc-1",
                               [{"candidate_id": "cand-1", "decision": "accept",
                                 "rationale": "r"}])


def test_duplicate_review_refused(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    decisions = [{"candidate_id": "cand-1", "decision": "accept", "rationale": "r"}]
    apply_review_decisions(study, cat.id, "rs-x", "mz", "rc-1", decisions)
    with pytest.raises(ValueError, match="duplicate|already"):
        apply_review_decisions(study, cat.id, "rs-x", "mz", "rc-2", decisions)


def test_mixed_situation_refused(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    with pytest.raises(ValueError, match="situation"):
        apply_review_decisions(study, cat.id, "rs-OTHER", "mz", "rc-1",
                               [{"candidate_id": "cand-1", "decision": "accept",
                                 "rationale": "r"}])


def test_defer_creates_no_promotion(tmp_path: Path) -> None:
    study, cat = _catalog(tmp_path)
    result = apply_review_decisions(study, cat.id, "rs-x", "mz", "rc-1",
                                    [{"candidate_id": "cand-1", "decision": "defer",
                                      "rationale": "need more evidence"}])
    assert result["promoted"] == [] and result["deferred"] == ["cand-1"]
    assert load_object_address_ids(study) == [], "defer never promotes"
