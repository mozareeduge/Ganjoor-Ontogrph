"""Tests for ontograph.anchors (ledger row P1.5).

The central regression guard here: census() must return exactly 7 mirror
hits (token-aware), NOT 8 (naive substring) -- poem 9107's `آینه‌بند` must
never appear. See EXTERNAL_REVIEW.md Finding 3 and
fixtures/mini-ganjoor/manifest.json's `token_aware_level` block.
"""
import json
import pathlib

from ontograph.anchors import LexicalAnchor, census
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "manifest.json", encoding="utf-8") as f:
    GROUND_TRUTH = json.load(f)["_fixture_ground_truth"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHOR = [LexicalAnchor(object_address="rust", form="زنگار")]


def _records():
    return scan_corpus(FIXTURE_ROOT)


def test_mirror_census_is_exactly_seven_token_aware_hits():
    hits = census(_records(), MIRROR_ANCHORS)
    assert len(hits) == GROUND_TRUTH["token_aware_level"]["mirror_hits_total"] == 7
    poem_ids = sorted({h.poem_id for h in hits})
    assert poem_ids == sorted(GROUND_TRUTH["token_aware_level"]["poems_with_mirror"])


def test_poem_9107_never_produces_a_mirror_hit():
    hits = census(_records(), MIRROR_ANCHORS)
    assert 9107 not in {h.poem_id for h in hits}
    assert GROUND_TRUTH["token_aware_level"]["excluded_false_positive_poem"] == 9107


def test_rust_census_matches_anchor_level_ground_truth():
    hits = census(_records(), RUST_ANCHOR)
    assert len(hits) == GROUND_TRUTH["anchor_level"]["rust_anchor_hits_total"] == 4
    poem_ids = sorted({h.poem_id for h in hits})
    assert poem_ids == sorted(GROUND_TRUTH["anchor_level"]["poems_with_rust"])


def test_unapproved_anchor_produces_no_hits():
    proposed = LexicalAnchor(object_address="mirror", form="آینه", status="proposed")
    hits = census(_records(), [proposed])
    assert hits == []


def test_hit_carries_source_return_fields():
    hits = census(_records(), MIRROR_ANCHORS)
    h = hits[0]
    assert h.original_text  # exact verse text preserved
    assert h.matcher_version and h.normalization_profile and h.tokenizer_version
    assert h.couplet_index is not None and h.position in ("Right", "Left")
