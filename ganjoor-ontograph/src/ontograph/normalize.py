"""Persian normalization pipeline.

Spec §58: Yeh/Kaf variants, Unicode normalization form, ZWNJ policy,
optional diacritic removal, whitespace -- versioned, with original text and
offsets preserved so normalization stays reversible at the reading layer.

Deliberately conservative (spec §58): punctuation deletion, stemming,
lemmatization, compound splitting, synonym/semantic expansion are NOT part
of this pipeline. Diacritic removal is available but OFF by default,
treated the same as those excluded operations -- it can alter which
passages an anchor matches, so a study must opt in explicitly rather than
get it for free.

Simplification recorded, not hidden: Unicode NFC composition is applied as
a pre-pass over the raw input, and "original" offsets in `NormalizedText`
are indices into the POST-NFC string, not the original byte-for-byte input.
For Persian text (rarely using decomposed combining sequences beyond
diacritics already present in source), this is lossless for display and
matching purposes; a future revision that needs true pre-NFC offsets
should treat this as a known, named gap, not silently work around it.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

NORMALIZATION_PROFILE_VERSION = "1.0.0"
TOKENIZER_VERSION = "1.0.0"

# Arabic -> Persian letter-variant normalization (spec §58 "Yeh/Kaf variants").
_YEH_VARIANTS = {"ي": "ی", "ى": "ی"}  # Arabic Yeh, Alef Maksura -> Persian Yeh
_KAF_VARIANTS = {"ك": "ک"}  # Arabic Kaf -> Persian Keheh
_LETTER_MAP = {**_YEH_VARIANTS, **_KAF_VARIANTS}

# Arabic diacritics (harakat) + tatweel + superscript alef -- optional strip only.
_DIACRITICS = set(
    "ًٌٍَُِّْٰـ"
)

ZWNJ = "‌"

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedText:
    """`normalized[i]` came from `original[offsets[i]]` for every i, where
    `original` is the post-NFC input (see module docstring). A deletion
    (a stripped diacritic, or one collapsed run of whitespace/duplicate
    ZWNJ) has no entry in `normalized`/`offsets` for the deleted
    characters; a whitespace run collapsed to one space maps that one
    output space to the FIRST original index in the run."""

    original: str
    normalized: str
    offsets: list[int]
    profile_version: str = NORMALIZATION_PROFILE_VERSION
    strip_diacritics: bool = False
    zwnj_policy: str = "keep"

    def to_original_span(self, norm_start: int, norm_end: int) -> tuple[int, int]:
        """Map a [start, end) span in `normalized` back to a span in
        `original`. `norm_end` is exclusive, matching Python slice
        convention; the returned original end is the offset of the last
        included character plus one."""
        if norm_start >= norm_end:
            raise ValueError("empty or inverted span")
        start = self.offsets[norm_start]
        end = self.offsets[norm_end - 1] + 1
        return start, end


def normalize(
    text: str,
    *,
    strip_diacritics: bool = False,
    zwnj_policy: str = "keep",
) -> NormalizedText:
    if zwnj_policy not in ("keep", "strip"):
        raise ValueError(f"unknown zwnj_policy: {zwnj_policy!r}")

    original = unicodedata.normalize("NFC", text)

    out_chars: list[str] = []
    out_offsets: list[int] = []
    i = 0
    n = len(original)
    while i < n:
        ch = original[i]

        if strip_diacritics and ch in _DIACRITICS:
            i += 1
            continue

        if ch == ZWNJ and zwnj_policy == "strip":
            i += 1
            continue

        if ch.isspace():
            run_start = i
            while i < n and original[i].isspace():
                i += 1
            out_chars.append(" ")
            out_offsets.append(run_start)
            continue

        out_chars.append(_LETTER_MAP.get(ch, ch))
        out_offsets.append(i)
        i += 1

    # Trim leading/trailing collapsed-whitespace entries directly on the
    # parallel lists (every whitespace run became exactly one literal " "
    # in out_chars by construction above, so this is an exact, not
    # heuristic, trim -- no need to re-search the joined string).
    start = 0
    end = len(out_chars)
    while start < end and out_chars[start] == " ":
        start += 1
    while end > start and out_chars[end - 1] == " ":
        end -= 1
    out_chars = out_chars[start:end]
    out_offsets = out_offsets[start:end]
    normalized = "".join(out_chars)

    return NormalizedText(
        original=original,
        normalized=normalized,
        offsets=out_offsets,
        strip_diacritics=strip_diacritics,
        zwnj_policy=zwnj_policy,
    )


# Token boundary definition (spec §58 / ledger P1.2): a token is a maximal
# run of "word" characters, where ZWNJ is a WORD-INTERNAL character (not a
# boundary) -- this is what makes "آینه‌بند" one token distinct from
# "آینه", per the mini-ganjoor fixture's poem 9107 (spec §58, external
# review Finding 3). Whitespace and punctuation are boundaries.
_TOKEN_RE = re.compile(rf"[^\s.,;:!?،؛؟«»\"'()\[\]{{}}]+")


def tokenize(normalized_text: str) -> list[tuple[str, int, int]]:
    """Returns (token_text, start, end) triples, start/end as [start, end)
    offsets into `normalized_text`. ZWNJ stays inside its token; it is
    never itself a token boundary regardless of `zwnj_policy` at the
    normalize() stage (a caller using zwnj_policy="strip" already removed
    ZWNJ before this runs, so there is nothing left for this function to
    decide there -- this tokenizer's own ZWNJ-is-word-internal rule only
    matters when zwnj_policy="keep")."""
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(normalized_text)]
