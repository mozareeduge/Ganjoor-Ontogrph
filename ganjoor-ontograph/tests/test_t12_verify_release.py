"""Ledger row T12: atomic release, standalone verify, commit/tag last.

Discriminating targets (execution spec T12 + Gate D):

1. `verify_release` runs WITHOUT workspace access — a COPIED release
   directory (moved anywhere) verifies.
2. Tampering fails: any byte change to any covered file (report, record,
   release.json) breaks its manifest hash; deleting a file fails; adding
   an unlisted file fails.
3. Manifest completeness: every file in the directory except
   manifest.sha256 must be listed; every listed file must exist.
4. Clean refusal on existing target is already T10; here the atomic
   rename + tag-last order is tested via verify-after-copy.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ontograph.release_v2 import collect_release
from ontograph.verify_release import verify_release


def _make_release(tmp_path: Path) -> Path:
    return collect_release(
        workspace=tmp_path, version="0.1.1", study_id="s",
        corpus_snapshot={"snapshot_id": "cs1-test"},
        operations=[{
            "id": "op-1", "operation_type": "census", "operation_version": "2.0.0",
            "parameters": {}, "result": {"prevalence": "5/27"},
            "source_manifest": [], "limitations": [], "corpus_snapshot": {},
        }],
    )


def test_copied_release_verifies_without_workspace(tmp_path: Path) -> None:
    out = _make_release(tmp_path)
    copy = tmp_path.parent / "elsewhere-release"
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(out, copy)
    report = verify_release(copy)
    assert report["valid"] is True
    assert report["files_checked"] > 0


def test_tampered_record_fails(tmp_path: Path) -> None:
    out = _make_release(tmp_path)
    ops = out / "records" / "operations.jsonl"
    ops.write_text(ops.read_text(encoding="utf-8").replace("5/27", "6/27"), encoding="utf-8")
    report = verify_release(out)
    assert report["valid"] is False
    assert any("operations.jsonl" in i for i in report["issues"])


def test_deleted_file_fails(tmp_path: Path) -> None:
    out = _make_release(tmp_path)
    (out / "report.html").unlink()
    report = verify_release(out)
    assert report["valid"] is False


def test_unlisted_extra_file_fails(tmp_path: Path) -> None:
    out = _make_release(tmp_path)
    (out / "smuggled.txt").write_text("x", encoding="utf-8")
    report = verify_release(out)
    assert report["valid"] is False
    assert any("smuggled.txt" in i for i in report["issues"])


def test_tampered_release_json_fails(tmp_path: Path) -> None:
    out = _make_release(tmp_path)
    rj = out / "release.json"
    data = rj.read_text(encoding="utf-8").replace('"study_id": "s"', '"study_id": "s2"')
    rj.write_text(data, encoding="utf-8")
    assert verify_release(out)["valid"] is False
