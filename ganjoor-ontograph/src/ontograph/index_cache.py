"""Corpus-root-keyed SQLite index cache (ledger row P9.2).

Every CLI verb used to do a full `scan_corpus()` + re-parse/re-tokenize
from scratch on each invocation (~60–90s on the real corpus before any
query work; ledger row P9.2). This module makes the already-proven
`corpus.build_index()` (Phase 1, proven against the real corpus in P8.1)
actually reusable: the derived SQLite index is stored on disk under a
deterministic path derived from the corpus root plus a *content signal*,
so a second invocation with the same corpus content reopens it in
seconds instead of rebuilding.

Cache-key discipline (the one genuinely novel engineering risk of
Phase 9 — plan risk #4: "a cache that serves stale or wrong-scoped
results would silently corrupt every downstream number"):

- The key is a SHA-256 over a composite content signal: the resolved
  corpus root path, the manifest.json SHA-256, the poem file count, and
  a cheap per-shard (per-poet-directory) fingerprint. **Never mtime
  alone**: the shard fingerprint is a hash over (relative path, size,
  mtime_ns) of every file in the shard, so a content edit that keeps
  size and mtime, a copy that changes mtime but not content, and a
  renamed shard all resolve correctly.
- Before serving a cached index, the *current* signal is recomputed and
  compared against the signal stored in the cache's meta file at build
  time. Any mismatch (changed manifest, added/removed/edited poem, a
  different corpus root entirely) misses the cache and triggers a full
  rebuild. Stale results are never served.

The cached index itself is opened read-only: like `corpus.py`, this
module treats upstream JSON as the source of truth and the derived
index as rebuildable infrastructure (spec §57) — nothing ever writes to
an existing cache entry.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from ontograph.anchors import AnchorHit, LexicalAnchor
from ontograph.corpus import build_index
from ontograph.field import PoemRecord
from ontograph.normalize import normalize

CACHE_SCHEMA_VERSION = 1

# Env override so a test (or a user) can point the cache somewhere
# ephemeral; default lives under the user's own cache dir, shared across
# studies and workspaces — the corpus content is the key, not the study.
_ENV_CACHE_DIR = "ONTOGRAPH_INDEX_CACHE_DIR"


def default_cache_dir() -> Path:
    env = os.environ.get(_ENV_CACHE_DIR)
    if env:
        return Path(env)
    return Path.home() / ".cache" / "ontograph" / "index-cache"


def _shard_fingerprint(root: Path) -> str:
    """Cheap per-shard (per-poet-directory) content fingerprint: stat-only
    (no file reads) — a hash over each file's relative path, size, and
    mtime_ns. Deliberately NOT mtime alone: size and path participate,
    and the signal as a whole also includes the manifest hash and poem
    file count (see `content_signal`)."""
    parts: list[bytes] = []
    for poet_dir in sorted(root.glob("poets/*")):
        if not poet_dir.is_dir():
            continue
        for f in sorted(poet_dir.rglob("*")):
            if not f.is_file():
                continue
            st = f.stat()
            rel = str(f.relative_to(root)).replace("\\", "/")
            parts.append(f"{rel}\0{st.st_size}\0{st.st_mtime_ns}\0".encode("utf-8"))
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()


def content_signal(root: str | Path) -> dict:
    """The composite content signal the cache key is derived from."""
    root = Path(root)
    manifest_bytes = (root / "manifest.json").read_bytes()
    poem_files = [
        p for p in root.glob("poets/*/**/*.json")
        if p.name not in ("poet.json", "_cat.json")
    ]
    return {
        "root": str(root.resolve()),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "poem_file_count": len(poem_files),
        "shard_fingerprint": _shard_fingerprint(root),
    }


def cache_key(root: str | Path, signal: dict | None = None) -> str:
    if signal is None:
        signal = content_signal(root)
    blob = json.dumps(signal, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


def _cache_paths(root: str | Path, cache_dir: Path, signal: dict | None = None) -> tuple[Path, Path]:
    key = cache_key(root, signal)
    base = f"index-{key}-v{CACHE_SCHEMA_VERSION}"
    return cache_dir / f"{base}.sqlite", cache_dir / f"{base}.meta.json"


def _open_read_only(db_path: Path):
    import sqlite3
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def get_or_build_index(
    root: str | Path, cache_dir: str | Path | None = None
) -> tuple[object, dict, bool]:
    """Return (connection, build_manifest, cache_hit) for `root`'s derived
    index, building it once via `corpus.build_index()` if no valid cache
    entry exists. The connection is opened READ-ONLY on the cached file —
    callers query it, never mutate it.

    `cache_hit` is False exactly when the index was (re)built this call.
    Raises FileNotFoundError (via `content_signal`) when `root` has no
    manifest.json — a missing corpus is an error, never an empty cache."""
    root = Path(root)
    cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    signal = content_signal(root)  # computed once; the fingerprint stat
    # pass over 132k+ files is the dominant warm-open cost — never paid twice
    db_path, meta_path = _cache_paths(root, cache_dir, signal)

    if db_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = None
        if (
            isinstance(meta, dict)
            and meta.get("cache_schema_version") == CACHE_SCHEMA_VERSION
            and meta.get("signal") == signal
        ):
            return _open_read_only(db_path), meta["build_manifest"], True

    # Miss (no entry, corrupt meta, or content changed) → full rebuild.
    fd, tmp_name = tempfile.mkstemp(prefix="ontograph-index-", suffix=".sqlite", dir=str(cache_dir))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        conn, build_manifest = build_index(root, db_path=str(tmp_path))
        conn.close()
        meta = {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "signal": signal,
            "build_manifest": build_manifest,
        }
        os.replace(tmp_path, db_path)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return _open_read_only(db_path), build_manifest, False


# --- index-backed records and census (ledger row P9.3's substrate) ---
#
# Both functions reproduce `field.scan_corpus`'s and `anchors.census`'s
# exact result ORDER, not just their content: `calibration_sample` is
# seed-position-sensitive, so a reordered hit list would silently change
# which hits a fixed-seed calibrate sample draws — fixture numbers must
# not change at all when verbs are rewired onto the cache.

def records_from_index(conn) -> list[PoemRecord]:
    """PoemRecord list equivalent to `scan_corpus(root)`'s, served from the
    cached index (a cheap SELECT, not a re-scan of 130k+ JSON files).
    Ordered by source path exactly as `scan_corpus`'s sorted glob is, and
    carrying the same (poem_id, poet_slug, poet_id, cat_id, path)."""
    rows = conn.execute(
        "SELECT id, poet_id, cat_id, source_path FROM poems"
    ).fetchall()
    records = [
        PoemRecord(
            poem_id=poem_id,
            poet_slug=Path(source_path).parts[Path(source_path).parts.index("poets") + 1],
            poet_id=poet_id,
            cat_id=cat_id,
            path=Path(source_path),
        )
        for poem_id, poet_id, cat_id, source_path in rows
    ]
    records.sort(key=lambda r: r.path)  # scan_corpus's own ordering
    return records


def census_from_index(conn, records: list[PoemRecord], anchors: list[LexicalAnchor]) -> list[AnchorHit]:
    """Token-level anchor census (spec §27.1) served from the cached
    index's token_offsets table instead of re-reading/re-tokenizing every
    poem JSON. Matching semantics are identical to `anchors.census`:
    approved anchors only, anchor forms normalized before comparison,
    token-exact (never substring — the 9107 `آینه‌بند` guard must not
    regress). Hit ORDER is identical to `anchors.census` too: records in
    `scan_corpus` order; within a poem, verse order then token_index
    order; within a token, `forms_by_object` insertion order."""
    approved = [a for a in anchors if a.status == "approved"]
    forms_by_object: dict[str, set[str]] = {}
    for a in approved:
        forms_by_object.setdefault(a.object_address, set()).add(normalize(a.form).normalized)

    all_forms = sorted({f for forms in forms_by_object.values() for f in forms})
    hits_by_poem: dict[int, list[AnchorHit]] = {}
    if all_forms:
        placeholders = ",".join("?" for _ in all_forms)
        rows = conn.execute(
            "SELECT t.poem_id, t.vorder, t.token_index, t.token_text, "
            "t.start_offset, t.end_offset, v.couplet_index, v.position, "
            "v.text, n.normalized_text "
            "FROM token_offsets t "
            "JOIN verses v ON v.poem_id = t.poem_id AND v.vorder = t.vorder "
            "JOIN normalized_verses n ON n.poem_id = t.poem_id AND n.vorder = t.vorder "
            f"WHERE t.token_text IN ({placeholders}) "
            "ORDER BY t.poem_id, t.vorder, t.token_index",
            all_forms,
        ).fetchall()
        for (poem_id, _vorder, token_index, token_text, start, end,
             couplet_index, position, text, normalized_text) in rows:
            for object_address, forms in forms_by_object.items():
                if token_text in forms:
                    hits_by_poem.setdefault(poem_id, []).append(
                        AnchorHit(
                            object_address=object_address,
                            lexical_anchor=token_text,
                            poem_id=poem_id,
                            couplet_index=couplet_index,
                            position=position,
                            original_text=text,
                            normalized_text=normalized_text,
                            token_start=start,
                            token_end=end,
                        )
                    )

    hits: list[AnchorHit] = []
    for record in records:  # scan_corpus ordering, per poem
        hits.extend(hits_by_poem.get(record.poem_id, []))
    return hits
