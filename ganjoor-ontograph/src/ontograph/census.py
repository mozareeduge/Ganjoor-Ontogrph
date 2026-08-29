"""Occurrence assessment and occurrence-policy orchestration.

Spec §8.1 (object-incidence modes: anchor/assessed-full/assessed-rule/
estimated), §8.1.1 (v2.3.0: ambiguous-hit denominator rule -- a unit with
only ambiguous hits stays in the eligible-unit denominator, scored 0, and
is reported separately rather than silently folded into presence or
absence), §9 (Close Calibration), §27.2 (estimator default: stratified
proportion + Wilson score interval, spec Appendix C.3 as amended in
v2.3.0).

`OccurrencePolicy` records here are what every later co-incidence/scale/
ablation calculation must read from -- never raw Anchor Hits directly
(spec §27.2, §28.1; this is the exact distinction EXTERNAL_REVIEW.md
Finding 1 found untested in the original fixture).

Implemented in ledger rows P2.1 (calibration sampler), P2.2 (assessment
records for both participating objects), P2.3 (denominator rule), P2.4
(estimator).
"""
