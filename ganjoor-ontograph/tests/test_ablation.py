"""Tests for ontograph.ablation (ledger row P3.8).

Ground truth: fixtures/mini-ganjoor/manifest.json's
_fixture_ground_truth.ablation_remove_sample1 block.
"""
import json
import pathlib

import pytest

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor, census
from ontograph.census import accepted_poem_ids
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED
from ontograph.field import scan_corpus

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"

with open(FIXTURE_ROOT / "canonical-study-assessments.json", encoding="utf-8") as f:
    CANON = json.load(f)["assessments"]

MIRROR_ANCHORS = [
    LexicalAnchor(object_address="mirror", form="آینه"),
    LexicalAnchor(object_address="mirror", form="آیینه"),
]
RUST_ANCHORS = [LexicalAnchor(object_address="rust", form="زنگار")]

SAMPLE1_POEM_IDS = {9101, 9102, 9103, 9104, 9105, 9106, 9107}


def _setup():
    records = scan_corpus(FIXTURE_ROOT)
    mirror_hits = census(records, MIRROR_ANCHORS)
    rust_hits = census(records, RUST_ANCHORS)
    mirror_assessments = {int(k): v for k, v in CANON["mirror"].items()}
    rust_assessments = {int(k): v for k, v in CANON["rust"].items()}
    accepted_mirror = accepted_poem_ids(mirror_hits, mirror_assessments)
    accepted_rust = accepted_poem_ids(rust_hits, rust_assessments)
    return mirror_hits, rust_hits, accepted_mirror, accepted_rust


def test_anchor_level_retention_is_1_of_4_poems_1_of_3_couplets():
    mirror_hits, rust_hits, _, _ = _setup()
    result = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, SAMPLE1_POEM_IDS)
    assert result.original_poem_scale == 4
    assert result.remaining_poem_scale == 1
    assert result.poem_scale_retention == pytest.approx(1 / 4)
    assert result.original_couplet_scale == 3
    assert result.remaining_couplet_scale == 1
    assert result.couplet_scale_retention == pytest.approx(1 / 3)


def test_assessed_level_retention_is_1_of_3_poems_1_of_2_couplets():
    mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    result = ablation_retention(
        mirror_hits, rust_hits, MODE_ASSESSED, SAMPLE1_POEM_IDS,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert result.original_poem_scale == 3
    assert result.remaining_poem_scale == 1
    assert result.poem_scale_retention == pytest.approx(1 / 3)
    assert result.original_couplet_scale == 2
    assert result.remaining_couplet_scale == 1
    assert result.couplet_scale_retention == pytest.approx(1 / 2)


def test_anchor_and_assessed_retention_diverge():
    """The direct Finding-1 regression guard for ablation: an engine that
    only ever computes one level would report the same ratio for both
    calls above. They must differ on this fixture."""
    mirror_hits, rust_hits, accepted_mirror, accepted_rust = _setup()
    anchor_result = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, SAMPLE1_POEM_IDS)
    assessed_result = ablation_retention(
        mirror_hits, rust_hits, MODE_ASSESSED, SAMPLE1_POEM_IDS,
        accepted_a=accepted_mirror, accepted_b=accepted_rust,
    )
    assert anchor_result.poem_scale_retention != assessed_result.poem_scale_retention
    assert anchor_result.couplet_scale_retention != assessed_result.couplet_scale_retention
