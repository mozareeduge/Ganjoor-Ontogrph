"""Ledger row T10: release collector and self-contained layout.

Discriminating targets (execution spec §6.7, T10):

1. `collect_release` produces the FULL §6.7 layout — records/ JSONL for
   every type (empty types get explicit EMPTY files), field/, provenance/,
   release.json, manifest.sha256 — never silently omitting a section.
2. Release references only internal relative paths + SHA-256 values.
3. manifest.sha256 lists every release file EXCEPT itself.
4. Existing release directory causes clean refusal (no clobber).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.release_v2 import (
    RELEASE_RECORD_TYPES,
    collect_release,
)


def test_full_layout_with_empty_explicit_files(tmp_path: Path) -> None:
    out = collect_release(
        workspace=tmp_path, version="0.1.1",
        study_id="s", corpus_snapshot={"snapshot_id": "cs1-test"},
        operations=[{"id": "op-1", "operation_type": "census"}],
    )
    rel = out.relative_to(tmp_path)
    for p in [
        "release.json", "manifest.sha256", "report.md", "report.html",
        "records/object-addresses.jsonl", "records/lexical-anchors.jsonl",
        "records/occurrence-assessments.jsonl", "records/occurrence-policies.jsonl",
        "records/operations.jsonl", "records/profiles.jsonl", "records/mappings.jsonl",
        "records/traces.jsonl", "records/experiments.jsonl", "records/findings.jsonl",
        "records/relation-objects.jsonl", "records/claims.jsonl", "records/reductions.jsonl",
        "records/events.jsonl", "records/research-situations.jsonl", "records/seeds.jsonl",
        "records/inquiry-catalogs.jsonl", "records/inquiry-reviews.jsonl",
        "records/descriptive-catalogs.jsonl",
        "field/charter.yml", "field/scope.json",
        "provenance/corpus-snapshot.json", "provenance/software-environment.json",
    ]:
        assert (tmp_path / rel / p).exists(), f"missing release file: {p}"
    ops = (tmp_path / rel / "records" / "operations.jsonl").read_text(encoding="utf-8")
    assert "op-1" in ops
    # empty types are explicit EMPTY files
    claims = (tmp_path / rel / "records" / "claims.jsonl").read_text(encoding="utf-8")
    assert claims == ""


def test_manifest_lists_everything_except_itself(tmp_path: Path) -> None:
    out = collect_release(
        workspace=tmp_path, version="0.1.1", study_id="s",
        corpus_snapshot={"snapshot_id": "cs1-test"}, operations=[],
    )
    manifest = (out / "manifest.sha256").read_text(encoding="utf-8")
    assert "manifest.sha256" not in manifest
    assert "release.json" in manifest and "records/operations.jsonl" in manifest
    # every listed hash matches
    import hashlib

    for line in manifest.strip().splitlines():
        digest, rel = line.split("  ", 1)
        f = out / rel
        assert f.exists()
        assert hashlib.sha256(f.read_bytes()).hexdigest() == digest


def test_existing_release_dir_refused(tmp_path: Path) -> None:
    collect_release(workspace=tmp_path, version="0.1.1", study_id="s",
                    corpus_snapshot={"snapshot_id": "cs1-test"}, operations=[])
    with pytest.raises(Exception, match="exists"):
        collect_release(workspace=tmp_path, version="0.1.1", study_id="s",
                        corpus_snapshot={"snapshot_id": "cs1-test"}, operations=[])


def test_release_json_internal_references_only(tmp_path: Path) -> None:
    out = collect_release(
        workspace=tmp_path, version="0.1.1", study_id="s",
        corpus_snapshot={"snapshot_id": "cs1-test"},
        operations=[{"id": "op-1", "operation_type": "census"}],
    )
    rj = json.loads((out / "release.json").read_text(encoding="utf-8"))
    text = json.dumps(rj)
    assert str(tmp_path) not in text and "C:\\" not in text
    assert rj["study_id"] == "s" and rj["version"] == "0.1.1"
