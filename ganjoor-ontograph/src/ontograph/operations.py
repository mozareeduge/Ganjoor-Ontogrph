"""Ledger row T09: OperationRecord persistence (spec §6.6).

Every analytical command persists an OperationRecord BEFORE returning
its result: append-only JSONL under `corpus/operations.jsonl`, one
immutable line per operation, carrying the full §6.6 field set and a
source manifest (poem id, repository-relative path, hit ids,
verse/couplet coordinates). Concurrent writers take an exclusive lock
and FAIL rather than interleave. `created_at` uses UTC ISO-8601;
record IDs are type prefix + UUID4 hex (spec §6.2).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

OPERATION_SCHEMA_VERSION = "3.0.0"
OPERATIONS_REL = "corpus/operations.jsonl"


def new_operation_id() -> str:
    return "op-" + uuid.uuid4().hex


def build_operation_record(
    study_id: str,
    operation_type: str,
    operation_version: str,
    parameters: dict,
    result: dict,
    hits: list,
    corpus_snapshot_id: str,
    workspace: Path,
    field_charter_version: str = "1.0.0",
    scope_spec: dict | None = None,
    limitations: list[str] | None = None,
    poem_paths: dict[int, str] | None = None,
) -> dict:
    """Assemble the §6.6 record. Source paths come from `poem_paths`
    (poem_id -> repository-relative path, supplied by the caller from its
    scan/index records); hits without a mapped path get a `poem://`
    pointer so provenance is never silently empty."""
    by_poem: dict[int, list] = {}
    for h in hits:
        by_poem.setdefault(h.poem_id, []).append(h)
    source_manifest = []
    for poem_id in sorted(by_poem):
        group = by_poem[poem_id]
        rel = (poem_paths or {}).get(poem_id, "")
        if not rel:
            rel = f"poem://{poem_id}"  # no corpus layout available to the caller
        rel = rel.replace("\\", "/")
        source_manifest.append({
            "poem_id": poem_id,
            "path": rel,
            "hit_ids": [h.id for h in group],
            "verse_orders": [h.verse_order for h in group],
            "couplet_indexes": [h.couplet_index for h in group],
        })
    return {
        "id": new_operation_id(),
        "schema_version": OPERATION_SCHEMA_VERSION,
        "study_id": study_id,
        "operation_type": operation_type,
        "operation_version": operation_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "field_charter_version": field_charter_version,
        "scope_spec": scope_spec or {},
        "object_address_ids": sorted({h.object_address for h in hits}),
        "parameters": parameters,
        "result": result,
        "source_manifest": source_manifest,
        "corpus_snapshot": {"snapshot_id": corpus_snapshot_id},
        "limitations": limitations or [],
    }


def _operations_path(workspace: Path) -> Path:
    return Path(workspace) / OPERATIONS_REL


def persist_operation_record(workspace: Path, record: dict, timeout_s: float = 10.0) -> Path:
    """Append ONE JSON line under an exclusive lock. A held lock (another
    writer mid-write) makes this FAIL, not interleave."""
    path = _operations_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with operation_lock(workspace, timeout_s=timeout_s):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def read_operation_records(workspace: Path) -> list[dict]:
    path = _operations_path(workspace)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


import contextlib as _contextlib  # noqa: E402


class operation_lock:
    """Exclusive cross-process lock over the operations file (T09 lock:
    concurrent JSONL writers fail instead of interleaving). Uses
    O_CREAT|O_EXCL lockfile semantics with a timeout."""

    def __init__(self, workspace: Path, timeout_s: float = 10.0) -> None:
        self.lock_path = Path(workspace) / (OPERATIONS_REL + ".lock")
        self.timeout_s = timeout_s
        self._fd = None

    def __enter__(self) -> "operation_lock":
        import os
        import time

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                self._fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"another operation writer holds {self.lock_path}; "
                        "refusing to interleave (T09)"
                    )
                time.sleep(0.05)

    def __exit__(self, *exc) -> None:
        import os

        if self._fd is not None:
            os.close(self._fd)
            with _contextlib.suppress(FileNotFoundError):
                self.lock_path.unlink()
        self._fd = None
