"""Persian normalization pipeline.

Spec §58: Yeh/Kaf variants, Unicode normalization form, ZWNJ policy,
optional diacritic removal, whitespace -- versioned, with original text and
offsets preserved so normalization stays reversible at the reading layer
(spec §58, last paragraph).

Implemented in ledger row P1.1 (pipeline) and P1.2 (token boundaries).
"""
