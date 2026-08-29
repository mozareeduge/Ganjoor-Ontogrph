"""Deterministic + epistemic contract tests, implementation gates.

Spec §65 (deterministic corpus tests), §66 (epistemic contract tests --
scenario tests that the system does NOT collapse anchor into occurrence,
co-incidence into causation, estimate into census, etc.), §69
(implementation gates 1-5), §70 (occurrence-assessment scalability gate).

Also home to the Appendix A "invariant audit" added per
EXTERNAL_REVIEW.md Finding 4 (ledger row P3.9, re-run again at P7.4): a
periodic re-check of the full Appendix A non-equivalence list against the
assembled engine, because a single ledger row's per-row "spec wins, flag
don't pick" discipline never by itself looks at the engine as a whole.

Implemented in ledger rows P3.9, P7.1-P7.6.
"""
