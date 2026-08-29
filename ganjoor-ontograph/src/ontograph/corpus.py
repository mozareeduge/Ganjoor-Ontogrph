"""CorpusSnapshot loading and pin verification.

Spec §56 (Source layer): the pinned Ganjoor repository is the documentary
source of truth. This module records, for a corpus root, the exact
manifest hash (and, when supplied by the caller, the git commit that root
was checked out at) and never modifies upstream JSON -- this module has no
write path at all.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CorpusSnapshot:
    """A pinned, read-only view of one corpus root's manifest.json.

    `commit` is the git commit SHA the caller asserts this root was checked
    out at (spec §56's "exact commit/build identity"). This module cannot
    verify that claim itself -- it has no git dependency -- so a caller
    that cares about the claim being true should pass a SHA it obtained
    from `git rev-parse HEAD` on the same root, not an assumed value.
    """

    root: Path
    manifest: dict
    manifest_sha256: str
    commit: str | None = None

    @property
    def poets_count(self) -> int:
        return self.manifest["PoetsCount"]

    @property
    def poems_count(self) -> int:
        return self.manifest["PoemsCount"]

    @property
    def schema_version(self) -> int:
        return self.manifest["SchemaVersion"]

    @property
    def generated_at_utc(self) -> str:
        return self.manifest["GeneratedAtUtc"]


def load_corpus_snapshot(root: str | Path, commit: str | None = None) -> CorpusSnapshot:
    """Load `manifest.json` from `root` and hash it (spec §56 manifest
    SHA-256 requirement). Raises FileNotFoundError if `root/manifest.json`
    does not exist -- there is no silent fallback to an assumed shape."""
    root = Path(root)
    manifest_path = root / "manifest.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return CorpusSnapshot(root=root, manifest=manifest, manifest_sha256=digest, commit=commit)
