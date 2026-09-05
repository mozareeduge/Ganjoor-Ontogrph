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
