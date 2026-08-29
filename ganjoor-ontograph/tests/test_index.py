"""Tests for ontograph.corpus.build_index (ledger row P1.6)."""
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
