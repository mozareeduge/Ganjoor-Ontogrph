"""ResearchRelease generation.

Spec §55 (ResearchRelease schema) and §56/v2.3.0 (data-licensing
carry-forward: a release must embed the corpus's licensing chain verbatim
-- public-domain poem texts; the Ganjoor compilation and Persian AI
summaries used under Ganjoor's own attribution convention; MIT
fork-generated English summaries where used). A release refuses to
generate with an empty `data_license_notice` (ledger row P4.4's Verify).

Also responsible for the release-as-git-tag convention (spec §60/v2.3.0,
ledger row P4.5), tying `workspace.py`'s git-backed workspace to an actual
tagged commit per release.

Implemented in ledger rows P4.4 and P4.5.
"""
