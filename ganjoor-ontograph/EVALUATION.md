# Evaluation — Ganjoor Ontograph Research Apparatus, Project Spec v2.2.0 → v2.3.0

This is a review of `Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.2.0_FINAL.md`, cross-checked against the live state of both source repositories it depends on:

- `ganjoor/ganjoor-data` (cloned fresh, HEAD `a46eaef480f637ab9d7af1f87f13eb33cffa17e0`)
- `erfanbashar1/persian-poetry-ai-agent-plugin` (cloned fresh, HEAD `500a82a55f90870f2214f39a8069182dbad4f183`)

and against this Claude Code environment, since the spec was written intentionally host-agnostic and the user's request is specifically for a Claude-Code-implementable version.

## Overall assessment

This is an unusually rigorous document. The Seed → Object Address → Lexical Anchor → Anchor Hit → Occurrence Assessment chain, the anchor/object-incidence mode taxonomy (§8.1), the two-direction close/distant pressure loop, the Bridge Record traceability device, and the Appendix A non-equivalence audit are all genuinely good methodological engineering — they anticipate the standard failure modes of computational literary study (conflating lexical retrieval with object presence, conflating co-occurrence with relation, conflating frequency with dispersion, conflating an estimate with a census) and build structural guards against each one before they can happen silently. The data model in Part VIII is implementable as written for the vast majority of records. Nothing in the philosophical framing overreaches into claiming automated interpretation.

The flaws found are not in the method. They cluster in exactly the two places you'd expect a philosophically-driven spec to be weakest: **facts about the two live repos it depends on**, and **the runtime-binding decision it deliberately deferred**. Both are now fixed in v2.3.0.

## Verified factual error (fixed)

**§1.1 cited two different commit SHAs for the same upstream snapshot.** The body text said upstream `ganjoor-data` was at commit `7243e5f0a390cba29b482ebb8c3ce2de42d8190d` (25 Aug 2026, 236 poets, 132,790 poems); the References list said the *same* date and counts came from commit `a46eaef480f637ab9d7af1f87f13eb33cffa17e0`. I cloned the live repo: current HEAD is `a46eaef480f637ab9d7af1f87f13eb33cffa17e0`, manifest generated 2026-08-25T16:22:30Z, 236 poets / 132,790 poems — exactly matching the References entry. The first SHA does not exist on the repository. This is the exact class of error §69.1's "corpus pin gate" and §65's "corpus snapshot and manifest hashes" test exist to catch — the spec's own methodology would have flagged its own mistake had the gate actually been run. Fixed in v2.3.0; see the changelog note inline at §1.1.

The fork's claimed snapshot (234 poets, 132,591 poems, 16 Aug 2026 manifest) checked out exactly: HEAD `500a82a55f90870f2214f39a8069182dbad4f183`, manifest `GeneratedAtUtc` 2026-08-16T12:20:22Z. No error there — but the exact commit SHA wasn't in the spec at all (only the manifest date), which isn't enough to satisfy the spec's own pin-gate; added.

## Real gaps (not errors, but the spec was silent where it needed a rule)

1. **`ganjoor-en` may not exist yet in the pinned fork snapshot.** The fork's own README marks English semantic summaries as "crawling… → v0.2.0"; `.qmd/index.yml` *declares* the `ganjoor-en` collection but declaring it and populating it are different facts. The spec's §21/§25 treat all three collections as symmetrically available. Added a requirement that a workspace call `status` and record live per-collection counts before depending on one — the same "declared ≠ populated" discipline the spec already applies one layer up (anchor ≠ object).

2. **Ambiguous hits' effect on the denominator was undefined.** §8.1 says ambiguous hits are excluded from the numerator of exact object incidence, but never says whether the unit they occur in stays in, or drops out of, the eligible-unit denominator for Prevalence (§27.4). Those are different numbers. Added §8.1.1 with an explicit rule (stays in the denominator, scored 0, reported separately) — this is the kind of silent-collapse gap the spec's whole design philosophy is built to prevent, so it's worth taking as seriously as any of the Appendix A equivalences.

3. **No default estimator for `estimated` mode.** §8.1/§27.2/§70 all *require* an estimated-incidence workflow with "sampling frame, strata, seed, estimator, uncertainty interval" but never specify one — which means the §70 scalability gate has no implementable route in v0.1 as written; every implementer would invent a different estimator and the "at least one end-to-end study must pressure the assessment workflow" test would be unreproducible across implementations. Proposed a concrete provisional default (stratified proportion estimator + Wilson score interval, with finite-population correction above 10% sampling fraction), explicitly filed under Appendix C.3 (replaceable engineering default, not a methodological commitment).

