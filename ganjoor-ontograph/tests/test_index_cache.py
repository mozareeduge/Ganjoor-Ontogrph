"""Tests for ontograph.index_cache (ledger row P9.2).

The cache-invalidation discipline is the point: a cache that serves stale
or wrong-scoped results would silently corrupt every downstream number
(Phase 9 plan risk #4). Everything here keys on corpus CONTENT, never
mtime alone, and every miss path is exercised against a fixture COPY, so
the checked-in fixture itself is never mutated.
"""
import json
import pathlib
import shutil

import pytest

from ontograph.anchors import LexicalAnchor, census as scan_census
from ontograph.field import scan_corpus
from ontograph.index_cache import (
    cache_key,
    census_from_index,
    content_signal,
    get_or_build_index,
    records_from_index,
)

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

MIRROR = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]


@pytest.fixture()
def corpus_copy(tmp_path):
    """A writable copy of the fixture — invalidation tests edit this, never
    the checked-in fixture."""
    dest = tmp_path / "corpus-copy"
    shutil.copytree(FIXTURE_ROOT, dest)
    return dest


def _copy_cache_dir(tmp_path):
    return tmp_path / "index-cache"


# --- warm-cache reuse: same root, same content → hit, no rebuild ---

def test_second_call_with_same_root_is_a_cache_hit(tmp_path, corpus_copy):
    cache_dir = _copy_cache_dir(tmp_path)
    conn1, manifest1, hit1 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit1 is False  # cold: built
    records1 = records_from_index(conn1)
    conn1.close()

    conn2, manifest2, hit2 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit2 is True  # warm: served from cache
    assert manifest2 == manifest1
    assert records_from_index(conn2) == records1
    conn2.close()


def test_index_backed_census_matches_scan_census_exactly(tmp_path, corpus_copy):
    """Same hits, same order, as the file-walking census — order matters
    because calibration_sample is seed-position-sensitive."""
    cache_dir = _copy_cache_dir(tmp_path)
    conn, _, _ = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    records = scan_corpus(corpus_copy)
    from_cache = census_from_index(conn, records_from_index(conn), MIRROR)
    from_scan = scan_census(records, MIRROR)
    assert from_cache == from_scan
    # and genuinely the same hits the fixture ground truth knows (7)
    assert len(from_cache) == 7
    conn.close()


def test_cache_key_differs_for_different_roots(tmp_path, corpus_copy):
    other = tmp_path / "other-root"
    shutil.copytree(FIXTURE_ROOT, other)
    assert cache_key(corpus_copy) != cache_key(other)


# --- invalidation: changed content or changed root must never serve stale ---

def test_edited_poem_invalidates_cache_and_new_hit_is_served(tmp_path, corpus_copy):
    cache_dir = _copy_cache_dir(tmp_path)
    conn1, _, _ = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert len(census_from_index(conn1, records_from_index(conn1), MIRROR)) == 7
    conn1.close()

    # Edit a poem: add a verse carrying the mirror anchor into a poem that
    # had none (poem 9301 lives in sample3, outside the mirror poems).
    poem_path = next(
        p for p in (corpus_copy / "poets" / "sample3").rglob("*.json")
        if p.name not in ("poet.json", "_cat.json")
    )
    poem = json.loads(poem_path.read_text(encoding="utf-8"))
    poem["Verses"].append({"VOrder": 99, "Position": "Right", "Text": "تست آینه",
                           "CoupletIndex": 99, "SectionIndex1": None})
    poem_path.write_text(json.dumps(poem, ensure_ascii=False), encoding="utf-8")

    conn2, _, hit2 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit2 is False  # content changed → rebuild, never stale service
    hits = census_from_index(conn2, records_from_index(conn2), MIRROR)
    assert len(hits) == 8  # the edited verse's anchor is now censused
    assert any(h.poem_id == poem["Id"] for h in hits)
    conn2.close()


def test_changed_manifest_invalidates_cache(tmp_path, corpus_copy):
    cache_dir = _copy_cache_dir(tmp_path)
    conn1, _, hit1 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    conn1.close()
    assert hit1 is False

    manifest_path = corpus_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["PoemsCount"] += 1  # what an upstream refresh would look like
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    conn2, _, hit2 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit2 is False  # manifest hash changed → miss
    conn2.close()


def test_renamed_shard_invalidates_cache_without_mtime_trickery(tmp_path, corpus_copy):
    """The fingerprint is over (path, size, mtime_ns) per file — never
    mtime alone — so a content-preserving rename must miss, and a pure
    mtime touch (size+path unchanged... path unchanged, but a touch alone
    must not corrupt anything either) is covered by the signal as a
    whole. Here: rename a poem file → different shard fingerprint."""
    cache_dir = _copy_cache_dir(tmp_path)
    conn1, _, _ = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    conn1.close()

    poem_path = next(
        p for p in (corpus_copy / "poets" / "sample3").rglob("*.json")
        if p.name not in ("poet.json", "_cat.json")
    )  # a real poem file, never the reserved poet.json/_cat.json
    poem_path.rename(poem_path.with_name("renamed-poem.json"))

    conn2, _, hit2 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit2 is False
    conn2.close()


def test_corrupt_meta_file_is_not_served(tmp_path, corpus_copy):
    cache_dir = _copy_cache_dir(tmp_path)
    conn1, _, _ = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    conn1.close()
    # Corrupt the meta sidecar (truncated write, etc.)
    meta = next(cache_dir.glob("*.meta.json"))
    meta.write_text("{not json", encoding="utf-8")
    conn2, _, hit2 = get_or_build_index(corpus_copy, cache_dir=cache_dir)
    assert hit2 is False  # rebuilt, not trusted
    conn2.close()


def test_content_signal_covers_manifest_count_and_shards(tmp_path, corpus_copy):
    signal = content_signal(corpus_copy)
    assert signal["poem_file_count"] > 0
    assert len(signal["manifest_sha256"]) == 64
    assert len(signal["shard_fingerprint"]) == 64
    assert signal["root"] == str(corpus_copy.resolve())
