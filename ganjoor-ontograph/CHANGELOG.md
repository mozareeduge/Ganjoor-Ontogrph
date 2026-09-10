# Changelog

## Unreleased — U07 governed documentation

- README, runbook, and migration guidance now expose the exact quickstart: **study new → inquire → field/refresh → review → walk → assessed-full operation → source return → Finding → release**.
- Documents use the actual CLI (`inquire --refresh`, `inquire --review`, `field build`, `walk`, `source show`, `record add --type finding`, and `release`).
- The agent/researcher boundary, sole versus multiple active ResearchSituation behavior, and non-equivalences between lexical hits, assessments, Findings, and releases are explicit.
- The stale pre-inquiry command flow is retired from the researcher-facing documentation.
## 0.1.1 â€” Trust repair (v0.1.1, execution spec T01â€“T13)

No new interpretive features. This release eliminates false-negative
phrase behavior, false assessment identity, incomplete guided review,
ephemeral operation results, and non-reproducible releases.

- T01: workspace schema_version stamping + backward-compatible readers
  (legacy workspaces read as version 1; detection by missing key, never
  filename).
- T02: structured anchors â€” auto/exact/phrase modes in scan + SQLite
  paths with identical results; ordered token n-gram phrase matching
  that never crosses verses; overlapping matches remain separate hits;
  whitespace-in-exact is a construction error (silent zero forbidden);
  `regex` refused until v0.2 opt-in.
- T03: non-destructive workspace migration â€” preview/apply, atomic
  writes, append-only receipted with before/after content hashes,
  legacy poem-keyed decisions preserved as `legacy-poem-decision`
  (never fanned across hits), explicit valid `--new-id` rename rule,
  object-address ID validation + duplicate refusal.
- T04: content-identity corpus snapshots (`cs1-â€¦`, portable clean-copy
  identity) and stable AnchorHit IDs (`ah1-â€¦`) identical warm/cold and
  across the scan and cached-index paths; matcher/corpus changes
  intentionally change IDs.
- T05: per-hit `HitOccurrenceAssessment` + supersession
  (`active_decision`, `hit_decisions`); superseded rows remain in the
  append-only ledger; the legacy poem-keyed shape is preserved.
- T06: canonical mode names (`anchor|assessed-full|assessed-rule|
  estimated`); `--mode assessed` is an alias with a stderr warning;
  assessed-full below 100% eligible-hit coverage fails BEFORE
  computation with coverage counts and legal alternatives;
  `legacy-poem-decision` rows provide zero coverage.
- T07: walk state machine separated from terminal I/O; Â§6.3 context
  display contract; identity-based scripted responses (order is not
  identity; stale IDs fail atomically); resume selects unassessed hits
  on the same snapshot.
- T08: narrow/split/trace/widen/context-ladder actions as first-class
  append-only events; narrow creates a replacement anchor and retires
  the broad one; split keeps the hit undecided; stop never imputes.
- T09: OperationRecord (Â§6.6) persisted before returning, append-only
  under an exclusive cross-process lock, full provenance + source
  manifest with repository-relative paths.
- T10: self-contained release layout (Â§6.7) â€” records/ JSONL for every
  type with explicit empty files, field/, provenance/, hash manifest
  covering every file except itself, clean refusal on existing target.
- T11: reports rendered solely from staged release content â€” actual
  values, sources, limitations; no workspace fallback; renderer computes
  nothing.
- T12: standalone release verification â€” a copied release verifies
  without workspace access; any tampering/deletion/extra file fails;
  release.json must reference only internal relative paths.
- T13: this release; Gates Aâ€“D discriminating fixtures all in suite.

Suite at release: 211 passed, 10 skipped, 1 xfailed.
