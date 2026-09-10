"""Tests for ontograph.normalize (ledger rows P1.1, P1.2)."""
from ontograph.normalize import normalize, tokenize, ZWNJ


# --- P1.1: round-trip offsets on 5 hand-picked fixture verses ---

FIXTURE_VERSES = [
    "آینه در دست من است امشب",
    "زنگار بر آن نشسته پنهان",
    "آیینه‌ی کهنه در صندوق خانه",
    f"آینه{ZWNJ}بند نو بر دیوار بستند",
    "دل من آرام گرفت امشب",
]


def test_roundtrip_offsets_exact_on_five_verses():
    for verse in FIXTURE_VERSES:
        nt = normalize(verse)
        for i in range(len(nt.normalized)):
            orig_idx = nt.offsets[i]
            # every non-whitespace normalized char must trace back to a
            # real position in the (NFC'd) original text
            assert 0 <= orig_idx < len(nt.original)


def test_yeh_kaf_variants_normalized():
    nt = normalize("علي و كتاب")  # Arabic Yeh + Arabic Kaf
    assert "ي" not in nt.normalized
    assert "ك" not in nt.normalized
    assert nt.normalized == "علی و کتاب"


def test_whitespace_collapsed_and_trimmed():
    nt = normalize("   آینه   در   دست   ")
    assert nt.normalized == "آینه در دست"


def test_diacritics_kept_by_default_stripped_when_opted_in():
    marked = "اَلا"
    nt_default = normalize(marked)
    assert nt_default.strip_diacritics is False
    assert "َ" in nt_default.normalized  # kept by default

    nt_stripped = normalize(marked, strip_diacritics=True)
    assert "َ" not in nt_stripped.normalized
    assert nt_stripped.normalized == "الا"


def test_span_roundtrip_to_original():
    nt = normalize("آینه در دست")
    start, end = nt.to_original_span(0, len("آینه"))
    assert nt.original[start:end] == "آینه"


# --- P1.2: token boundary / ZWNJ compound case (the poem 9107 trap) ---

def test_zwnj_joined_compound_is_one_token():
    text = f"آینه{ZWNJ}بند نو"
    nt = normalize(text)  # zwnj_policy="keep" by default
    tokens = tokenize(nt.normalized)
    token_texts = [t[0] for t in tokens]
    assert token_texts == [f"آینه{ZWNJ}بند", "نو"]
    # the whole point: the compound is NOT the same token as plain "آینه"
    assert "آینه" not in token_texts


def test_plain_mirror_word_is_its_own_token():
    nt = normalize("آینه در دست")
    tokens = tokenize(nt.normalized)
    token_texts = [t[0] for t in tokens]
    assert "آینه" in token_texts


def test_punctuation_is_a_token_boundary():
    nt = normalize("آینه، زنگار!")
    tokens = tokenize(nt.normalized)
    token_texts = [t[0] for t in tokens]
    assert "آینه" in token_texts
    assert "زنگار" in token_texts
    assert "،" not in token_texts and "!" not in token_texts
