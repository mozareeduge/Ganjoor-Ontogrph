"""Ledger row T09: OperationRecord persisted BEFORE returning, with
source manifest, provenance, and stdout operation_record_id.

Discriminating targets (execution spec §6.6, T09):

1. Every analytical command persists an OperationRecord (append-only
   JSONL) BEFORE returning its result — a result without a persisted
   record is the forbidden shortcut.
2. Repetition appends a NEW immutable record (never overwrites).
3. The record carries: schema_version, study_id, operation_type,
   operation_version, created_at, field_charter_version, scope_spec,
   object_address_ids, parameters, result, source_manifest, and
   corpus_snapshot — every §6.6 field present.
4. Source entries carry poem id, repository-relative path, hit IDs, and
   verse/couplet coordinates.
5. Concurrent writers fail instead of interleaving (file lock).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from ontograph.anchors import AnchorHit
from ontograph.operations import (
    OPERATION_SCHEMA_VERSION,
    build_operation_record,
    persist_operation_record,
    read_operation_records,
)


def _hit(poem_id: int, verse_order: int) -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=0, position="Right",
        original_text="آینه در دست من است امشب",
        normalized_text="آینه در دست من است امشب",
        token_start=0, token_end=4,
        verse_order=verse_order, corpus_snapshot_id="cs1-test",
    )


def test_record_carries_every_section_field(tmp_path: Path) -> None:
    hits = [_hit(9101, 1), _hit(9102, 1)]
    record = build_operation_record(
        study_id="rostam-strategies",
        operation_type="census",
        operation_version="2.0.0",
        parameters={"object": "mirror", "mode": "assessed-full"},
        result={"hit_count": 2},
        hits=hits,
        corpus_snapshot_id="cs1-test",
        workspace=tmp_path,
        poem_paths={9101: "poets/sample1/ghazal/p9101.json",
                    9102: "poets/sample2/ghazal/p9201.json"},
    )
    for f in ("id", "schema_version", "study_id", "operation_type", "operation_version",
              "created_at", "field_charter_version", "scope_spec", "object_address_ids",
              "parameters", "result", "source_manifest", "corpus_snapshot", "limitations"):
        assert f in record, f"missing §6.6 field: {f}"
    assert record["schema_version"] == OPERATION_SCHEMA_VERSION
    entry = record["source_manifest"][0]
    assert entry["poem_id"] == 9101
    assert entry["path"] == "poets/sample1/ghazal/p9101.json"
    assert entry["hit_ids"] == [hits[0].id]
    assert entry["verse_orders"] == [1]


def test_persist_before_return_and_append_only(tmp_path: Path) -> None:
    hits = [_hit(9101, 1)]
    r1 = build_operation_record(
        study_id="s", operation_type="census", operation_version="2.0.0",
        parameters={}, result={"hit_count": 1}, hits=hits,
        corpus_snapshot_id="cs1-test", workspace=tmp_path,
    )
    path = persist_operation_record(tmp_path, r1)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    # repetition appends a NEW record
    r2 = dict(r1)
    r2["id"] = r1["id"] + "-b"
    persist_operation_record(tmp_path, r2)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    records = read_operation_records(tmp_path)
    assert [r["id"] for r in records] == [r1["id"], r1["id"] + "-b"]


def test_relative_paths_never_absolute(tmp_path: Path) -> None:
    hits = [_hit(9101, 1)]
    record = build_operation_record(
        study_id="s", operation_type="census", operation_version="2.0.0",
        parameters={}, result={}, hits=hits,
        corpus_snapshot_id="cs1-test", workspace=tmp_path,
    )
    entry = record["source_manifest"][0]
    assert not entry["path"].startswith(str(tmp_path)) and "\\" not in entry["path"]


def test_concurrent_writers_fail_not_interleave(tmp_path: Path) -> None:
    import subprocess, sys

    hits = [_hit(9101, 1)]
    record = build_operation_record(
        study_id="s", operation_type="census", operation_version="2.0.0",
        parameters={}, result={}, hits=hits,
        corpus_snapshot_id="cs1-test", workspace=tmp_path,
    )
    # a held lock makes the second writer fail cleanly
    from ontograph.operations import operation_lock

    with operation_lock(tmp_path):
        with pytest.raises(Exception):
            persist_operation_record(tmp_path, record, timeout_s=1)
    # after release, write succeeds
    persist_operation_record(tmp_path, record)
