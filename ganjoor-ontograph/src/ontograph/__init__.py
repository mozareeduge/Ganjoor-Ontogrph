"""Ganjoor Ontograph deterministic engine.

Implements the spec at
../Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md, Part IX
(Technical architecture). Each sibling module corresponds to one line of
that spec's proposed structure (spec §59):

    corpus.py      -- CorpusSnapshot loading, pin verification (spec §56)
    normalize.py   -- Persian normalization pipeline (spec §58)
    field.py       -- FieldCharter / ScopeSpec construction (spec §7, §23, §48)
    anchors.py     -- LexicalAnchor / AnchorHit census (spec §8, §27.1)
    census.py      -- exact anchor-hit census orchestration (spec §27.1)
    encounters.py  -- EncounterRecord construction across scales (spec §24)
    metrics.py      -- incidence, prevalence, spread, concentration, dispersion (spec §27.3-27.7)
    compare.py     -- typed co-incidence, conditional association, lift, scale profile, field comparison (spec §28-30)
    ablation.py    -- Ablation + AblationRetention (spec §31)
    mediation.py   -- Mediational Incidence / relation-mediated thickness (v0.2 scope, spec §72 -- not built in v0.1)
    workspace.py   -- study workspace + git-repo convention (spec §60)
    release.py     -- ResearchRelease generation (spec §55)
    validate.py    -- deterministic + epistemic contract tests, implementation gates (spec §65, §66, §69, §70)

This engine never modifies the pinned corpus (spec §56) and never
collapses an anchor-level result into an assessed-level one (spec §8.1,
Appendix A) -- see EXTERNAL_REVIEW.md for why that distinction is load-bearing
enough to have its own fixture and its own tests.
"""

__version__ = "0.1.0"
