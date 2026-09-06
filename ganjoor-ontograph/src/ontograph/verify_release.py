"""Ledger row T12: standalone release verification (spec §6.7, T12).

`verify_release(directory)` imports NO workspace readers. It checks:
- manifest.sha256 lists every file in the directory except itself, and
  nothing that doesn't exist;
- every listed hash matches the file's bytes;
- release.json parses and references only internal relative paths.
Any mismatch fails with the offending relative path(s) in `issues`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_release(release_dir: Path) -> dict:
    """Standalone verification. Never touches a workspace."""
    release_dir = Path(release_dir)
    issues: list[str] = []
    manifest_path = release_dir / "manifest.sha256"
    if not manifest_path.exists():
        return {"valid": False, "issues": ["manifest.sha256 missing"], "files_checked": 0}

    listed: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        listed[rel] = digest

    actual = {
        str(f.relative_to(release_dir)).replace("\\", "/")
        for f in release_dir.rglob("*")
        if f.is_file()
    }
    for missing in sorted(set(listed) - actual):
        issues.append(f"listed file missing: {missing}")
    for extra in sorted(actual - set(listed) - {"manifest.sha256"}):
        issues.append(f"unlisted file present: {extra}")

    files_checked = 0
    for rel, digest in sorted(listed.items()):
        f = release_dir / rel
        if not f.exists():
            continue
        files_checked += 1
        actual_digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if actual_digest != digest:
            issues.append(f"hash mismatch: {rel}")

    # release.json must parse and reference only internal relative paths
    rj_path = release_dir / "release.json"
    if rj_path.exists():
        try:
            rj = json.loads(rj_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            issues.append(f"release.json unparseable: {e}")
            rj = None
        if rj is not None:
            text = json.dumps(rj)
            for bad in ("C:\\", "C:/", "file://"):
                if bad in text:
                    issues.append(f"release.json contains non-internal reference: {bad}")
            for ref_key in ("manifest", "report_markdown", "report_html"):
                ref = rj.get(ref_key)
                if ref and (release_dir / ref).exists() is False:
                    issues.append(f"release.json reference missing: {ref_key}={ref}")

    # W09A (§19.7): inquiry reference integrity — reviews cite live
    # catalogs, catalogs cite existing situations, governed operations
    # cite existing situations. These checks read ONLY release content.
    def _rows(rel: str) -> list[dict]:
        p = release_dir / "records" / f"{rel}.jsonl"
        if not p.exists():
            return []
        return [
            json.loads(l)
            for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
        ]

    catalogs = _rows("inquiry-catalogs")
    reviews = _rows("inquiry-reviews")
    situations = _rows("research-situations")
    operations = _rows("operations")

    situation_ids = {r.get("id") for r in situations}
    for cat in catalogs:
        if cat.get("situation_id") and cat["situation_id"] not in situation_ids:
            issues.append(
                f"inquiry-catalog cites missing situation: {cat.get('id')}"
            )
    catalog_ids = {r.get("id") for r in catalogs}
    for rev in reviews:
        if rev.get("catalog_id") and rev["catalog_id"] not in catalog_ids:
            issues.append(
                f"inquiry-review cites missing catalog: {rev.get('catalog_id')}"
            )
    for op in operations:
        if op.get("inquiry_status") == "governed" and op.get("situation_id") \
                and op["situation_id"] not in situation_ids:
            issues.append(
                f"governed operation cites missing situation: {op.get('id')}"
            )

    return {"valid": not issues, "issues": issues, "files_checked": files_checked}
