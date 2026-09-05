"""Ledger row T10: release collector + self-contained layout (spec §6.7).

`collect_release` stages the FULL §6.7 layout: release.json,
manifest.sha256, report.md/html stubs (T11 fills them), records/ JSONL
for every declared record type (empty types get explicit EMPTY files),
field/, provenance/. All references are internal relative paths +
SHA-256 digests; absolute paths never enter the release. The manifest
lists every release file except itself. An existing release directory
is refused cleanly — no clobber.

Rendering (report.md/html with real values) is T11; standalone verify is
T12. The legacy P4.4/P9.8 release path stays untouched.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

RELEASE_SCHEMA_VERSION = "2.0.0"

RELEASE_RECORD_TYPES = (
    "object-addresses", "lexical-anchors", "occurrence-assessments",
    "occurrence-policies", "operations", "profiles", "mappings", "traces",
    "experiments", "findings", "relation-objects", "claims", "reductions",
    "events", "research-situations", "seeds", "inquiry-catalogs",
    "inquiry-reviews", "descriptive-catalogs",
)


def collect_release(
    workspace: Path,
    version: str,
    study_id: str,
    corpus_snapshot: dict,
    operations: list[dict] | None = None,
    record_payloads: dict[str, list[dict]] | None = None,
    field_charter: str = "",
    field_scope: dict | None = None,
) -> Path:
    """Stage `releases/vX.Y.Z/` with the full §6.7 layout and return the
    release directory. Refuses an existing directory (atomic rename comes
    in T12; staging happens in a temp sibling and is renamed into place
    only after verify — here we refuse if the TARGET exists)."""
    workspace = Path(workspace)
    target = workspace / "releases" / f"v{version}"
    if target.exists():
        raise FileExistsError(f"release directory already exists: {target}")

    payloads = record_payloads or {}
    ops = operations or []

    # stage in temp sibling, rename at the end (T12 adds verify before rename)
    import tempfile

    staging = Path(tempfile.mkdtemp(prefix=".release-stage-", dir=workspace))
    try:
        records_dir = staging / "records"
        records_dir.mkdir(parents=True)
        for rtype in RELEASE_RECORD_TYPES:
            rows = payloads.get(rtype, ops if rtype == "operations" else [])
            with (records_dir / f"{rtype}.jsonl").open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

        field_dir = staging / "field"
        field_dir.mkdir()
        (field_dir / "charter.yml").write_text(field_charter or "", encoding="utf-8")
        (field_dir / "scope.json").write_text(
            json.dumps(field_scope or {}, ensure_ascii=False, indent=1), encoding="utf-8"
        )

        prov = staging / "provenance"
        prov.mkdir()
        (prov / "corpus-snapshot.json").write_text(
            json.dumps(corpus_snapshot, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        (prov / "software-environment.json").write_text(
            json.dumps({"python": __import__("sys").version}, indent=1), encoding="utf-8"
        )

        release_json = {
            "schema_version": RELEASE_SCHEMA_VERSION,
            "study_id": study_id,
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "corpus_snapshot_id": corpus_snapshot.get("snapshot_id"),
            "record_counts": {
                rt: len(payloads.get(rt, ops if rt == "operations" else []))
                for rt in RELEASE_RECORD_TYPES
            },
            "manifest": "manifest.sha256",
            "report_markdown": "report.md",
            "report_html": "report.html",
        }
        (staging / "release.json").write_text(
            json.dumps(release_json, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        # T11 renders real reports from staged records only; T10 writes
        # explicit placeholders so the layout is complete and the files
        # are hash-covered from day one.
        (staging / "report.md").write_text(
            f"# Research Release v{version}\n\n(staged — rendering in T11)\n",
            encoding="utf-8",
        )
        (staging / "report.html").write_text(
            f"<h1>Research Release v{version}</h1>", encoding="utf-8"
        )

        # manifest: every file except itself, relative paths + sha256
        manifest_lines = []
        for f in sorted(p for p in staging.rglob("*") if p.is_file()):
            rel = str(f.relative_to(staging)).replace("\\", "/")
            manifest_lines.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}")
        (staging / "manifest.sha256").write_text(
            "\n".join(manifest_lines) + "\n", encoding="utf-8"
        )

        target.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(target)
        return target
    finally:
        if staging.exists():
            import shutil

            shutil.rmtree(staging, ignore_errors=True)
