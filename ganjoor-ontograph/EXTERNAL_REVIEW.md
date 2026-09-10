# External review — Ganjoor Ontograph Research Apparatus (v2.3.0 + implementation package)

Independent cross-layer evaluation by a fresh Claude Opus 4.8 session with no
prior context on this project, commissioned specifically to go past
`EVALUATION.md` rather than re-surface it. It read the spec, `USER_JOURNEY.md`,
the fixture corpus (generator, ground truth, test), the build plan/ledger, and
both skills in full before writing this.

## Verdict up front

This is a genuinely strong, unusually self-disciplined package. The
methodological spine (Seed → Object Address → Lexical Anchor → Anchor Hit →
Occurrence Assessment), the anchor/object incidence modes, the close/distant
pressure loop, the Appendix A non-equivalence audit, and the data-model
schemas are coherent and, as `EVALUATION.md` already established, largely
defect-free at the design level. `USER_JOURNEY.md` is excellent design work —
every step is spec-cited, the result-card shape is concrete, and the two
out-of-scope refusals (§4) are exactly right. The prior evaluation did solid
work; this review is deliberately going past it.

The findings below are not in the method. They're in one place: the gap
between what the apparatus promises and what the test fixture + build loop
can actually prove. The whole project's value proposition is "you will never
mistake a lexical match for an object occurrence, or co-incidence for a
relation." The current test strategy cannot demonstrate that the engine
upholds that promise at the layer where it matters most. That's the
throughline of findings 1–3.

## Finding 1 — The co-incidence/relation tests never exercise the anchor→object gate for the second participant

*(highest leverage; methodological + data + technical)*

**What's wrong.** The spec's core invariant (§27.2, §28.1, and the skill's
own `claim-permission.md` lines 18–21) is that a typed co-incidence matrix
must be built from assessed occurrences of *all* participating Object
Addresses, never raw anchors. But in the fixture, rust (`زنگار`) is never
given an Object Address, a `LexicalAnchor` record, or a single Occurrence
Assessment. Only mirror is assessed (ledger P2.2). The ground-truth
co-incidence numbers in `manifest.json` are computed by the README/test
scripts with literal substring matching (`if RUST in v["Text"]`) — i.e. they
are anchor-level numbers.

So ledger rows P3.3 ("typed co-incidence matrix (AᵀA from occurrence policy,
not raw anchors)"), P3.6 (scale profile), and P3.8 (ablation) all assert the
engine reproduces 3 / 2 / 2→1 — but those targets are identical whether the
engine correctly uses assessed occurrences or cheats with raw lexical
matches, because no rust hit and no mirror hit in the three co-incidence
poems is ever rejected or ambiguous.

**Why it matters (the failure mode).** An implementation that entirely skips
occurrence assessment for the second participant — the exact "co-incidence ≠
relation / Anchor Hit ≠ object occurrence" collapse the project exists to
prevent — passes every co-incidence, scale, and ablation test green. The
epistemic gate (§66) and the scalability gate (§70) would report success on
an engine that silently does the forbidden thing. Note also that the one
ambiguity case (poem 9105) has no rust in it, so ambiguity never propagates
into a relation count — the interaction that's actually dangerous is
untested.

**What to change.** Add a discriminating fixture case where assessed and
anchor co-incidence diverge: e.g. a poem where mirror and rust co-occur
lexically but the mirror hit is assessed `rejected` (figurative), so the
assessed pair-count is strictly lower than the anchor pair-count. Give rust
its own Object Address + assessments in the ledger. Then P3.3's target for
`A_anchor` and for the assessed matrix must differ — and only a correct
engine passes both.

## Finding 2 — The occurrence-assessment scalability gate (§70) is structurally unfalsifiable on the only corpus the loop ever runs

*(methodological + technical)*

**What's wrong.** §70 is explicitly about proving the lexical/object
distinction "remains usable at realistic corpus scale," requiring an object
with "enough Anchor Hits to pressure the assessment workflow." The fixture
has 6 mirror hits. You cannot meaningfully sample 6 hits. The estimator test
(ledger P2.4) is a 100%-sampling-fraction run that "recovers the same point
estimate as assessed-full" — that's a tautology (a census equals itself for
any estimator); it exercises neither the Wilson interval, the stratification,
nor the finite-population correction. `BUILD_PLAN.md` declares v0.1 "done"
when Phase 7 passes on the fixture, and Phase 8 (real corpus) is explicitly
optional/manual/out-of-loop.

**Why it matters.** The single hardest and most novel gate — the one with
"no prior art to copy" (the estimator and ambiguity rules are the v2.3.0
additions) — can be marked green while never being pressured. The autonomous
`/loop` will legitimately reach "v0.1 complete, gates passed" having proven
the easy half of the claim and none of the hard half. That's a false sense
of doneness baked into the definition of done.

**What to change.** Either (a) add a second, deliberately larger fixture
object (a common filler word with ~40–60 hits) so estimated mode can be
tested at a genuine <100% sampling fraction against a known census, and make
P7.5 assert the Wilson interval actually brackets the true value across
seeds; or (b) explicitly downgrade the Phase-7 status string from "gates
passed" to "gates passed except §70-at-scale, pending Phase 8," so the loop
can't self-certify the scalability gate it never ran.

