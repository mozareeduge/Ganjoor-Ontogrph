"""Ledger row W07A: operation inquiry schema + situation selector.

Discriminating targets (openspec tasks.md W07A, design §8):

1. OperationRecord schema 3 round-trips situation fields
   (`situation_id`, `inquiry_status`).
2. Tolerant readers mark schema-1/2 rows (no situation fields) as
   `legacy-unframed` — never raise, never fabricate a situation_id.
3. A pure selector (`select_situation`) inherits ONE active situation;
   refuses ZERO (message names the `inquire` command) and refuses
   MULTIPLE without an explicit ID — never selects by recency.
4. An unknown/nonexistent situation ID is refused.
5. A superseded situation is never selected — not implicitly, and not
   by explicit ID while an active situation exists.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.operations import (
    LEGACY_UNFRAMED,
    build_operation_record,
    persist_operation_record,
    read_operation_records,
)
from ontograph.records_v2 import ResearchSituation, persist_situation
from ontograph.w07 import SituationResolutionError, select_situation


def _make_situation(status: str = "situational", rs_id: str = "",
                    supersedes: str | None = None) -> ResearchSituation:
    s = ResearchSituation(
        study_id="w07-study",
        verbatim_hunch="a hunch about mirrors in the fixture",
        normalized_display_hunch="a hunch about mirrors in the fixture",
        actor="mz",
        status=status,
        supersedes=supersedes,
    )
    if rs_id:
        object.__setattr__(s, "id", rs_id)
    return s


# --- 1. schema 3 round-trip -------------------------------------------------


def test_schema3_roundtrips_situation_fields(tmp_path: Path) -> None:
    record = build_operation_record(
        "w07-study", "census", "1.0.0", {}, {}, [], "cs1-test",
        workspace=tmp_path,
        situation_id="rs1-abc", inquiry_status="governed",
    )
    assert record["situation_id"] == "rs1-abc"
    assert record["inquiry_status"] == "governed"
    persist_operation_record(tmp_path, record)
    loaded = read_operation_records(tmp_path)
    assert loaded[0]["situation_id"] == "rs1-abc"
    assert loaded[0]["inquiry_status"] == "governed"


# --- 2. tolerant legacy reader ----------------------------------------------


def test_legacy_rows_marked_legacy_unframed(tmp_path: Path) -> None:
    legacy = {
        "id": "op-old1", "schema_version": "2.0.0", "study_id": "w07-study",
        "operation_type": "census", "operation_version": "1.0.0",
        "created_at": "2026-09-05T10:00:00+00:00",
        "field_charter_version": "1.0.0", "scope_spec": {},
        "object_address_ids": ["mirror"], "parameters": {}, "result": {},
        "source_manifest": [], "corpus_snapshot": {"snapshot_id": "cs1-x"},
        "limitations": [],
    }  # deliberately NO situation fields
    path = tmp_path / "corpus" / "operations.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    loaded = read_operation_records(tmp_path)
    assert loaded[0]["inquiry_status"] == LEGACY_UNFRAMED
    assert loaded[0]["situation_id"] is None


# --- 3. the pure selector ----------------------------------------------------


def test_single_active_situation_inherited(tmp_path: Path) -> None:
    persist_situation(tmp_path, _make_situation(rs_id="rs1-only"))
    assert select_situation(tmp_path, None) == "rs1-only"


def test_zero_situations_refuse_naming_inquire(tmp_path: Path) -> None:
    with pytest.raises(SituationResolutionError) as exc:
        select_situation(tmp_path, None)
    assert "inquire" in str(exc.value)


def test_multiple_active_refuse_without_explicit_id(tmp_path: Path) -> None:
    persist_situation(tmp_path, _make_situation(rs_id="rs1-a"))
    persist_situation(tmp_path, _make_situation(rs_id="rs1-b"))
    # refusal — never silent recency selection
    with pytest.raises(SituationResolutionError):
        select_situation(tmp_path, None)
    # explicit ID disambiguates
    assert select_situation(tmp_path, "rs1-b") == "rs1-b"


def test_unknown_situation_id_refuses(tmp_path: Path) -> None:
    persist_situation(tmp_path, _make_situation(rs_id="rs1-a"))
    with pytest.raises(SituationResolutionError):
        select_situation(tmp_path, "rs1-missing")


# --- 4. superseded situations are never selected ------------------------------


def test_all_superseded_refuses(tmp_path: Path) -> None:
    persist_situation(tmp_path, _make_situation(
        rs_id="rs1-old", status="superseded", supersedes="rs1-older"))
    with pytest.raises(SituationResolutionError) as exc:
        select_situation(tmp_path, None)
    assert "inquire" in str(exc.value)


def test_superseded_id_refuses_when_active_exists(tmp_path: Path) -> None:
    persist_situation(tmp_path, _make_situation(
        rs_id="rs1-old", status="superseded", supersedes="rs1-older"))
    persist_situation(tmp_path, _make_situation(rs_id="rs1-new"))
    with pytest.raises(SituationResolutionError):
        select_situation(tmp_path, "rs1-old")
    assert select_situation(tmp_path, "rs1-new") == "rs1-new"
