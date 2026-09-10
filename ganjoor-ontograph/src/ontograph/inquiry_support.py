"""Ledger row W04A (Amendment §19.3): deterministic corpus support
verification and lexical-neighbor proposal computation.

Pure engine functions over the built index (no cache, no CLI):
- `compute_support`: is a supplied anchor form present in the pinned
  corpus? Three honest outcomes: supported (positive counts + located
  evidence), unsupported (exact zero), not-applicable (non-Persian form
  — a language fact, not a checked negative).
- `lexical_neighbors`: for a verified seed form, tokens co-occurring in
  the same verses, ordered by raw frequency (DECLARED retrieval order —
  never relation strength). Output kind is only ever `lexical-neighbor`.
- `receipt_valid`: a receipt is valid only against the snapshot id it
  was computed on; any snapshot change stales it.

No LLM, no translation, no semantic inference (Amendment §19.3).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ontograph.normalize import normalize


def _is_persian(form: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in form)


def compute_support(
    conn: sqlite3.Connection,
    corpus_root: Path,
    snapshot_id: str,
    form: str,
    match_mode: str,
) -> dict:
    """Verify a supplied anchor form against the pinned corpus."""
    if not _is_persian(form):
        return {
            "form": form, "match_mode": match_mode,
            "support_status": "not-applicable",
            "hit_count": 0, "poem_count": 0, "poet_count": 0,
            "evidence": [],
            "limitations": ["non-persian form: corpus support is not a meaningful check"],
            "corpus_snapshot_id": snapshot_id,
        }

    norm = normalize(form).normalized
    tokens = norm.split()
    placeholders = ",".join("?" for _ in tokens)
    if match_mode == "phrase" or len(tokens) > 1:
        # phrase: contiguous n-gram within one verse — join token rows per
        # verse and match the ordered sequence
        rows = conn.execute(
            "SELECT t.poem_id, t.vorder, t.token_text, t.start_offset, t.end_offset, "
            "v.text, v.couplet_index, pt.slug "
            "FROM token_offsets t "
            "JOIN verses v ON v.poem_id=t.poem_id AND v.vorder=t.vorder "
            "JOIN poems p ON p.id=t.poem_id "
            "JOIN poets pt ON pt.id=p.poet_id "
            f"WHERE t.token_text IN ({placeholders}) "
            "ORDER BY t.poem_id, t.vorder, t.token_index",
            tokens,
        ).fetchall()
        by_verse: dict[tuple, list] = {}
        for r in rows:
            by_verse.setdefault((r[0], r[1]), []).append(r)
        hits = []
        for (poem_id, vorder), vrows in by_verse.items():
            toks = [(r[2], r[3], r[4]) for r in vrows]
            n = len(tokens)
            for i in range(len(toks) - n + 1):
                if [toks[i + j][0] for j in range(n)] == tokens:
                    hits.append((poem_id, vorder, vrows[0][5], vrows[0][6], vrows[0][7],
                                 toks[i][1], toks[i + n - 1][2]))
        hit_count = len(hits)
    else:
        rows = conn.execute(
            "SELECT t.poem_id, t.vorder, t.start_offset, t.end_offset, v.text, "
            "v.couplet_index, pt.slug "
            "FROM token_offsets t "
            "JOIN verses v ON v.poem_id=t.poem_id AND v.vorder=t.vorder "
            "JOIN poems p ON p.id=t.poem_id "
            "JOIN poets pt ON pt.id=p.poet_id "
            "WHERE t.token_text = ? ORDER BY t.poem_id, t.vorder",
            (norm,),
        ).fetchall()
        hits = [(r[0], r[1], r[4], r[5], r[6], r[2], r[3]) for r in rows]
        hit_count = len(hits)

    poem_ids = sorted({h[0] for h in hits})
    poet_count = len({h[4] for h in hits}) if hits else 0
    evidence = [
        {
            "path": f"poets/{h[4]}/…/poem-{h[0]}.json" if h[4] else f"poem://{h[0]}",
            "poem_id": h[0], "verse_order": h[1], "couplet_index": h[3],
            "match_span": [h[5], h[6]], "corpus_snapshot_id": snapshot_id,
        }
        for h in hits[:5]  # located examples, capped
    ]
    return {
        "form": form,
        "match_mode": match_mode,
        "support_status": "supported" if hit_count > 0 else "unsupported",
        "hit_count": hit_count,
        "poem_count": len(poem_ids),
        "poet_count": poet_count,
        "evidence": evidence,
        "limitations": [],
        "corpus_snapshot_id": snapshot_id,
    }


def lexical_neighbors(
    conn: sqlite3.Connection,
    corpus_root: Path,
    snapshot_id: str,
    seed_form: str,
    top_n: int = 10,
) -> dict:
    """Tokens co-occurring in verses containing the seed form, ordered by
    raw frequency (declared retrieval priority — NOT relation strength)."""
    norm = normalize(seed_form).normalized
    seed_rows = conn.execute(
        "SELECT poem_id, vorder FROM token_offsets WHERE token_text = ?",
        (norm,),
    ).fetchall()
    counts: dict[str, int] = {}
    example: dict[str, tuple] = {}
    for poem_id, vorder in seed_rows:
        text = conn.execute(
            "SELECT v.text FROM verses v WHERE v.poem_id=? AND v.vorder=?",
            (poem_id, vorder),
        ).fetchone()
        toks = conn.execute(
            "SELECT token_text FROM token_offsets WHERE poem_id=? AND vorder=? ORDER BY token_index",
            (poem_id, vorder),
        ).fetchall()
        for (tok,) in toks:
            if tok == norm:
                continue
            counts[tok] = counts.get(tok, 0) + 1
            if tok not in example and text:
                example[tok] = (poem_id, vorder, text[0])
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return {
        "seed_form": seed_form,
        "kind": "lexical-neighbor",
        "ordering": "raw-frequency-descending (declared retrieval order, not relation strength)",
        "corpus_snapshot_id": snapshot_id,
        "neighbors": [
            {
                "token": tok,
                "count": cnt,
                "example_verse": {
                    "poem_id": example[tok][0],
                    "verse_order": example[tok][1],
                    "text": example[tok][2],
                },
            }
            for tok, cnt in ordered
        ],
    }


def receipt_valid(computed_snapshot_id: str, current_snapshot_id: str) -> bool:
    """A support receipt is valid only for the snapshot it was computed
    on; any corpus change stales it (Amendment §19.3)."""
    return computed_snapshot_id == current_snapshot_id
