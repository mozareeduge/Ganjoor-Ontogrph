"""LexicalAnchor / AnchorHit census.

Spec §8 (Seed -> Object Address -> Lexical Anchor -> Anchor Hit ->
Occurrence Assessment chain) and §27.1 (exact anchor-hit census). An Anchor
Hit states only that an anchor matched -- never that the addressed object
occurred (spec §8.1, Appendix A: "Anchor Hit != object occurrence").

Census matches against TOKENS (spec §58's tokenizer, `normalize.tokenize`),
not raw substrings -- this is what makes poem 9107's `آینه‌بند` correctly
NOT count as a hit for anchor `آینه` (external review Finding 3). A naive
`substring in text` implementation would over-count it; this module must
not regress to that.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ontograph.field import PoemRecord
from ontograph.normalize import NORMALIZATION_PROFILE_VERSION, TOKENIZER_VERSION, normalize, tokenize

MATCHER_VERSION = "1.0.0"


@dataclass(frozen=True)
class LexicalAnchor:
    object_address: str
    form: str
    match_mode: str = "exact"  # spec §49: exact|normalized|phrase|regex -- only "exact" implemented in v0.1
    status: str = "approved"


@dataclass(frozen=True)
class AnchorHit:
    object_address: str
    lexical_anchor: str
    poem_id: int
    couplet_index: int | None  # None for a verse with no couplet -- e.g. Position="Comment" prose commentary in the real corpus (see census()'s own note)
    position: str
    original_text: str
    normalized_text: str
    token_start: int
    token_end: int
    matcher_version: str = MATCHER_VERSION
    normalization_profile: str = NORMALIZATION_PROFILE_VERSION
    tokenizer_version: str = TOKENIZER_VERSION


def census(records: list[PoemRecord], anchors: list[LexicalAnchor]) -> list[AnchorHit]:
    """Exact anchor-hit census (spec §27.1) restricted to `approved`
    anchors (spec §49) and matched at the TOKEN level, not the substring
    level. `anchors` may name several `object_address`es at once (e.g. one
    call censuses both "mirror" and "rust" anchors together) -- the
    resulting hit list is unordered across objects; group by
    `hit.object_address` if a caller needs them separated."""
    # Real-corpus finding (ledger row P8.1/Phase 8): ~647 real poems (prose
    # Sufi commentary such as Osmani's Qushayriyya, Araqi's Lama'at) carry
    # verses with `Position: "Comment"` and no `CoupletIndex` at all --
    # spec §24's "structurally exceptional records are not silently forced
    # into couplet logic" applies here: such a verse is still censused (its
    # lexical content is not silently dropped), but `couplet_index` is
    # `None` rather than a fabricated value, and `compare.py`'s couplet-
    # scale logic must exclude `None` from participating in couplet-scale
    # co-incidence (two unrelated Comment verses are not "the same couplet").
    approved = [a for a in anchors if a.status == "approved"]
    forms_by_object: dict[str, set[str]] = {}
    for a in approved:
        # normalize the anchor form itself so a caller-supplied form with,
        # say, an Arabic Yeh variant still matches normalized tokens
        normalized_form = normalize(a.form).normalized
        forms_by_object.setdefault(a.object_address, set()).add(normalized_form)

    hits: list[AnchorHit] = []
    for record in records:
        poem = json.loads(record.path.read_text(encoding="utf-8"))
        for verse in poem["Verses"]:
            text = verse["Text"]
            nt = normalize(text)
            tokens = tokenize(nt.normalized)
            for token_text, start, end in tokens:
                for object_address, forms in forms_by_object.items():
                    if token_text in forms:
                        hits.append(
                            AnchorHit(
                                object_address=object_address,
                                lexical_anchor=token_text,
                                poem_id=record.poem_id,
                                couplet_index=verse.get("CoupletIndex"),
                                position=verse["Position"],
                                original_text=text,
                                normalized_text=nt.normalized,
                                token_start=start,
                                token_end=end,
                            )
                        )
    return hits
