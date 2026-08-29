# Research Release template (spec §55, §Appendix B, `ResearchRelease`)

A release is not "what mirror is." It is what this inquiry established,
through which operations, and where another encounter can still change the
result. Before generating, confirm every item in Appendix B's minimum
complete study package is present, and that:

- **`data_license_notice`** is populated verbatim from the corpus/fork
  licensing chain (spec §56) — public-domain poem texts; no-license-declared
  Ganjoor compilation and Persian AI summaries used under Ganjoor's own
  attribution convention; MIT fork-generated English summaries where used.
- **corpus_snapshot** names the exact commit/manifest hash, not "latest."
- **reopening_conditions** are stated, not left implicit.
- **residue** (rejected routes) is included, not silently dropped.

Do not export a release with a `known-stale` or `unknown` corpus/retrieval
synchronization verdict (spec §25) without surfacing that mismatch
prominently in the release itself.
