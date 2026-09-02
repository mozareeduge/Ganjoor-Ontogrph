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

    T04 additions: `content_signal` (content hash over poem files) and
    `snapshot_id` (content-identity id per spec §6.1) are populated by
    `corpus_snapshot()`; a bare `load_corpus_snapshot()` leaves them None.
    """

    root: Path
    manifest: dict
    manifest_sha256: str
    commit: str | None = None
    content_signal: str | None = None
    poem_count: int | None = None
    snapshot_id: str | None = None

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


# --- T04: content-identity snapshot ID + content signal ---

def corpus_content_signal(root: str | Path) -> str:
    """Content signal (spec §6.1): a deterministic hash over the corpus's
    poem JSON content, independent of absolute paths and mtimes. Cheap
    walk: per-poem-file SHA-256 folded in sorted-relative-path order."""
    root = Path(root)
    h = hashlib.sha256()
    poem_files = sorted(
        p for p in root.glob("poets/*/**/*.json")
        if p.name not in ("poet.json", "_cat.json")
    )
    for p in poem_files:
        rel = str(p.relative_to(root)).replace("\\", "/")
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def corpus_snapshot(root: str | Path) -> "CorpusSnapshot":
    """Content-identity snapshot (spec §6.1, T04): snapshot_id =
    `cs1-` + first 24 lowercase hex of SHA-256 over
    commit-or-none + NUL + manifest-sha256 + NUL + content-signal-sha256.
    Absolute corpus paths are metadata, not identity, so a portable clean
    copy receives the SAME id. The commit is read from the root's own git
    metadata when available; `None` when the root is not a git checkout."""
    root = Path(root)
    snap = load_corpus_snapshot(root)
    try:
        import subprocess

        commit = (
            subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True, timeout=15,
            ).stdout.strip()
            or None
        )
    except Exception:
        commit = None
    signal = corpus_content_signal(root)
    identity = "\x00".join(
        [commit or "none", snap.manifest_sha256, signal]
    ).encode("utf-8")
    snapshot_id = "cs1-" + hashlib.sha256(identity).hexdigest()[:24]
    return CorpusSnapshot(
        root=root,
        manifest=snap.manifest,
        manifest_sha256=snap.manifest_sha256,
        commit=commit,
        content_signal=signal,
        poem_count=len(list(root.glob("poets/*/**/*.json")))
        - _non_poem_json_count(root),
        snapshot_id=snapshot_id,
    )


def _non_poem_json_count(root: Path) -> int:
    reserved = {"poet.json", "_cat.json"}
    return sum(
        1
        for p in root.glob("poets/*/**/*.json")
        if p.name in reserved
    )


# --- Derived SQLite research index (spec §57) ---
#
# "Derived infrastructure ... not treated as source evidence" -- rebuilt
# from the pinned JSON, never itself edited. Every row's primary key is
# the same poem_id/vorder the upstream JSON already uses, which IS the
# link back to a source address (spec §57: "a manifest linking every
# derived row to upstream source addresses") -- no separate provenance
# table is needed on top of that.
#
# `sections` has no primary key, deliberately: a real-corpus rebuild
# (Phase 8, ledger row P8.1) found `Section.Index` is not even unique
# within one poem across `SectionType`s -- e.g. poem 142187 has a
# `WholePoem` section AND a `Couplet` section both at `Index: 2`. Widening
# a candidate key to (poem_id, idx, section_type) still collided 3,586
# times across the real corpus. This extends P0.5's finding that
# `SectionIndex1` cannot identify per-couplet sections in epic-format
# poems: `Section.Index` itself is not a reliable per-poem identifier
# either, for any `PoemFormat`. `CoupletIndex` on `verses` remains the
# only reliable per-verse key -- `sections` rows are kept for their
# `plain_text`/`section_type` content, addressed by `poem_id` alone, not
# treated as individually addressable by `idx`.

import sqlite3  # noqa: E402  (grouped here, next to its only use, not at module top)

from ontograph.field import scan_corpus, scan_poets  # noqa: E402
from ontograph.normalize import normalize, tokenize  # noqa: E402

_SCHEMA = """
CREATE TABLE poets (
    id INTEGER PRIMARY KEY, slug TEXT, name TEXT,
    birth_year_lunar_hijri INTEGER, death_year_lunar_hijri INTEGER
);
CREATE TABLE poems (
    id INTEGER PRIMARY KEY, poet_id INTEGER, cat_id INTEGER, title TEXT, source_path TEXT
);
CREATE TABLE sections (
    poem_id INTEGER, idx INTEGER, section_type TEXT, verse_type TEXT,
    couplets_count INTEGER, plain_text TEXT
);
CREATE INDEX sections_poem_id_idx ON sections (poem_id);
CREATE TABLE verses (
    poem_id INTEGER, vorder INTEGER, position TEXT, text TEXT,
    couplet_index INTEGER, section_index1 INTEGER,
    PRIMARY KEY (poem_id, vorder)
);
CREATE TABLE couplets (
    poem_id INTEGER, couplet_index INTEGER, right_vorder INTEGER, left_vorder INTEGER,
    PRIMARY KEY (poem_id, couplet_index)
);
CREATE TABLE normalized_verses (
    poem_id INTEGER, vorder INTEGER, normalized_text TEXT, profile_version TEXT,
    PRIMARY KEY (poem_id, vorder)
);
CREATE TABLE token_offsets (
    poem_id INTEGER, vorder INTEGER, token_index INTEGER, token_text TEXT,
    start_offset INTEGER, end_offset INTEGER,
    PRIMARY KEY (poem_id, vorder, token_index)
);
"""


def build_index(root: str | Path, db_path: str = ":memory:") -> tuple[sqlite3.Connection, dict]:
    """Rebuild the derived SQLite index from `root`'s pinned JSON.

    Returns (connection, build_manifest) where build_manifest carries a
    row count per table -- a caller compares these against the source
    manifest's own PoetsCount/PoemsCount (spec §57's "assert row counts
    match manifest counts exactly", ledger row P1.6's Verify)."""
    root = Path(root)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)

    poet_rows = 0
    for p in scan_poets(root):
        conn.execute(
            "INSERT INTO poets VALUES (?, ?, ?, ?, ?)",
            (p.poet_id, p.slug, p.slug, p.birth_year_lunar_hijri, p.death_year_lunar_hijri),
        )
        poet_rows += 1

    poem_rows = section_rows = verse_rows = couplet_rows = normalized_rows = token_rows = 0
    for record in scan_corpus(root):
        poem = json.loads(record.path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO poems VALUES (?, ?, ?, ?, ?)",
            (poem["Id"], record.poet_id, poem["CatId"], poem["Title"], str(record.path)),
        )
        poem_rows += 1

        for s in poem["Sections"]:
            conn.execute(
                "INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?)",
                (poem["Id"], s["Index"], s["SectionType"], s.get("VerseType"),
                 s["CoupletsCount"], s.get("PlainText")),
            )
            section_rows += 1

        couplets: dict[int, dict[str, int]] = {}
        for v in poem["Verses"]:
            couplet_index = v.get("CoupletIndex")  # None for a Position="Comment"
            # prose-commentary verse in the real corpus -- ~647 poems (e.g.
            # Osmani's Qushayriyya, Araqi's Lama'at) carry these; spec §24:
            # not silently forced into couplet logic. Still indexed as a
            # verse/normalized_verse/token row (its content is not dropped),
            # just excluded from the couplets table below.
            conn.execute(
                "INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?)",
                (poem["Id"], v["VOrder"], v["Position"], v["Text"],
                 couplet_index, v.get("SectionIndex1")),
            )
            verse_rows += 1
            if couplet_index is not None:
                couplets.setdefault(couplet_index, {})[v["Position"]] = v["VOrder"]

            nt = normalize(v["Text"])
            conn.execute(
                "INSERT INTO normalized_verses VALUES (?, ?, ?, ?)",
                (poem["Id"], v["VOrder"], nt.normalized, nt.profile_version),
            )
            normalized_rows += 1

            for i, (tok, start, end) in enumerate(tokenize(nt.normalized)):
                conn.execute(
                    "INSERT INTO token_offsets VALUES (?, ?, ?, ?, ?, ?)",
                    (poem["Id"], v["VOrder"], i, tok, start, end),
                )
                token_rows += 1

        for ci, positions in couplets.items():
            conn.execute(
                "INSERT INTO couplets VALUES (?, ?, ?, ?)",
                (poem["Id"], ci, positions.get("Right"), positions.get("Left")),
            )
            couplet_rows += 1

    conn.commit()
    build_manifest = {
        "poets": poet_rows,
        "poems": poem_rows,
        "sections": section_rows,
        "verses": verse_rows,
        "couplets": couplet_rows,
        "normalized_verses": normalized_rows,
        "token_offsets": token_rows,
    }
    return conn, build_manifest
