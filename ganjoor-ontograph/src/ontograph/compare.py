"""Typed co-incidence, conditional association, lift, scale profile, field comparison.

Spec Part V operation packs A-D: §28.1 (typed co-incidence matrix A^T A
built from `OccurrencePolicy`, never raw anchors -- with a separate,
explicitly-labelled `A_anchor` matrix for lexical exploration), §28.2
(conditional association P(B|A)/P(A|B), never "causation"), §28.3 (lift
with a minimum-support guard, never "statistical significance" without a
declared reference condition), §29 (Relation Scale Profile / ScaleSurvival
across the scale ladder), §30 (Compare Fields).

Every co-incidence/scale result computed here must report BOTH the
anchor-level and assessed-level numbers when they can differ -- see
EXTERNAL_REVIEW.md Finding 1 and the mini-ganjoor fixture's poem 9106,
which exists specifically so this module's tests can catch a co-incidence
function that silently reads raw anchors instead of `census.py`'s
`OccurrencePolicy` output.

Implemented in ledger rows P3.3 (co-incidence matrix), P3.4 (conditional
association), P3.5 (lift), P3.6 (scale profile), P3.7 (compare fields).
"""
