"""Tests for ontograph.field (ledger row P1.3)."""
import pathlib

from ontograph.field import (
    FieldCharter,
    all_poems,
    difference,
    poet,
    poet_life_proxy_charter,
    scan_corpus,
    union,
)

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"


def _records():
    return scan_corpus(FIXTURE_ROOT)


def test_scan_finds_all_27_poems():
    records = _records()
    assert len(records) == 27
    assert {r.poet_slug for r in records} == {"sample1", "sample2", "sample3", "sample4"}


def test_union_sample1_sample2_is_12_poems():
    records = _records()
    charter = FieldCharter(
        purpose="test",
        corpus_snapshot="mini-ganjoor",
        scope_spec=union(poet("sample1"), poet("sample2")),
    )
    assert charter.poem_count(records) == 12


def test_all_minus_sample3_is_22_poems():
    records = _records()
    charter = FieldCharter(
        purpose="test",
        corpus_snapshot="mini-ganjoor",
        scope_spec=difference(all_poems(), poet("sample3")),
    )
    assert charter.poem_count(records) == 22


def test_derived_field_is_labelled():
    records = _records()
    charter = FieldCharter(
        purpose="test derived",
        corpus_snapshot="mini-ganjoor",
        scope_spec=poet("sample1"),
        derived=True,
        derivation_rule="poets whose documented life overlaps 700-800 AH",
    )
    assert charter.derived is True
    assert "700-800" in charter.derivation_rule


def test_poet_life_proxy_700_800_ah_matches_sample1_and_sample2_only():
    # sample1: 705-780 (overlaps), sample2: 750-820 (overlaps),
    # sample3: 850-910 (no overlap), sample4: 600-655 (no overlap)
    records = _records()
    charter = poet_life_proxy_charter(FIXTURE_ROOT, 700, 800)
    assert charter.derived is True
    assert "700-800" in charter.derivation_rule
    poem_ids = charter.poem_ids(records)
    matched_slugs = {r.poet_slug for r in records if r.poem_id in poem_ids}
    assert matched_slugs == {"sample1", "sample2"}
    assert charter.poem_count(records) == 12  # 7 (sample1) + 5 (sample2)
