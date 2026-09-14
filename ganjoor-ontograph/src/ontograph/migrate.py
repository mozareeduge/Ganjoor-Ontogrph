"""Ledger row T03: non-destructive migration + ID/duplicate validation.

Spec §15 (migration and compatibility) and the execution spec's T03 row:
- legacy detection is by missing `schema_version`, never by filename;
- preview counts/inferred modes/orphans/writes without writing;
- `--apply` is atomic (schema stamp, receipts) and never destroys;
- legacy poem-level decisions are preserved as `legacy-poem-decision`
  records and are NEVER fanned across multiple hits -- re-review happens
  through the walk flow, not by copying;
- renames require an explicit, valid `--new-id`;
- every migration appends a receipt with before/after content hashes.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ontograph.anchors import resolve_auto_mode
from ontograph.workspace import WORKSPACE_SCHEMA_VERSION, read_study_config

VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

MIGRATION_RECEIPT_VERSION = "1.0.0"


def validate_object_address_id(object_address_id: str) -> str:
    """Object Address IDs are researcher-chosen ASCII-safe IDs (spec §6.2):
    lowercase/alphanumeric start, then [a-z0-9._-]. IDs are not paths."""
    if not object_address_id or not VALID_ID_RE.match(object_address_id):
        raise ValueError(
            f"invalid object address id {object_address_id!r}: must match "
            f"{VALID_ID_RE.pattern} (ids are not paths)"
        )
    return object_address_id


def check_duplicate_object_ids(
    workspace: Path, new_object_id: str, existing: list[dict]
) -> None:
    """Refuse a duplicate active Object Address ID on any write route."""
    validate_object_address_id(new_object_id)
    for entry in existing:
        if entry.get("id") == new_object_id:
            raise ValueError(
                f"duplicate object address id: {new_object_id!r} already exists "
                f"in {workspace}; ids are unique"
            )


@dataclass
class MigrationPlan:
    workspace: Path
    is_legacy: bool
    schema_version: int
    objects: int = 0
    legacy_poem_decisions: int = 0
    inferred_modes: dict[str, list[str]] = field(default_factory=dict)
    orphans: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)


def _object_entries(ws: Path) -> list[dict]:
    path = ws / "objects" / "object-addresses.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _ledger_rows(ws: Path) -> list[dict]:
    path = ws / "corpus" / "occurrence-ledger.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def detect_legacy(workspace: str | Path) -> MigrationPlan:
    ws = Path(workspace)
    config = read_study_config(ws)
    version = config.get("schema_version")
    is_legacy = version is None  # §15.1: detect by missing key, never filename
    plan = MigrationPlan(
        workspace=ws,
        is_legacy=is_legacy,
        schema_version=int(version) if isinstance(version, int) else 1,
        objects=len(_object_entries(ws)),
    )
    for row in _ledger_rows(ws):
        # a pre-T05 legacy ledger row is poem-keyed: it has poem_id but no
        # anchor_hit_id (per-hit identity only exists from T04/T05 on)
        if "poem_id" in row and not row.get("anchor_hit_id"):
            plan.legacy_poem_decisions += 1
    for entry in _object_entries(ws):
        for form in entry.get("anchors", []):
            if isinstance(form, str) and form:
                plan.inferred_modes.setdefault(entry["id"], []).append(resolve_auto_mode(form))
            else:
                plan.orphans.append(f"{entry.get('id')}: non-string anchor {form!r}")
    return plan


def preview_migration(workspace: str | Path) -> MigrationPlan:
    """Preview ONLY: identical detection, zero writes."""
    return detect_legacy(workspace)


@dataclass
class MigrationReceipt:
    before_content_hash: str
    after_content_hash: str
    applied: bool
    renamed_to: str | None


def _dir_hash(p: Path, exclude: str | None = None) -> str:
    h = hashlib.sha256()
    for f in sorted(p.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(p)).replace("\\", "/")
        if exclude is not None and rel == exclude:
            continue
        h.update(rel.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


RECEIPT_REL_PATH = "corpus/migration-receipts.jsonl"


def migrate_workspace(
    workspace: str | Path, apply: bool, new_id: str | None = None
) -> MigrationReceipt:
    """Non-destructive migration. Without `apply` this is preview only.

    With `apply`: stamp schema_version 2 (atomic rewrite), convert poem-
    keyed legacy ledger rows to `legacy-poem-decision` marker rows (one
    row in, one marker row out -- never fanned), append a receipt, and —
    only with a VALID `new_id` — rename the directory. The legacy path-
    shaped study_id is preserved as `legacy_study_id` (§15.6)."""
    ws = Path(workspace)
    plan = detect_legacy(ws)
    before = _dir_hash(ws, exclude=RECEIPT_REL_PATH)
    if new_id is not None:
        validate_object_address_id(new_id)
    if not apply:
        return MigrationReceipt(before, before, applied=False, renamed_to=None)

    # 1. stamp schema_version in study.yml (atomic: tmp file + rename)
    config = read_study_config(ws)
    config["schema_version"] = WORKSPACE_SCHEMA_VERSION
    study_yml = ws / "study.yml"
    tmp = study_yml.with_suffix(".yml.tmp")
    tmp.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(study_yml)

    # 2. preserve legacy poem-level decisions with the marker assessor type
    #    (§15.5): one row in -> one marker row out, never fanned across hits
    ledger_path = ws / "corpus" / "occurrence-ledger.jsonl"
    if ledger_path.exists():
        rows = _ledger_rows(ws)
        out_lines = []
        for row in rows:
            if "poem_id" in row and not row.get("anchor_hit_id"):
                row = dict(row)
                row["assessor_type"] = "legacy-poem-decision"
                row["reassessment_required"] = True
            out_lines.append(json.dumps(row, ensure_ascii=False))
        ledger_tmp = ledger_path.with_suffix(".jsonl.tmp")
        ledger_tmp.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
        ledger_tmp.replace(ledger_path)

    # 3. optional rename (requires valid new_id, validated above)
    target: Path | None = None
    if new_id is not None:
        config = read_study_config(ws)
        config["legacy_study_id"] = config.get("study_id")
        config["study_id"] = new_id
        study_yml.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        target = ws.parent / new_id
        ws.rename(target)
        ws = target

    receipt = MigrationReceipt(
        before_content_hash=before,
        after_content_hash=_dir_hash(ws, exclude=RECEIPT_REL_PATH),
        applied=True,
        renamed_to=str(target) if target else None,
    )
    # 4. append-only receipt (§15.7)
    receipts = ws / "corpus" / "migration-receipts.jsonl"
    with receipts.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "schema_version": MIGRATION_RECEIPT_VERSION,
                    "before_content_hash": receipt.before_content_hash,
                    "after_content_hash": receipt.after_content_hash,
                    "renamed_to": receipt.renamed_to,
                }
            )
            + "\n"
        )
    return receipt


# --- Amendment 20 §9/F04: hit-assessments.jsonl -> occurrence-positions.jsonl ---
#
# A SEPARATE migration from migrate_workspace() above (which handles T03's
# poem-keyed -> hit-keyed upgrade). This one upgrades the hit-keyed
# HitOccurrenceAssessment ledger (T05-era, one active row per hit, human
# implied) into the flat-assessment OccurrencePosition model (Amendment
# 20 §3.1, many co-existing positions per hit, no implied assessor).

POSITIONS_MIGRATION_RECEIPT_VERSION = "1.0.0"

from ontograph.positions import STANCE_OF_DECISION  # noqa: E402


def _legacy_assessor_id(assessor_type: str, assessor_id: str) -> str:
    return f"legacy:{assessor_type}:{assessor_id or 'unknown'}"


def preview_positions_migration(workspace: str | Path) -> dict:
    """Preview ONLY: identical detection, zero writes (mirrors
    preview_migration's contract for the T03 migration)."""
    from ontograph.census import load_hit_assessments

    ws = Path(workspace)
    rows = load_hit_assessments(ws)
    to_migrate = [r for r in rows if r.assessor_type != "legacy-poem-decision"]
    skipped = [r for r in rows if r.assessor_type == "legacy-poem-decision"]
    distinct = sorted({(r.assessor_type, r.assessor_id or "unknown") for r in to_migrate})
    return {
        "workspace": str(ws),
        "positions_to_create": len(to_migrate),
        "legacy_poem_decisions_skipped": len(skipped),
        "assessors_to_synthesize": [_legacy_assessor_id(t, i) for t, i in distinct],
        "object_addresses": sorted({r.object_address_id for r in to_migrate}),
    }


def migrate_to_positions(workspace: str | Path, apply: bool) -> dict:
    """Amendment 20 §9. Non-destructive, `--apply`-gated, before/after-hash
    receipt.

    1. Each `hit-assessments.jsonl` row with a real per-hit decision
       becomes exactly ONE `OccurrencePosition` -- never fanned. Rows are
       replayed in file order, so a hit that was re-decided multiple times
       by the SAME (assessor_type, assessor_id) reconstructs the same
       supersession chain through `positions.position_for()`'s own
       same-assessor-active-lookup; a hit decided by two DIFFERENT legacy
       identities keeps both as separate, non-erasing positions (which the
       old flat ledger could never actually represent, since it only ever
       tracked one active row per hit -- see the policy note below).
    2. `legacy-poem-decision` rows (poem-keyed, no anchor_hit_id) are left
       untouched wherever they already live and are never converted --
       they continue to provide zero coverage exactly as before (Amendment
       20 §3.2's one non-hierarchical, structural exception).
    3. Each migrated study gets an explicit `ResolutionPolicy`, declared
       by "migration", so the pre-Amendment-20 numbers stay reproducible
       as a visible choice rather than a hidden default.

       DEVIATION FROM THE AMENDMENT'S LITERAL TEXT, judged deliberately:
       the Amendment's §9 prose names `named-assessor(legacy:human:*)` as
       the synthesized policy. That kind requires exactly ONE
       assessor_object_id (§4.3); no wildcard mechanism exists or was
       built. It would silently give wrong numbers on any study where the
       old ledger recorded more than one distinct (assessor_type,
       assessor_id) pair (e.g. two different --assessor values used
       across sessions). Since the OLD model only ever kept ONE active
       row per hit regardless of how many distinct ids touched it, every
       hit has exactly one legacy-synthesized position after migration --
       which makes `kind="concordance"` trivially and ALWAYS equivalent
       to the old single-decision semantics (unanimity among exactly one
       position is automatic), for any number of distinct legacy
       identities. Used here instead.
    4. Idempotent: if `occurrence-positions.jsonl` already has content,
       this is a no-op, not a duplicate.
    """
    from ontograph.assessors import AssessorObject, read_assessors, register_assessor
    from ontograph.census import load_hit_assessments
    from ontograph.positions import _ledger_path as _positions_ledger_path
    from ontograph.positions import position_for
    from ontograph.resolution import ResolutionPolicy, declare_policy, new_policy_id

    ws = Path(workspace)
    before = _dir_hash(ws, exclude=RECEIPT_REL_PATH)
    preview = preview_positions_migration(ws)
    if not apply:
        return {"applied": False, "before_content_hash": before, **preview}

    positions_path = _positions_ledger_path(ws)
    if positions_path.exists() and positions_path.read_text(encoding="utf-8").strip():
        return {"applied": True, "no_op": True, "reason": "occurrence-positions.jsonl already populated", **preview}

    rows = load_hit_assessments(ws)
    to_migrate = [r for r in rows if r.assessor_type != "legacy-poem-decision"]

    # 1. synthesize one AssessorObject per distinct (assessor_type, assessor_id)
    existing_ids = {a.id for a in read_assessors(ws)}
    distinct = sorted({(r.assessor_type, r.assessor_id or "unknown") for r in to_migrate})
    for assessor_type, assessor_id in distinct:
        legacy_id = _legacy_assessor_id(assessor_type, assessor_id)
        if legacy_id in existing_ids:
            continue
        register_assessor(ws, AssessorObject(
            id=legacy_id,
            label=f"legacy {assessor_type} ({assessor_id})",
            assessor_type=assessor_type,
            apparatus="migrated from pre-Amendment-20 hit-assessments.jsonl; "
                      "no richer apparatus record exists for pre-migration rows",
            independence_class="legacy-unknown",
            registered_by="migration",
        ))

    # 2. one row in -> one position out, in file order (reconstructs same-
    #    assessor supersession chains faithfully; never fans across hits)
    created = 0
    for r in to_migrate:
        legacy_id = _legacy_assessor_id(r.assessor_type, r.assessor_id or "unknown")
        position_for(
            ws, r.anchor_hit_id, r.object_address_id, legacy_id,
            STANCE_OF_DECISION[r.decision],
            rationale=r.rationale,
            apparatus="migrated (see AssessorObject.apparatus)",
        )
        created += 1

    # 3. explicit, visible policy declaration preserving old behaviour --
    #    see the docstring above for why `concordance`, not `named-assessor`
    declare_policy(ws, ResolutionPolicy(
        id=new_policy_id(),
        object_address_id="*",
        kind="concordance",
        declared_by="migration",
        justification="",
    ))

    receipt = {
        "schema_version": POSITIONS_MIGRATION_RECEIPT_VERSION,
        "migration_type": "positions",
        "before_content_hash": before,
        "after_content_hash": _dir_hash(ws, exclude=RECEIPT_REL_PATH),
        "positions_created": created,
        "legacy_poem_decisions_skipped": preview["legacy_poem_decisions_skipped"],
        "assessors_synthesized": preview["assessors_to_synthesize"],
    }
    receipts = ws / "corpus" / "migration-receipts.jsonl"
    receipts.parent.mkdir(parents=True, exist_ok=True)
    with receipts.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    return {"applied": True, "no_op": False, **receipt}
