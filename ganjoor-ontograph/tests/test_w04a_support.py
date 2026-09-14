"""Ledger row W04A (Amendment §19.3): corpus support + lexical-neighbor
computation over the cached index — PURE engine functions, no CLI.

Discriminating targets:

1. Supplied exact/phrase forms return hand-checked counts from the
   fixture corpus: 'آینه' has known anchor-level counts; a phrase
   'آینه و' matches only where the tokens are contiguous in one verse.
2. Zero support stays EXPLICIT: unsupported=False, hit_count=0 — never
   silently dropped or upgraded.
3. English tokens are not queried as Persian motifs (a latin form
   returns support_status='not-applicable' with a language note, not a
   zero that looks like a checked negative).
4. Lexical-neighbor proposals: for a verified seed form, neighbors are
   tokens co-occurring in the same verse, ordered by declared retrieval
   order (frequency) — never presented as relation strength.
5. Results pin snapshot/field/window versions; a changed snapshot
   stales the receipt.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.corpus import corpus_snapshot
from ontograph.corpus import build_index
import sqlite3
from ontograph.field import scan_corpus
from ontograph.inquiry_support import (
    compute_support,
    lexical_neighbors,
)


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    import shutil

    root = tmp_path_factory.mktemp("corpus") / "mini"
    shutil.copytree(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor", root)
    return root


@pytest.fixture(scope="module")
def index(corpus: Path):
    db = corpus / "idx.sqlite"
    build_index(corpus, db)
    conn = sqlite3.connect(db)
    yield conn
    conn.close()


def test_known_counts_for_exact_form(index, corpus: Path) -> None:
    snap = corpus_snapshot(corpus)
    out = compute_support(index, corpus, snap.snapshot_id, form="آینه", match_mode="exact")
    # fixture ground truth (token-aware): form 'آینه' = 6 hits over 6 poems
    # (9107's آینه‌بند is a ZWNJ compound = different token; 9104 is آیینه)
    assert out["support_status"] == "supported"
    assert out["hit_count"] == 6
    assert out["poem_count"] == 6
    assert out["evidence"], "supported requires located evidence"
    assert out["evidence"][0]["path"].startswith("poets/")


def test_phrase_support_contiguous_only(index, corpus: Path) -> None:
    snap = corpus_snapshot(corpus)
    out = compute_support(index, corpus, snap.snapshot_id, form="آینه و زنگار", match_mode="phrase")
    assert out["support_status"] == "supported"
    # poem 9201 v1: "آینه و زنگار در یک نفس" is the contiguous occurrence
    assert out["hit_count"] == 1


def test_zero_support_stays_explicit(index, corpus: Path) -> None:
    snap = corpus_snapshot(corpus)
    out = compute_support(index, corpus, snap.snapshot_id, form="قلمرو", match_mode="exact")
    assert out["support_status"] == "unsupported"
    assert out["hit_count"] == 0
    assert out["evidence"] == []


def test_english_form_is_not_applicable(index, corpus: Path) -> None:
    snap = corpus_snapshot(corpus)
    out = compute_support(index, corpus, snap.snapshot_id, form="mirror", match_mode="exact")
    assert out["support_status"] == "not-applicable"
    assert "non-persian" in " ".join(out.get("limitations", []))


def test_lexical_neighbors_declared_retrieval_order(index, corpus: Path) -> None:
    snap = corpus_snapshot(corpus)
    out = lexical_neighbors(index, corpus, snap.snapshot_id, seed_form="آینه", top_n=5)
    assert out["seed_form"] == "آینه"
    neighbors = out["neighbors"]
    assert 0 < len(neighbors) <= 5
    # ordered by frequency descending (declared retrieval order)
    counts = [n["count"] for n in neighbors]
    assert counts == sorted(counts, reverse=True)
    # the seed itself and stopword-ish tokens may appear; each neighbor
    # carries its count and at least one locating verse reference
    assert all("example_verse" in n for n in neighbors)
    assert all(n["token"] != "آینه" for n in neighbors)


def test_snapshot_change_stales_receipt(index, corpus: Path, tmp_path: Path) -> None:
    snap = corpus_snapshot(corpus)
    from ontograph.inquiry_support import receipt_valid

    assert receipt_valid(snap.snapshot_id, snap.snapshot_id) is True
    assert receipt_valid(snap.snapshot_id, "cs1-different") is False
