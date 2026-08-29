"""Ablation and AblationRetention.

Spec §31: deliberately remove a component (poet, poem, category, lexical
anchor variant, object address, Relation-Object, derived field rule) and
recompute a declared result; `AblationRetention = M(after) / M(before)`.
Names what was removed and what remained -- never explains *why* without a
Finding (spec §16, Appendix A: "conditional association != causation"
applies here too).

Per EXTERNAL_REVIEW.md Finding 1, ablation retention must be computed and
reported at both the anchor level and the assessed level when they differ
(the mini-ganjoor fixture's `_fixture_ground_truth.ablation_remove_sample1`
block gives both: 33%/25% anchor-level vs. 50%/33% assessed-level).

Implemented in ledger row P3.8.
"""
