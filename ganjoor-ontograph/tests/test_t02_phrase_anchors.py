"""Ledger row T02: structured anchors; auto/exact/phrase in scan + SQLite.

Discriminating targets (execution spec §13 T02 lock + §14 fixtures 2-4):

1. **Phrase positive**: a contiguous two-token Persian phrase inside one
   verse matches; the same two tokens in REVERSE order in a different
   verse do NOT (ordered n-gram, not a bag of tokens).
2. **Split-across-verses negative**: the two tokens straddling a verse
   boundary never match (phrase matching never crosses verses).
3. **Overlap**: two overlapping phrase matches in one verse both appear
   as separate hits (overlaps remain separate, per §6.2).
4. **auto inference**: one token -> exact; whitespace form -> phrase
   (CLI-facing inference lives in the parser; the anchor layer accepts
   the resolved mode).
5. **scan/index equivalence**: phrase census results are IDENTICAL
   whether served from `anchors.census` (scan) or
   `index_cache.census_from_index` (SQLite) over the same temp corpus.
6. **Forbidden shortcut canary**: whitespace+explicit exact fails before
   write (an exact anchor whose normalized form contains whitespace is a
   construction error -- historically this silently matched nothing).

Fixture discipline: the committed mini-ganjoor fixture's poem set is
frozen by ground truth (27 poems), so these tests build a TEMP corpus
copy with three purpose-built poems added, and never touch fixtures/.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ontograph.anchors import LexicalAnchor, census
from ontograph.field import PoemRecord, scan_corpus
from ontograph.index_cache import census_from_index
from ontograph.normalize import tokenize

# purpose-built verses (normalized Persian, no diacritics):
#   poem A v1: "از چشم او دل گرفتار شد"  -> phrase "دل گرفتار" matches;
#              reversed "گرفتار دل" (v2) must NOT match phrase "دل گرفتار"
#   poem B v1: "...دل" / v2: "گرفتار..." -> split across verses, no match
#   poem C v1: "دل گرفتار گرفتار شد"     -> overlaps: "دل گرفتار" at
#              tokens 1-2 AND "گرفتار گرفتار"? no -- overlapping pair is
#              "دل گرفتار" (t1-t2) and the second instance "گرفتار" does
#              not form another "دل گرفتار". For a true overlap we use
#              phrase "گرفتار گرفتار" in "گرفتار گرفتار گرفتار": tokens
#              1-2 and 2-3 both match -> overlap case.
PHRASE = "دل گرفتار"
REVERSED = "گرفتار دل"


def _poem_json(poem_id: int, title: str, verses: list[str]) -> dict:
    return {
        "Id": poem_id,
        "CatId": 1,
        "Title": title,
        "FullTitle": title,
        "FullUrl": f"/fixture/{poem_id}",
        "RhymeLetters": "",
        "SourceName": "mini-ganjoor-fixture",
        "SourceUrlSlug": "fixture",
        "PoemSummary": "",
        "Metre": {"Id": 1, "Rhythm": "fixture metre"},
        "Sections": [
            {
                "Index": 0,
                "Number": 1,
                "SectionType": "WholePoem",
                "VerseType": "First",
                "RhymeLetters": "",
                "PlainText": " / ".join(verses),
                "HtmlText": "",
                "PoemFormat": "Ghazal",
                "CoupletsCount": (len(verses) + 1) // 2,
            }
        ],
        "Verses": [
            {
                "VOrder": i + 1,
                "Position": "Right" if i % 2 == 0 else "Left",
                "Text": text,
                "CoupletIndex": i // 2,
                "SectionIndex1": 0,
            }
            for i, text in enumerate(verses)
        ],
    }


@pytest.fixture()
def phrase_corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    shutil.copytree(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor", root)
    ghazal = root / "poets" / "sample1" / "ghazal"
    (ghazal / "p9801.json").write_text(
        json.dumps(_poem_json(9801, "عبارت", ["از چشم او دل گرفتار شد", "به یاد او گرفتار دل شدم"]), ensure_ascii=False),
        encoding="utf-8",
    )
    (ghazal / "p9802.json").write_text(
        json.dumps(_poem_json(9802, "شکسته", ["دل", "گرفتار بود"]), ensure_ascii=False),
        encoding="utf-8",
    )
    (ghazal / "p9803.json").write_text(
        json.dumps(_poem_json(9803, "همپوش", ["گرفتار گرفتار گرفتار شد"]), ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def _records(root: Path) -> list[PoemRecord]:
    return [r for r in scan_corpus(root) if r.poem_id >= 9801]


def test_phrase_positive_and_reversed_negative(phrase_corpus: Path) -> None:
    records = _records(phrase_corpus)
    phrase_anchor = LexicalAnchor(object_address="bond", form=PHRASE, match_mode="phrase")
    hits = census(records, [phrase_anchor])
    by_poem = {h.poem_id for h in hits}
    assert 9801 in by_poem, "contiguous phrase in v1 must match"
    # reversed-order verse (v2: گرفتار دل) must NOT match
    assert not any(h.poem_id == 9801 and "گرفتار دل" in h.normalized_text for h in hits)


def test_phrase_never_crosses_verses(phrase_corpus: Path) -> None:
    records = _records(phrase_corpus)
    hits = census(records, [LexicalAnchor(object_address="bond", form=PHRASE, match_mode="phrase")])
    assert 9802 not in {h.poem_id for h in hits}, (
        "tokens split across v1/v2 must never form a phrase match"
    )


def test_overlapping_matches_remain_separate(phrase_corpus: Path) -> None:
    records = _records(phrase_corpus)
    hits = census(
        records,
        [LexicalAnchor(object_address="bond", form="گرفتار گرفتار", match_mode="phrase")],
    )
    poem_hits = [h for h in hits if h.poem_id == 9803]
    assert len(poem_hits) == 2, f"tokens 1-2 and 2-3 must each match, got {len(poem_hits)}"
    starts = sorted(h.token_start for h in poem_hits)
    assert starts[0] < starts[1], "two distinct, overlapping spans"


def test_scan_and_index_phrase_census_identical(phrase_corpus: Path) -> None:
    from ontograph.corpus import build_index
    import sqlite3

    records = _records(phrase_corpus)
    anchors = [
        LexicalAnchor(object_address="bond", form=PHRASE, match_mode="phrase"),
        LexicalAnchor(object_address="bond2", form="گرفتار", match_mode="exact"),
    ]
    scan_hits = census(records, anchors)

    db = phrase_corpus / "idx.sqlite"
    build_index(phrase_corpus, db)
    conn = sqlite3.connect(db)
    try:
        index_hits = census_from_index(conn, records, anchors)
    finally:
        conn.close()
    key = lambda h: (h.object_address, h.poem_id, h.token_start, h.token_end, h.lexical_anchor)
    assert sorted(map(key, scan_hits)) == sorted(map(key, index_hits))


def test_exact_anchor_with_whitespace_is_a_construction_error() -> None:
    from ontograph.anchors import validate_anchor_form

    with pytest.raises(ValueError):
        validate_anchor_form("دل گرفتار", match_mode="exact")


def test_auto_mode_inference() -> None:
    from ontograph.anchors import resolve_auto_mode

    assert resolve_auto_mode("گرفتار") == "exact"
    assert resolve_auto_mode("دل گرفتار") == "phrase"