## Finding 3 — The fixture bakes in matcher/schema semantics the spec warns against, and defers all real-world validation to the optional end

*(data + technical)*

Two concrete instances:

**Naive substring matching.** Ground truth is defined by `form in text`.
Persian needs token-/ZWNJ-aware boundaries (the spec says so in §58, and
ledger P1.2 builds exactly that). But P1.5's census is verified to return
exactly 6 against a substring-derived truth. There is no fixture case where
token-aware matching and substring matching diverge (e.g. `آینه` as a
substring of a longer token that should not count). So the anchor matcher's
most important correctness property — not over-matching — is untested, and a
tokenizer-aware engine that correctly rejects a spurious substring would be
scored as failing against a truth computed the wrong way.

**Unverified load-bearing schema.** `generate_fixture.py`'s own docstring
admits `poet.json`/`_cat.json` fields are "NOT independently verified against
the real schema." The entire couplet/hemistich distinction — the pivot of
Tests B/D/E and the whole "does it survive at tight scale" value
proposition — rests on per-verse `CoupletIndex` and `Position: Right/Left`
existing with exactly these semantics in real `ganjoor-data`. This could not
be verified in-session (the fork/upstream repos weren't in this session's
scope and a multi-GB clone was judged disproportionate). If the real schema
groups couplets differently, every Phase 1–3 module is coded and "verified"
against a fiction, and the mismatch surfaces only at the optional, manual,
deferred-to-last Phase 8.

**Why it matters.** The build loop is memoryless and fixture-only by design.
Any matcher-semantics or schema error is invisible until after the engine is
built and self-certified.

**What to change.** Add the divergence case for substring vs. token matching
now; and pull a single-poem real-schema spot check forward to Phase 0/1 (one
file, not a full clone) so the `CoupletIndex`/`Position` contract is
confirmed before the couplet-scale engine is written on top of it.

## Finding 4 — The one-row-at-a-time, memoryless build loop is structurally weak at exactly the cross-cutting invariants the project cares most about

*(process; lighter)*

Finding 1 is a violation that only becomes visible when you hold P2.2 + P3.3
+ §27.2 in view simultaneously. The loop's design ("no memory of any prior
session," "one row, verify, stop") is superb for bounded mechanical work but
has no step that ever looks at the engine as a whole against Appendix A. The
"spec wins, flag don't pick" rule is good, but it fires per-row; nothing
forces a periodic whole-system audit.

**What to change.** Add a recurring ledger row (say, end of each phase) that
re-runs the Appendix A non-equivalence list as live assertions across the
assembled engine — an "invariant audit" that a single row can't satisfy by
construction.

## Finding 5 — The OOO apparatus is largely decorative relative to the engine's real guards

*(strategic observation, not a defect)*

Worth saying plainly because it should shape build effort, not the design:
nearly every safeguard that actually protects a researcher — snapshot
pinning, anchor≠occurrence, frequency vs. dispersion (Gries), co-incidence≠
causation, source-return, denominator display — is rigorous
reproducible-corpus-linguistics discipline that stands entirely without
Harman/Bogost. The spec is admirably honest about this restraint (§2.2; §12
"fourfold only when load-bearing"; §73). The OOO-specific machinery (Fourfold
Diagnostic, Bridge Records) is the part most likely to be built, add
ceremony, and be ignored by working researchers.

**What to change.** Apply the spec's own §12/§73 logic to its implementation:
defer the Fourfold Diagnostic and Bridge Record record-types out of v0.1
until a real Research Situation demands one, rather than building record CRUD
for them (P4.1) on spec. This tightens v0.1 around the parts that carry the
actual epistemic weight.

## What is genuinely solid

- **Methodology & data model** — the five-record chain, the incidence-mode
  taxonomy, §8.1.1's ambiguous-denominator rule, and the Part VIII schemas
  are coherent and implementable as written. No defect found beyond how
  they're tested.
- **Design/UX** — `USER_JOURNEY.md` is the strongest single document in the
  set; the menu-driven progressive disclosure and the out-of-scope refusals
  are exactly what this kind of tool needs. (One minor watch-point: the
  calibration turn genuinely requires the researcher to make an informed
  anchor-vs-object judgment — the one place the "never needs the vocabulary"
  promise is under real tension — but §3.1 handles it well by showing real
  text.)
- **Provenance discipline** — the corpus-pin / license-carry-forward /
  synchronization-verdict machinery, and the AI-summary provenance fields,
  are thorough and correctly reflexive.
- **The framing** — insisting the status is "implementation specification,
  not working apparatus" until the five gates pass is the right posture, and
  it's what makes findings 1–3 fixable rather than fatal: the gates just
  need to actually bite.

## Bottom line

Prioritize in this order: (1) make the co-incidence/relation tests require
assessed occurrences of both participants with a divergent case; (2) give
§70 a fixture object large enough to falsify the estimated-mode claim, or
stop letting the loop self-certify that gate; (3) add the
substring-vs-token divergence case and pull one real-schema spot check
forward. Those three turn the fixture from a consistency check into an
actual proof that the apparatus does the one thing it's built to do.
Findings 4–5 are about spending build effort where the epistemic weight
actually sits.

— Independent Opus 4.8 review
