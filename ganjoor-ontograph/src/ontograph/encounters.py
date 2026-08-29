"""Encounter construction across declared scales.

Spec §24 (Encounter scales: verse/hemistich, couplet, section, poem,
category, poet-work, field, token-window) and the `EncounterRecord` schema
(spec §50). Each operation declares unit eligibility explicitly --
prose-like, incomplete, or structurally exceptional records are not
silently forced into couplet logic (spec §24).

This is where the real-corpus finding from ledger row P0.5 becomes load-
bearing: epic-format poems (multiple `SectionType: Couplet` records per
poem, `SectionIndex1` constant across all of them) cannot use
`SectionIndex1` to build section-scale encounters the way a single-section
ghazal can -- section-scale grouping for those poems must correlate via
`CoupletIndex` instead, or such poems must be excluded from section-scale
eligibility with that exclusion shown, not silently miscounted.

Implemented in ledger row P1.6 (alongside the SQLite index) and exercised
further by P3.6 (Relation Scale Profile).
"""
