"""G20 (L3.1): corpus_snapshot() uses the same clean-git fast path
index_cache.cache_identity() already has, instead of unconditionally
reading and SHA-256ing every poem file's bytes (measured 780s cold on
the real ~132K-file corpus).

Uses a genuinely controlled, isolated git repo (not this repo's own
live status, which is fragile mid-session) to make the clean/dirty
distinction deterministic.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ontograph.corpus import corpus_snapshot


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _make_mini_corpus(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({"schema": "1.0"}), encoding="utf-8")
    poet_dir = root / "poets" / "testpoet"
    poet_dir.mkdir(parents=True)
    (poet_dir / "1.json").write_text(json.dumps({
        "Id": 1, "Title": "t", "Verses": [
            {"Text": "آینه در دست من است", "VOrder": 1, "CoupletIndex": 0, "Position": "Right"},
        ],
    }), encoding="utf-8")


def _make_clean_git_corpus(tmp_path: Path) -> Path:
    root = tmp_path / "clean-corpus"
    _make_mini_corpus(root)
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "-A")
    _git(root, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return root


def test_clean_git_corpus_uses_the_fast_path_never_reads_poem_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_clean_git_corpus(tmp_path)

    def _explode(*a, **kw):
        raise AssertionError("corpus_content_signal (full byte-hash walk) must NOT run on a clean-git corpus")

    import ontograph.corpus as corpus_mod

    monkeypatch.setattr(corpus_mod, "corpus_content_signal", _explode)

    snap = corpus_snapshot(root)
    assert snap.content_signal.startswith("git:")
    assert snap.commit is not None


def test_dirty_git_corpus_still_uses_the_correct_full_signal(tmp_path: Path) -> None:
    root = _make_clean_git_corpus(tmp_path)
    (root / "poets" / "testpoet" / "1.json").write_text(json.dumps({
        "Id": 1, "Title": "t-edited", "Verses": [],
    }), encoding="utf-8")  # uncommitted edit -> dirty tree

    snap = corpus_snapshot(root)
    assert not snap.content_signal.startswith("git:")  # real fallback hash, not the cheap stand-in
    assert len(snap.content_signal) == 64  # a real sha256 hexdigest


def test_non_git_corpus_still_uses_the_correct_full_signal(tmp_path: Path) -> None:
    root = tmp_path / "no-git-corpus"
    _make_mini_corpus(root)
    snap = corpus_snapshot(root)
    assert not snap.content_signal.startswith("git:")
    assert snap.commit is None


def test_snapshot_id_is_deterministic_for_the_same_clean_corpus(tmp_path: Path) -> None:
    root = _make_clean_git_corpus(tmp_path)
    a = corpus_snapshot(root)
    b = corpus_snapshot(root)
    assert a.snapshot_id == b.snapshot_id


def test_snapshot_id_changes_when_content_actually_changes(tmp_path: Path) -> None:
    root = _make_clean_git_corpus(tmp_path)
    before = corpus_snapshot(root)
    (root / "poets" / "testpoet" / "1.json").write_text(json.dumps({
        "Id": 1, "Title": "different", "Verses": [],
    }), encoding="utf-8")
    _git(root, "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "-A")
    _git(root, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "edit")
    after = corpus_snapshot(root)
    assert before.snapshot_id != after.snapshot_id
