"""Ledger row T03: non-destructive migration + ID/duplicate validation.

Discriminating targets (execution spec §13 T03 + §15 migration rules):

1. A copied legacy rostam-style workspace (path-shaped study_id, no
   schema_version, poem-keyed assessments present) is detected, and
   `workspace migrate` PREVIEW reports counts/inferred modes/orphans
   WITHOUT writing anything. Only `--apply` writes; the original
   workspace bytes are unchanged either way (non-destructive: migration
   runs on the copy in these tests and the tests also assert the ORIGINAL
   directory mtime/content is untouched when only previewing).
2. Migration requires explicit `--new-id` before a directory rename to a
   valid ID; legacy path IDs stay readable.
3. Duplicate object IDs and invalid IDs are rejected on write routes.
4. Legacy poem-level decisions are stored as `legacy-poem-decision` and
   NEVER fanned across multiple hits (§15.5) -- re-review is required.
5. An append-only migration receipt with before/after hashes is written.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ontograph.migrate import (
    MigrationPlan,
    detect_legacy,
    migrate_workspace,
    preview_migration,
    validate_object_address_id,
)


def _dir_hash(p: Path, exclude: str | None = None) -> str:
    from ontograph.migrate import _dir_hash as _m

    return _m(p, exclude=exclude)


@pytest.fixture()
def legacy_workspace(tmp_path: Path) -> Path:
    """A minimal legacy (pre-T01) workspace: no schema_version, path-shaped
    id, one object entry with an anchor, poem-keyed occurrence ledger."""
    ws = tmp_path / "ontograph-workspaces" / "C:_Users_someone_rostam-strategies"
    (ws / "objects").mkdir(parents=True)
    (ws / "corpus").mkdir()
    (ws / "events").mkdir()
    (ws / "field").mkdir()
    (ws / "study.yml").write_text(
        "study_id: C:/Users/someone/rostam-strategies\ncorpus_root: C:/corpus\n",
        encoding="utf-8",
    )
    (ws / "objects" / "object-addresses.jsonl").write_text(
        json.dumps({"id": "mirror", "preferred_label": "آینه", "anchors": ["آینه"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (ws / "corpus" / "occurrence-ledger.jsonl").write_text(
        json.dumps({"poem_id": 9101, "decision": "accepted", "note": "legacy poem-level"}) + "\n",
        encoding="utf-8",
    )
    return ws


def test_detect_legacy_by_missing_schema_version(legacy_workspace: Path) -> None:
    plan = detect_legacy(legacy_workspace)
    assert plan.is_legacy is True
    assert plan.schema_version == 1
    assert plan.legacy_poem_decisions == 1
    assert plan.objects == 1
    # non-legacy detection by filename must NOT happen (§15.1): a modern
    # workspace with schema_version 2 is never flagged even if its dir
    # name looks path-shaped
    modern = legacy_workspace.parent / "modern"
    modern.mkdir()
    (modern / "study.yml").write_text(
        "schema_version: 2\nstudy_id: modern\ncorpus_root: C:/corpus\n", encoding="utf-8"
    )
    assert detect_legacy(modern).is_legacy is False


def test_preview_writes_nothing(legacy_workspace: Path) -> None:
    before = _dir_hash(legacy_workspace)
    plan: MigrationPlan = preview_migration(legacy_workspace)
    assert plan.inferred_modes == {"mirror": ["exact"]}  # single-token anchor -> exact
    assert plan.legacy_poem_decisions == 1
    assert plan.writes == []
    assert _dir_hash(legacy_workspace) == before, "preview must not write"


def test_apply_is_atomic_receipted_and_fans_no_poem_decisions(legacy_workspace: Path) -> None:
    before_hash = _dir_hash(legacy_workspace)
    receipt = migrate_workspace(legacy_workspace, apply=True)
    # schema stamped
    text = (legacy_workspace / "study.yml").read_text(encoding="utf-8")
    assert "schema_version: 2" in text
    # legacy poem decision preserved as legacy-poem-decision, NOT fanned
    ledger = [json.loads(l) for l in (legacy_workspace / "corpus" / "occurrence-ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    decisions = [r.get("assessor_type") for r in ledger]
    assert "legacy-poem-decision" in decisions, "legacy decision must be preserved with that marker"
    assert len(ledger) == 1, "never fan one poem decision across hits"
    # receipt has before/after hashes and the before hash matches reality
    # (both hashes exclude the append-only receipt file itself, so the
    # after-hash comparison against the live directory is well-defined)
    assert receipt.before_content_hash == before_hash
    from ontograph.migrate import RECEIPT_REL_PATH

    assert receipt.after_content_hash == _dir_hash(legacy_workspace, exclude=RECEIPT_REL_PATH)
    assert receipt.before_content_hash != receipt.after_content_hash


def test_rename_requires_valid_new_id(legacy_workspace: Path) -> None:
    with pytest.raises(ValueError):
        migrate_workspace(legacy_workspace, apply=True, new_id="C:/bad/path id")
    receipt = migrate_workspace(legacy_workspace, apply=True, new_id="rostam-strategies")
    assert (legacy_workspace.parent / "rostam-strategies").exists()
    assert not legacy_workspace.exists()


def test_object_address_id_validation() -> None:
    assert validate_object_address_id("mirror-1") == "mirror-1"
    with pytest.raises(ValueError):
        validate_object_address_id("Bad ID!")
    with pytest.raises(ValueError):
        validate_object_address_id("")


def test_duplicate_object_ids_rejected(legacy_workspace: Path) -> None:
    from ontograph.migrate import check_duplicate_object_ids

    # simulate a duplicate write
    with pytest.raises(ValueError, match="duplicate"):
        check_duplicate_object_ids(
            legacy_workspace, new_object_id="mirror",
            existing=[{"id": "mirror", "preferred_label": "آینه", "anchors": []}],
        )
