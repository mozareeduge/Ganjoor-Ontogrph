"""Regression test for a real-corpus crash found in Phase 8 (ledger row
P8.1): `build_index()` and `anchors.census()` both indexed `verse["CoupletIndex"]`
with bracket access, which raised `KeyError` the moment a real poem
contained a `Position: "Comment"` prose-commentary verse (no couplet at
all) -- ~647 real poems have at least one such verse (e.g. Osmani's
Qushayriyya, Araqi's Lama'at). This test reproduces that exact verse
shape without needing the real corpus, using the actual structure of
poets/eraghi/lamaat/sh13.json's verse 5 ("Comment", text "شعر", no
CoupletIndex key at all).
"""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.compare import MODE_ANCHOR, typed_coincidence
from ontograph.corpus import build_index
from ontograph.field import PoemRecord

MIRROR_ANCHORS = [LexicalAnchor(object_address="mirror", form="آینه")]


def _write_poem_with_comment_verse(tmp_path, poem_id, poet_slug="testpoet"):
    poet_dir = tmp_path / "poets" / poet_slug / "cat1"
    poet_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "poets" / poet_slug / "poet.json").write_text(
        json.dumps({"Id": 1}), encoding="utf-8"
    )
    poem = {
        "Id": poem_id,
        "CatId": 1,
        "Title": "test poem with prose commentary",
        "Sections": [{"Index": 0, "SectionType": "WholePoem", "CoupletsCount": 2}],
        "Verses": [
            {"VOrder": 1, "Position": "Right", "Text": "آینه در دست من است", "CoupletIndex": 0},
            {"VOrder": 2, "Position": "Left", "Text": "زنگار بر آن نشسته پنهان", "CoupletIndex": 0},
            {"VOrder": 3, "Position": "Comment", "Text": "شعر"},  # no CoupletIndex at all, like the real corpus
            {"VOrder": 4, "Position": "Right", "Text": "آینه دیگری نیز اینجاست", "CoupletIndex": 1},
            {"VOrder": 5, "Position": "Left", "Text": "زنگار دیگری هم آنجاست", "CoupletIndex": 1},
        ],
    }
    poem_path = poet_dir / f"p{poem_id}.json"
    poem_path.write_text(json.dumps(poem, ensure_ascii=False), encoding="utf-8")
    return poem_path


def test_census_does_not_crash_on_comment_verse_and_sets_couplet_index_none(tmp_path):
    poem_path = _write_poem_with_comment_verse(tmp_path, 90001)
    record = PoemRecord(poem_id=90001, poet_slug="testpoet", poet_id=1, cat_id=1, path=poem_path)
    hits = census([record], MIRROR_ANCHORS)  # must not raise KeyError
    assert len(hits) == 2  # both mirror hits, in couplets 0 and 1
    assert {h.couplet_index for h in hits} == {0, 1}


def test_comment_verse_itself_is_censused_not_silently_dropped(tmp_path):
    """The Comment verse's own text ("شعر") isn't a mirror hit here, but a
    verse WITH a matching anchor in Comment position must still produce an
    AnchorHit with couplet_index=None, not be silently skipped."""
    poet_dir = tmp_path / "poets" / "testpoet" / "cat1"
    poet_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "poets" / "testpoet" / "poet.json").write_text(json.dumps({"Id": 1}), encoding="utf-8")
    poem = {
        "Id": 90002, "CatId": 1, "Title": "comment verse contains the anchor",
        "Verses": [{"VOrder": 1, "Position": "Comment", "Text": "آینه در این تفسیر آمده است"}],
    }
    poem_path = poet_dir / "p90002.json"
    poem_path.write_text(json.dumps(poem, ensure_ascii=False), encoding="utf-8")
    record = PoemRecord(poem_id=90002, poet_slug="testpoet", poet_id=1, cat_id=1, path=poem_path)
    hits = census([record], MIRROR_ANCHORS)
    assert len(hits) == 1
    assert hits[0].couplet_index is None
    assert hits[0].position == "Comment"


def test_couplet_scale_coincidence_excludes_none_couplet_hits(tmp_path):
    """Two hits both with couplet_index=None (in different poems, or even
    the same poem) must NOT be reported as couplet-scale co-incident --
    "no couplet" is not a shared couplet."""
    poet_dir = tmp_path / "poets" / "testpoet" / "cat1"
    poet_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "poets" / "testpoet" / "poet.json").write_text(json.dumps({"Id": 1}), encoding="utf-8")
    poem = {
        "Id": 90003, "CatId": 1, "Title": "both objects in comment verses",
        "Verses": [
            {"VOrder": 1, "Position": "Comment", "Text": "آینه و زنگار در این تفسیر آمده است"},
        ],
    }
    poem_path = poet_dir / "p90003.json"
    poem_path.write_text(json.dumps(poem, ensure_ascii=False), encoding="utf-8")
    record = PoemRecord(poem_id=90003, poet_slug="testpoet", poet_id=1, cat_id=1, path=poem_path)
    mirror_hits = census([record], [LexicalAnchor(object_address="mirror", form="آینه")])
    rust_hits = census([record], [LexicalAnchor(object_address="rust", form="زنگار")])
    assert mirror_hits[0].couplet_index is None and rust_hits[0].couplet_index is None

    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    assert result.poem_scale == frozenset({90003})  # still co-incident at poem scale
    assert result.couplet_scale == frozenset()  # but NOT at couplet scale -- no real shared couplet


def test_build_index_does_not_crash_on_comment_verse(tmp_path):
    poem_path = _write_poem_with_comment_verse(tmp_path, 90004)
    root = poem_path.parent.parent.parent.parent  # tmp_path
    conn, manifest = build_index(root)  # must not raise KeyError
    assert manifest["verses"] == 5  # all 5 verses indexed, including the Comment one
    assert manifest["couplets"] == 2  # only the 2 real couplets, not a phantom "None" couplet
    row = conn.execute(
        "SELECT couplet_index FROM verses WHERE poem_id = 90004 AND vorder = 3"
    ).fetchone()
    assert row[0] is None
