"""LexicalAnchor / AnchorHit census.

Spec §8 (Seed -> Object Address -> Lexical Anchor -> Anchor Hit ->
Occurrence Assessment chain) and §27.1 (exact anchor-hit census). An Anchor
Hit states only that an anchor matched -- never that the addressed object
occurred (spec §8.1, Appendix A: "Anchor Hit != object occurrence").

Census results must distinguish anchor-level (naive) from token-aware-level
(spec §58 tokenizer applied) counts -- see EXTERNAL_REVIEW.md Finding 3 and
the mini-ganjoor fixture's poem 9107 for why this distinction has its own
regression test.

Implemented in ledger row P1.5.
"""
