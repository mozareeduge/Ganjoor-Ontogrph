"""Tests for ontograph.corpus (ledger row P0.4)."""
import pathlib

from ontograph.corpus import load_corpus_snapshot

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"


def test_loads_fixture_manifest():
    snap = load_corpus_snapshot(FIXTURE_ROOT)
    assert snap.poets_count == 4
    assert snap.poems_count == 27
    assert snap.schema_version == 1
    assert len(snap.manifest_sha256) == 64  # sha256 hex digest length


def test_manifest_hash_is_reproducible():
    a = load_corpus_snapshot(FIXTURE_ROOT)
    b = load_corpus_snapshot(FIXTURE_ROOT)
    assert a.manifest_sha256 == b.manifest_sha256


def test_missing_manifest_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_corpus_snapshot(FIXTURE_ROOT / "does-not-exist")


def test_commit_is_caller_supplied_not_verified():
    snap = load_corpus_snapshot(FIXTURE_ROOT, commit="deadbeef")
    assert snap.commit == "deadbeef"