4. **AI-generated English summaries have no fixed identity.** The fork's own docs describe the summarizer as "any OpenAI-compatible API — pluggable." §40 treats "the AI-generated summary" as if it were one stable derivative Profile per poem; it isn't, across fork rebuilds. Added `summarizer_model_version` / `summarizer_prompt_version` to `ProfileRecord`, required whenever `access_apparatus = ai-summary`.

5. **No data-licensing carry-forward requirement.** The fork's `NOTICE.md` is explicit and reasonable: public-domain poems, no-license-declared Ganjoor compilation/Persian AI summaries (used under an attribution convention), MIT English summaries. The spec never mentions this chain, despite repeatedly discussing "scholarly export" and public `ResearchRelease`s. Added a `data_license_notice` field to `ResearchRelease` and a requirement that it be populated verbatim, not re-derived at export time.

6. **Workspace concurrency/version-control model was unspecified.** The spec builds an append-only event log and JSONL records (exactly the shape of a commit log) but never says the workspace itself should be under version control. Added a should-requirement that each study workspace be a git repository with releases as tagged commits — reusing discipline the spec already imposes on the corpus layer, applied reflexively to the research layer, rather than inventing new machinery.

7. **The MCP adapter contract (§63) didn't specify the actual MCP session protocol** the sibling retrieval server already requires (session-id header capture/reuse, `notifications/initialized` handshake) — an adapter built to the letter of v2.2.0 would not interoperate with the real server it's meant to sit beside. Added the concrete requirement, sourced directly from the fork's own skill documentation.

8. **CLI verb collision risk.** The fork ships both a `qmd` CLI (`qmd search`, `qmd query`) *and* a narrower MCP tool surface (`query` only, explicitly "there is NO `search` tool"). Ontograph's own CLI design in §62 doesn't reuse those names, but the spec never states the distinction explicitly, which is exactly the kind of ambiguity an implementer skimming two overlapping projects trips on. Added a one-paragraph disambiguation.

## The deliberate gap: runtime binding

Parts IX–XII were, correctly, written to not privilege one agent host — the engine is CLI/JSON-contract-first, and Appendix C.3 explicitly left "CLI vs. MCP/equivalent adapter" as an open provisional default. That's good spec design in general, but it means the document *as written* cannot be handed to Claude Code and implemented, because "ready for implementation in Claude Code" requires exactly the binding decision the spec deferred.

Added **Part XIII — Claude Code implementation binding** (§75–80): Claude Code is a shell-capable harness, so the CLI path is sufficient and the MCP adapter is unneeded for this target; a concrete `.claude/skills/persian-poetry-ontograph/` skill package mirroring the frontmatter convention the sibling `persian-poetry-mcp` skill already uses; an explicit division of labor between the two skills (discovery → `persian-poetry-mcp`, everything object/field/census/mapping → `persian-poetry-ontograph`); a concrete Bash-invocation and failure-mode pattern; and a permissioning posture (explicit settings.json allowlisting of corpus-mutating verbs, no blanket Bash grant). This resolves Appendix C.3's open question for this one runtime without promoting it to a project-wide invariant — a future non-shell host could still need the adapter.

## What I did not touch

The methodological invariants (Appendix C.1), the fourfold-diagnostic discipline, the Trace→Relation-Object lifecycle, the Use-Status/Claim-Permission separation, the operation packs in Part V, and the worked example were all left as written — I found no factual or implementability defect in them, and second-guessing settled methodological choices wasn't the ask. The changes are additive and corrective, not a rewrite: v2.3.0 is v2.2.0 plus ten targeted fixes and one new part.

## Files produced

- `Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` — the corrected/extended spec (drop-in replacement for v2.2.0).
- `.claude/skills/persian-poetry-ontograph/` — a starting skill scaffold per the new Part XIII (frontmatter + reference/template stubs). This is a scaffold, not the Python engine itself (§59's `src/ontograph/` module, the CLI, and the fixture test suite in Part XI are the actual implementation work and are substantial on their own — building those was outside what was asked here, which was to fix the spec, not build the system against it).
