"""Amendment 20 F04: migrate_to_positions() -- hit-assessments.jsonl ->
occurrence-positions.jsonl.

Discriminating targets (Plans.md F04 DoD):
1. Exactly one position per legacy assessment row.
2. Fixture arithmetic unchanged when resolved under the synthesized policy.
3. Original workspace files untouched (hash-verified).
4. Re-running on an already-migrated workspace is a no-op, not a duplicate.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ontograph.census import (
    HitOccurrenceAssessment,
    append_hit_assessment,
    load_hit_assessments,
    new_hit_assessment_id,
)
from ontograph.migrate import migrate_to_positions, preview_positions_migration
from ontograph.positions import active_positions, read_positions, standing_of
from ontograph.resolution import active_policy_for, resolve

OBJ = "mirror"


def _seed_legacy_ledger(ws: Path) -> None:
    """3 hits decided by one human, plus one hit re-decided (a
    supersession chain the migration must reconstruct faithfully)."""
    ws.mkdir(parents=True, exist_ok=True)
    rows = [
        HitOccurrenceAssessment(
            id=new_hit_assessment_id(), anchor_hit_id="ah1-1",
            object_address_id=OBJ, decision="accepted", assessor_type="human", assessor_id="mz",
        ),
        HitOccurrenceAssessment(
            id=new_hit_assessment_id(), anchor_hit_id="ah1-2",
            object_address_id=OBJ, decision="rejected", assessor_type="human", assessor_id="mz",
        ),
    ]
    for row in rows:
        append_hit_assessment(ws, row)
    # re-decide ah1-2: reject -> ambiguous (supersession within the SAME assessor)
    first_active = [r for r in load_hit_assessments(ws) if r.anchor_hit_id == "ah1-2"][0]
    revised = HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-2",
        object_address_id=OBJ, decision="ambiguous", assessor_type="human", assessor_id="mz",
        supersedes=first_active.id,
    )
    append_hit_assessment(ws, revised)


def test_preview_does_not_write(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    before = sorted(ws.rglob("*"))
    result = migrate_to_positions(ws, apply=False)
    after = sorted(ws.rglob("*"))
    assert before == after  # zero writes
    assert result["applied"] is False
    assert result["positions_to_create"] == 3  # 2 original + 1 revision row


def test_migration_creates_exactly_one_position_per_legacy_row(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    legacy_rows = load_hit_assessments(ws)
    assert len(legacy_rows) == 3

    result = migrate_to_positions(ws, apply=True)
    assert result["applied"] is True and result["no_op"] is False
    assert result["positions_created"] == 3

    positions = read_positions(ws)
    assert len(positions) == 3  # one in -> one out, never fanned


def test_supersession_chain_reconstructed_within_same_assessor(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    migrate_to_positions(ws, apply=True)

    positions = read_positions(ws)
    active = active_positions(positions, "ah1-2", OBJ)
    assert len(active) == 1  # still one active position (same assessor superseded itself)
    assert active[list(active)[0]].stance == "undecidable"  # ambiguous -> undecidable, the LATEST decision


def test_fixture_arithmetic_unchanged_under_synthesized_policy(tmp_path: Path) -> None:
    """The old flat ledger's numbers (2 hits assessed, ah1-1 accepted,
    ah1-2 [superseded to] ambiguous) must be exactly reproducible by
    resolving under the migration's synthesized policy."""
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    migrate_to_positions(ws, apply=True)

    policy = active_policy_for(ws, OBJ)
    assert policy is not None
    assert policy.kind == "concordance"
    assert policy.declared_by == "migration"

    positions = read_positions(ws)
    active_1 = active_positions(positions, "ah1-1", OBJ)
    active_2 = active_positions(positions, "ah1-2", OBJ)
    assert resolve(ws, active_1, policy) == "occurs"  # was "accepted"
    assert resolve(ws, active_2, policy) == "undecidable"  # was superseded to "ambiguous"

    # single-position hits are never "contested" -- old single-decision
    # semantics reproduce exactly regardless of how many distinct legacy
    # assessor ids exist in the study (see migrate.py's policy-choice note)
    assert standing_of(ws, active_1) == "single-position"
    assert standing_of(ws, active_2) == "single-position"


def test_original_workspace_untouched(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    reference = tmp_path / "reference-copy"
    shutil.copytree(ws, reference)

    migrate_to_positions(ws, apply=True)

    # every pre-existing file (hit-assessments.jsonl itself) is byte-identical;
    # the migration only ever ADDS new files, never edits existing ones
    original_ledger = reference / "corpus" / "hit-assessments.jsonl"
    migrated_ledger = ws / "corpus" / "hit-assessments.jsonl"
    assert original_ledger.read_bytes() == migrated_ledger.read_bytes()


def test_rerun_on_migrated_workspace_is_a_noop_not_a_duplicate(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    _seed_legacy_ledger(ws)
    migrate_to_positions(ws, apply=True)
    first_count = len(read_positions(ws))

    result = migrate_to_positions(ws, apply=True)
    assert result["no_op"] is True
    second_count = len(read_positions(ws))
    assert second_count == first_count  # not duplicated


def test_legacy_poem_decision_rows_are_never_converted(tmp_path: Path) -> None:
    ws = tmp_path / "study"
    ws.mkdir(parents=True)
    marker_row = HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-legacy",
        object_address_id=OBJ, decision="accepted",
        assessor_type="legacy-poem-decision", assessor_id="",
    )
    append_hit_assessment(ws, marker_row)
    real_row = HitOccurrenceAssessment(
        id=new_hit_assessment_id(), anchor_hit_id="ah1-real",
        object_address_id=OBJ, decision="accepted", assessor_type="human", assessor_id="mz",
    )
    append_hit_assessment(ws, real_row)

    preview = preview_positions_migration(ws)
    assert preview["positions_to_create"] == 1  # only the real row
    assert preview["legacy_poem_decisions_skipped"] == 1

    migrate_to_positions(ws, apply=True)
    positions = read_positions(ws)
    assert len(positions) == 1
    assert positions[0].anchor_hit_id == "ah1-real"
