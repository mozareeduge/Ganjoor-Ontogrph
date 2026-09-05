"""Tests for ontograph.corpus.build_index (ledger row P1.6)."""
import json
import pathlib

from ontograph.corpus import build_index, load_corpus_snapshot

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"


def test_index_row_counts_match_manifest():
    snap = load_corpus_snapshot(FIXTURE_ROOT)
    conn, build_manifest = build_index(FIXTURE_ROOT)
    assert build_manifest["poets"] == snap.poets_count == 4
    assert build_manifest["poems"] == snap.poems_count == 27


def test_verse_and_couplet_counts_are_consistent():
    conn, build_manifest = build_index(FIXTURE_ROOT)
    (verse_count,) = conn.execute("SELECT COUNT(*) FROM verses").fetchone()
    (couplet_count,) = conn.execute("SELECT COUNT(*) FROM couplets").fetchone()
    assert verse_count == build_manifest["verses"]
    assert couplet_count == build_manifest["couplets"]
    # every couplet has exactly 2 verses in this fixture (Right + Left)
    assert verse_count == couplet_count * 2


def test_token_offsets_exclude_9107_false_positive_as_a_standalone_mirror_token():
    conn, _ = build_index(FIXTURE_ROOT)
    rows = conn.execute(
        "SELECT token_text FROM token_offsets JOIN verses "
        "ON token_offsets.poem_id = verses.poem_id AND token_offsets.vorder = verses.vorder "
        "WHERE token_offsets.poem_id = 9107"
    ).fetchall()
    tokens = {r[0] for r in rows}
    assert "آینه" not in tokens
    assert any("بند" in t for t in tokens)  # the compound token is present, just not bare


def test_sections_include_poem_level_metadata():
    conn, build_manifest = build_index(FIXTURE_ROOT)
    (section_count,) = conn.execute("SELECT COUNT(*) FROM sections").fetchone()
    assert section_count == build_manifest["sections"] == 27  # 1 section per fixture poem


def test_build_index_survives_a_poem_with_duplicate_section_index_across_types(tmp_path):
    """Real-corpus finding (Phase 8, ledger row P8.1): poem 142187 in the
    live vendored corpus has a `WholePoem` section AND a `Couplet` section
    both at `Index: 2` -- `Section.Index` is not a reliable per-poem key
    (extends P0.5's SectionIndex1 finding). `sections` has no primary key
    for exactly this reason; this reproduces that exact shape without
    needing the real corpus."""
    poet_dir = tmp_path / "poets" / "testpoet" / "cat1"
    poet_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "poets" / "testpoet" / "poet.json").write_text(json.dumps({"Id": 1}), encoding="utf-8")
    poem = {
        "Id": 142187, "CatId": 1, "Title": "duplicate section index across types",
        "Sections": [
            {"Index": 0, "SectionType": "WholePoem", "CoupletsCount": 2},
            {"Index": 1, "SectionType": "WholePoem", "CoupletsCount": 1},
            {"Index": 2, "SectionType": "WholePoem", "CoupletsCount": 1},
            {"Index": 2, "SectionType": "Couplet", "CoupletsCount": 1},  # same idx as above, different type
        ],
        "Verses": [
            {"VOrder": 1, "Position": "Right", "Text": "متن آزمایشی یک", "CoupletIndex": 0},
            {"VOrder": 2, "Position": "Left", "Text": "متن آزمایشی دو", "CoupletIndex": 0},
        ],
    }
    (poet_dir / "p142187.json").write_text(json.dumps(poem, ensure_ascii=False), encoding="utf-8")

    conn, build_manifest = build_index(tmp_path)  # must not raise sqlite3.IntegrityError
    assert build_manifest["sections"] == 4
    (section_count,) = conn.execute("SELECT COUNT(*) FROM sections WHERE poem_id = 142187").fetchone()
    assert section_count == 4  # all 4 kept, none silently dropped to satisfy a false uniqueness assumption
