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

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ontograph.field import PoemRecord
from ontograph.normalize import NORMALIZATION_PROFILE_VERSION, TOKENIZER_VERSION, normalize, tokenize

MATCHER_VERSION = "1.1.0"  # T02: phrase n-gram matching added

VALID_MATCH_MODES = ("exact", "phrase", "regex", "normalized", "auto")


def validate_anchor_form(form: str, match_mode: str) -> str:
    """Validate an anchor form against its declared match mode (T02).

    - form must be non-empty after normalization;
    - `regex` is v0.2 opt-in only (spec §6.2) and is rejected here until
      that row lands -- never silently treated as another mode;
    - an `exact` anchor whose NORMALIZED form contains whitespace is a
      construction error: the pre-T02 engine silently matched nothing in
      that case (token-exact matching can never hit a multi-token form),
      and silent zero for an unsupported matcher is forbidden;
    - returns the normalized form so callers persist it once."""
    if match_mode not in VALID_MATCH_MODES:
        raise ValueError(f"unsupported match_mode: {match_mode!r}")
    if match_mode == "regex":
        raise ValueError("match_mode 'regex' is v0.2 opt-in and not yet supported")
    normalized = normalize(form).normalized
    if not normalized.strip():
        raise ValueError("anchor form is empty after normalization")
    if match_mode == "exact" and " " in normalized:
        raise ValueError(
            f"exact anchor form {form!r} normalizes to multi-token {normalized!r}; "
            "use match_mode='phrase' (a silent no-match is forbidden)"
        )
    return normalized


def resolve_auto_mode(form: str) -> str:
    """`auto` CLI inference (spec §6.2): one normalized token -> exact;
    multiple tokens (whitespace-separated) -> phrase."""
    normalized = normalize(form).normalized
    return "exact" if " " not in normalized else "phrase"


def _phrase_token_spans(
    tokens: list[tuple[str, int, int]], phrase_tokens: list[str]
) -> list[tuple[int, int]]:
    """Ordered token n-gram matcher (T02 lock): all contiguous runs of
    phrase_tokens inside `tokens`, as (start_token_idx, end_token_idx)
    pairs INCLUSIVE. Overlapping runs are all returned (overlaps remain
    separate hits). Matching never crosses verses because callers feed
    one verse's tokens at a time."""
    n = len(phrase_tokens)
    if n == 0:
        return []
    spans = []
    for i in range(len(tokens) - n + 1):
        if [tokens[i + j][0] for j in range(n)] == phrase_tokens:
            spans.append((i, i + n - 1))
    return spans


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
    verse_order: int | None = None  # T04: source VOrder (set by census); None only for legacy callers
    corpus_snapshot_id: str | None = None  # T04: content-identity id of the corpus this hit came from
    matcher_version: str = MATCHER_VERSION
    normalization_profile: str = NORMALIZATION_PROFILE_VERSION
    tokenizer_version: str = TOKENIZER_VERSION

    @property
    def id(self) -> str:
        """Stable hit ID (spec §6.3, T04): `ah1-` + first 24 lowercase hex
        of SHA-256 over corpus_snapshot_id + NUL + object_address_id + NUL
        + lexical_anchor_id + NUL + poem_id + NUL + verse_order + NUL +
        start + NUL + end + NUL + matcher_version (UTF-8, decimal
        serialization). Corpus or matcher changes intentionally change
        IDs. Timestamps and absolute paths never participate."""
        payload = "\x00".join(
            [
                self.corpus_snapshot_id or "none",
                self.object_address,
                self.lexical_anchor,
                str(self.poem_id),
                str(self.verse_order if self.verse_order is not None else -1),
                str(self.token_start),
                str(self.token_end),
                self.matcher_version,
            ]
        ).encode("utf-8")
        return "ah1-" + hashlib.sha256(payload).hexdigest()[:24]


def census(
    records: list[PoemRecord],
    anchors: list[LexicalAnchor],
    corpus_snapshot_id: str | None = None,
) -> list[AnchorHit]:
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
    # T04: hits carry the corpus snapshot identity. When the caller omits
    # it, derive it from the records' shared corpus root (all records in
    # one census call always come from one scan_corpus root). The root
    # derivation walks up from the poem path to the dir containing
    # manifest.json; ad-hoc poem files outside a corpus layout get "none".
    if corpus_snapshot_id is None and records:
        poem_path = Path(records[0].path)
        corpus_root = poem_path.parent
        for _ in range(5):
            if (corpus_root / "manifest.json").exists():
                break
            if corpus_root.parent == corpus_root:
                corpus_root = None
                break
            corpus_root = corpus_root.parent
        else:
            corpus_root = None
        if corpus_root is not None:
            from ontograph.corpus import corpus_snapshot as _cs

            corpus_snapshot_id = _cs(corpus_root).snapshot_id
    approved = [a for a in anchors if a.status == "approved"]
    # T02: per-anchor normalized forms keyed by mode. exact anchors keep
    # their single-token set; phrase anchors carry their ordered token
    # list. Everything is validated up front -- an invalid form/mode
    # fails BEFORE any corpus reading (spec §7: unsupported input fails
    # before computation).
    exact_by_object: dict[str, set[str]] = {}
    phrase_by_object: dict[str, list[list[str]]] = {}
    for a in approved:
        mode = a.match_mode
        if mode == "auto":
            mode = resolve_auto_mode(a.form)
        normalized_form = validate_anchor_form(a.form, mode)
        if mode == "phrase":
            phrase_by_object.setdefault(a.object_address, []).append(normalized_form.split())
        else:  # exact (or the legacy `normalized` alias, emitted canonically as exact)
            exact_by_object.setdefault(a.object_address, set()).add(normalized_form)

    hits: list[AnchorHit] = []
    for record in records:
        poem = json.loads(record.path.read_text(encoding="utf-8"))
        for verse in poem["Verses"]:
            text = verse["Text"]
            nt = normalize(text)
            tokens = tokenize(nt.normalized)
            for token_text, start, end in tokens:
                for object_address, forms in exact_by_object.items():
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
                                verse_order=verse["VOrder"],
                                corpus_snapshot_id=corpus_snapshot_id,
                            )
                        )
            # T02 phrase pass: ordered n-grams within THIS verse only
            for object_address, phrase_lists in phrase_by_object.items():
                for phrase_tokens in phrase_lists:
                    for i, j in _phrase_token_spans(tokens, phrase_tokens):
                        hits.append(
                            AnchorHit(
                                object_address=object_address,
                                lexical_anchor=" ".join(phrase_tokens),
                                poem_id=record.poem_id,
                                couplet_index=verse.get("CoupletIndex"),
                                position=verse["Position"],
                                original_text=text,
                                normalized_text=nt.normalized,
                                token_start=tokens[i][1],
                                token_end=tokens[j][2],
                                verse_order=verse["VOrder"],
                                corpus_snapshot_id=corpus_snapshot_id,
                            )
                        )
    return hits
