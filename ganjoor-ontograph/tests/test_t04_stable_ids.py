"""Ledger row T04: verse order, CorpusSnapshot, stable hit IDs.

Discriminating targets (execution spec §6.1/§6.3, T04 row):

1. CorpusSnapshot ID is deterministic content identity: `cs1-` + first
   24 hex of SHA-256 over commit-or-none + NUL + manifest-sha256 + NUL +
   content-signal-sha256. A portable CLEAN COPY of the same corpus at a
   different path gets the SAME snapshot id (absolute paths are metadata,
   not identity).
2. AnchorHit IDs are stable across warm/cold runs: `ah1-` + 24 hex of
   SHA-256 over the §6.3 field tuple. Same corpus + same anchor state ->
   same hit IDs on two independent engine runs.
3. verse_order is source VOrder; hit ID changes when matcher_version
   changes (corpus/matcher changes INTENTIONALLY change IDs).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ontograph.anchors import LexicalAnchor, census
from ontograph.corpus import corpus_snapshot
from ontograph.field import scan_corpus


@pytest.fixture()
def fixture_root(tmp_path: Path) -> Path:
    src = Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"
    root = tmp_path / "corpusA"
    shutil.copytree(src, root)
    return root


def test_snapshot_id_is_content_identity_not_path(fixture_root: Path, tmp_path: Path) -> None:
    snap_a = corpus_snapshot(fixture_root)
    copy = tmp_path / "elsewhere" / "corpusB"
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture_root, copy)
    snap_b = corpus_snapshot(copy)
    assert snap_a.snapshot_id == snap_b.snapshot_id, (
        "a portable clean copy must receive the same snapshot id"
    )
    assert snap_a.snapshot_id.startswith("cs1-")
    assert len(snap_a.snapshot_id) == len("cs1-") + 24
    assert snap_a.poem_count == 27


def test_snapshot_id_changes_with_content(fixture_root: Path) -> None:
    snap_a = corpus_snapshot(fixture_root)
    poem = fixture_root / "poets" / "sample1" / "ghazal" / "p9101.json"
    data = json.loads(poem.read_text(encoding="utf-8"))
    data["Verses"][0]["Text"] = "آینه در دست تو است امشب"
    poem.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    snap_b = corpus_snapshot(fixture_root)
    assert snap_a.snapshot_id != snap_b.snapshot_id


def test_hit_ids_stable_across_runs_and_sensitive_to_matcher(fixture_root: Path) -> None:
    records = scan_corpus(fixture_root)
    anchors = [LexicalAnchor(object_address="mirror", form="آینه", match_mode="exact")]
    hits1 = census(records, anchors)
    hits2 = census(scan_corpus(fixture_root), anchors)
    ids1 = {h.id for h in hits1}
    ids2 = {h.id for h in hits2}
    assert ids1 == ids2 and len(ids1) == len(hits1), "warm/cold identity"
    assert all(h.id.startswith("ah1-") and len(h.id) == len("ah1-") + 24 for h in hits1)
    assert all(h.verse_order is not None for h in hits1)
    assert all(h.corpus_snapshot_id == corpus_snapshot(fixture_root).snapshot_id for h in hits1)

    # matcher change intentionally changes IDs
    from dataclasses import replace
    from ontograph.anchors import AnchorHit, MATCHER_VERSION

    h = hits1[0]
    bumped = replace(h, matcher_version="9.9.9")
    assert bumped.id != h.id
    # same tuple -> same id (determinism, not time)
    again = replace(h, matcher_version="9.9.9")
    assert again.id == bumped.id
