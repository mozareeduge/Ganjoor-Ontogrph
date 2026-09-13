---
title: "Amendment 20 — Flat Assessment"
subtitle: "Removing default assessor precedence from Occurrence Assessment, census coverage, and Claim Permission"
amendment: 20
version: "1.1.0"
status: "normative amendment — decisions made, implementation pending"
date: 2026-09-13
author: "Mohammad Zare (research decision); drafted to specification"
changelog: "1.1.0: closed two gaps found in review — §4.3 gained `contestation_threshold` (the field §4.7's ceiling table referenced but never defined) and `min_weight_for_inclusion`; §4.9 added, giving the previously-vestigial per-position `weight` field its only two legal consumers (triage queue ordering, policy inclusion floor) with an explicit non-consumer list (never resolution, never a tiebreaker, never a substitute for independence_class). Ledger: F05/F10 updated, F13 added for triage ordering."
amends: "Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md (§5, §8.1, §8.1.1, §9, §16, §27.2, §49, §70, Appendix A, Appendix C.1) and implementation/V0_2_HERMES_EXECUTION_SPEC.md (§6.4, §6.5, §9, §10, §14, §15)"
---

# Amendment 20 — Flat Assessment

## 0. Why this file, here, with this name

**Decision.** This is a separate, numbered Amendment document sitting beside the
project spec, not an edit to `Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md`
and not a new `v3.0.0` spec file.

**Why.**

1. It changes an Appendix C.1 methodological invariant, so it cannot be a
   §19.x execution-spec amendment (those are engineering-level and the code
   already cites them as `Amendment §19.2`, `§19.4`, `§19.5`, `§19.6`, `§19.9`).
   `§20.x` is the next free number in that same citation namespace, so code
   comments and refusal messages can cite `Amendment §20.3` unambiguously and
   consistently with what `cli.py` already does.
2. The project's own discipline is append-only and never-overwrite —
   `IMPLEMENTATION_LEDGER.md`'s header rule ("never edit a `done` row... don't
   rewrite history silently"), the spec's own additive Part XIII, and
   `V0_2_HERMES_EXECUTION_SPEC.md` carrying its own ledger. Rewriting 2,000
   lines of a spec that 336 tests and ~7,500 lines of source cite by
   §-number is exactly the silent-drift risk that discipline exists to stop.
3. `V0_2_HERMES_EXECUTION_SPEC.md` set the precedent that a normative document
   may carry its own implementation ledger. This one does (§10).

**On acceptance**, the project spec's version becomes **2.4.0** and this
amendment is folded in as **Part XIV** plus a revised **Appendix C.1** and
**Appendix A** at the next spec consolidation. Until then this file is
normative over the sections it names; where it and v2.3.0 disagree, this file
wins, and v2.3.0's text is not edited.

**Rejected alternative:** a new `v3.0.0` spec file — rejected because it
orphans every existing §-citation in the source tree for no methodological
gain.

---

## 1. The research decision this amendment implements

The researcher's statement, verbatim:

> "i disagree myself with human first and accepted/rejected/ambiguous — humans
> are also objects horizontally working in this complex object, important to
> record their stuff, but not the ultimate decider that after that traces of
> other objects where involved, or anything becomes removed. So, i need aligned
> with OOO, a redesign of the research machine... humans can assess if they
> want. but we will not have human only assessment principle by default."

Read precisely, this is **not** "let AI decide instead of humans." It is a flat
ontology objection to *any single object type holding default, trace-erasing
final authority*. It has three parts, and this amendment answers each:

| The objection | The mechanism that answers it |
|---|---|
| No type is the ultimate decider **by default** | §3.4: no built-in precedence; composition is an explicitly declared, versioned **Resolution Policy**; no policy declared ⇒ no aggregate computed (§4.3) |
| One object's contribution must not **erase** another's | §3.3: `supersedes` is scoped to the *same* assessor object; cross-assessor overwrite is structurally impossible |
| Humans **may** assess when they want | §4.4: `named-assessor(<researcher>)` is a first-class, permanently supported policy that reproduces the old numbers exactly, correctly labelled as one declared operationalization among others |

Nothing is taken away from the researcher. What is removed is the *default*.

---

## 2. Conceptual ground

### 2.1 What was actually load-bearing, and what was not

v2.3.0 never says an Occurrence Assessment must be human-authored. §8.1 defines
`assessed-full` as "**all hits have an Occurrence Assessment**" — a *coverage*
predicate. §49's `OccurrenceAssessment` schema has carried
`assessor: human|agent|rule` since v2.2.0. Appendix C.1's invariants require
that the chain stay *distinct* and that "AI proposal remains distinguishable
from evidence."

So "100% human coverage" was never a spec commitment. It entered through the
implementation: `walk.py:245` and `walk_state.py:262` hardcode
`assessor_type="human"`, and `census.py:242-247` counts every non-legacy row
identically, so the axis was never visible and therefore never chosen.

But **distinguishability alone is not enough**, and this is where this
amendment goes beyond earlier analysis. A model in which agent and rule
contributions are *labelled* but a human contribution *supersedes* them is
still hierarchical — it just has an honest label on the hierarchy. The
researcher is rejecting "distinguishable but human-final," not merely
"indistinguishable."

The invariant that replaces it has two clauses:

> **Non-precedence.** No assessor type holds default priority over another.
> How contributions compose is a declared, versioned, inspectable operation,
> never a built-in ordering.
>
> **Non-erasure.** A contribution is never overwritten or deleted by another
> object's contribution. Revision is self-scoped: an object may revise its own
> position; it may never supersede another's.

### 2.2 Reconciliation with Bogost's ontography (spec §3)

§3 is titled "Ontographic arrangement before explanatory hierarchy," and says
units' "later importance is established by evidence and research consequences,
not by the fact that they entered the inventory."

The old `assessed-full` gate inverted its own title twice over. It required
that (a) every unit be sorted before the arrangement could be spoken about at
all, and (b) the sorting be done by one privileged type. Flat assessment fixes
both: the **Position Set** on a hit *is* an ontographic arrangement — a flat
list of heterogeneous, differently-conditioned encounters with that hit — and
it is publishable *as an arrangement* (§4.2, `inventory` mode) before anything
resolves it.

Flatness is not relativism. §22's role discipline already says the role follows
the question, not the entity type. The **Resolution Policy** is exactly where a
study declares consequence — per study, per object, disclosed on every result
card, and ablatable (§2.3). That is §22 applied to assessors instead of to
corpus entities.

### 2.3 Reconciliation with Moretti's operationalization (spec §26)

§26 cites Moretti (2013): a concept becomes researchable through explicit
operations "whose consequences can be inspected and revised."

**A Resolution Policy is an operationalization in exactly Moretti's sense**, and
a very literal one: "this hit counts as an occurrence" becomes a declared
operation over a Position Set. Moretti's requirement is therefore directly
implementable and this amendment makes it mandatory:

> **Policy ablation (§20.7).** Every aggregate object-incidence result must
> also report the same figure under at least one alternative declared policy —
> at minimum under `concordance` and under each single-assessor projection. If
> the figure is stable across policies, that stability is evidence. If it
> swings, **the swing is the finding**, not a problem to be tuned away.

This generalizes the AI-triage-ablation idea into something type-neutral: it
ablates *any* assessor, the researcher's own positions included. That is both
more flat and more useful — "what does this result look like without me?" is a
better question than "what does it look like without the machine?"

### 2.4 Disagreement is preserved as Trace, never resolved by rank

§13 already names "contradiction between Profiles" as a Trace source; §26
already says "disagreement between operations can become a Trace instead of
being averaged into a synthetic truth." The mechanism exists and was unused for
this purpose.

**Decision.** A hit whose Position Set contains differing stances from two or
more assessor objects has Standing `contested`, and the engine **automatically
mints a Trace candidate** for it, carrying the hit, every position with its
apparatus and conditions, and the source return. Contestation is not an error
state and not a tie to be broken. It is the cheapest research material the
apparatus can produce, and §20.6's permission table makes it expensive to
ignore.

The aggregate contestation *distribution* is itself a finding: a machine and a
researcher who disagree uniformly are producing noise; disagreement
concentrated in one poet, one anchor form, or one register has located a
boundary of the Object Address — which is §38's object-boundary work arriving
automatically instead of one passage at a time.

### 2.5 The assessor is an object in the field

**Decision.** Assessor identities are registered as first-class records
(`AssessorObject`, §3.2) with their own IDs, apparatus description, and
conditions of validity — not as an enum value on an assessment row.

This is the structural form of the researcher's own sentence ("humans are also
objects horizontally working in this complex object"). It has three concrete
consequences: assessors can be ablated like poets can (§31); an assessor can
carry a Profile (§10) describing how it accesses hits; and a second human
researcher is a second assessor object, not a conflict.

---

## 3. The data model

### 3.1 `OccurrencePosition` replaces `OccurrenceAssessment`

**Decision.** The record is renamed and re-semanticised. An Occurrence
Assessment was a *verdict*. An **Occurrence Position** is a *positioned,
attributed record of how one assessing object stands toward the question
"may this Anchor Hit count as an occurrence of this Object Address?"*

Positions do not overwrite each other. A hit accumulates a **Position Set**.

```yaml
# OccurrencePosition  (workspace: corpus/occurrence-positions.jsonl, append-only)
id:                      # "op1-" + uuid4 hex
anchor_hit_id:           # stable ah1- id (spec §6.3) — snapshot-scoped
object_address_id:
assessor_object_id:      # REQUIRED. FK into objects/assessor-objects.jsonl. No default.
stance:                  # occurs | does-not-occur | undecidable | out-of-scope
weight:                  # optional float in [0,1]; null by default. The assessor's OWN
                         #   self-reported confidence in THIS position (e.g. an LLM
                         #   triage's certainty, a rule's match-strength). NEVER read as
                         #   a probability of truth, NEVER used by resolve() to break a
                         #   tie between assessors, and NEVER a substitute for
                         #   `independence_class`. Its only two legal consumers are (a)
                         #   ordering an unpositioned queue for walk/triage attention
                         #   (§4.9), and (b) a policy's OPTIONAL
                         #   `min_weight_for_inclusion` gate (§4.3) — never resolution
                         #   itself. A `weighted` ResolutionPolicy's weights (§4.3) are a
                         #   separate, per-ASSESSOR value declared once in the policy;
                         #   this field is per-POSITION and self-reported. Do not conflate
                         #   the two.
rationale:               # free text
apparatus:               # what produced this position (see §3.2 apparatus grammar)
conditions:              # {corpus_snapshot_id, scope_hash, anchor_forms, tokenizer_version, policy_version}
created_at:              # UTC ISO-8601
supersedes:              # null, or a prior position id BY THE SAME assessor_object_id
```

**Stance vocabulary — decision and rationale.** `accepted | rejected |
ambiguous` is the grammar of adjudication: someone *accepts* someone else's
submission. It encodes the hierarchy in the word. The replacement is the
grammar of a position about the object:

| Old | New | What changed |
|---|---|---|
| `accepted` | `occurs` | no longer "I accept it," now "on my access, it occurs" |
| `rejected` | `does-not-occur` | ditto |
| `ambiguous` | `undecidable` | the assessor looked and the object exceeded the access — an OOO-positive result, not a failure |
| — | `out-of-scope` | **new.** The hit is a genuine occurrence but of a *different* object, or outside the declared field. This case was silently polluting `rejected` and destroying the ability to split an Object Address (§38) from the assessment ledger. |

**Deferral is not a stance.** Earlier analysis proposed splitting `ambiguous`
into `ambiguous-on-inspection` and `deferred`; this amendment **supersedes that
recommendation** with a cleaner answer: not having positioned a hit is simply
the *absence* of a position, and absence is already first-class (Standing
`unpositioned`, §3.5). No enum value is needed, and `undecidable` is protected
from absorbing "I ran out of time," which was the original worry.

### 3.2 `AssessorObject`

```yaml
# objects/assessor-objects.jsonl (append-only)
id:                      # e.g. "as-mz", "as-triage-claude-opus5-v3", "as-rule-figurative-v1"
label:
assessor_type:           # OPEN vocabulary, NOT a ranked enum:
                         #   human | agent | rule | retrieval-score | corpus-metadata |
                         #   prior-study | editorial-apparatus | <study-declared>
apparatus:               # required. human: who + what context ladder levels are opened.
                         #   agent: model id + prompt version + harness.
                         #   rule: rule id + version + implementation reference.
independence_class:      # declared. Two assessors sharing a class do NOT count as
                         #   independent corroboration in §4.2's concordant tier.
                         #   (A rule authored by an agent shares that agent's class.)
conditions_of_validity:  # corpus/scope/anchor/tokenizer compatibility, free text + machine fields
registered_by:
registered_at:
```

`assessor_type` is a **descriptive** field with no ordering. Nothing in the
engine may branch on it to grant precedence. The one and only exception is the
migration marker `legacy-poem-decision`, which continues to provide zero
coverage exactly as today (execution spec §15.5) because those rows are
poem-keyed and cannot be attached to a hit at all — a *structural* exclusion,
not a hierarchical one.

`independence_class` is the guard against the obvious cheat ("add a second
assessor to buy a higher permission tier"): two assessors in the same class do
not corroborate each other.

### 3.3 Non-erasure, enforced structurally

**Decision.** `supersedes` is valid **only** when the superseded position
carries the same `assessor_object_id`. A cross-assessor supersession is a hard
refusal at write time, not a validation warning.

This single rule is the load-bearing line of the entire amendment. It is what
makes "a human's decision does not delete the trace of other objects" a
property of the data model rather than a policy someone must remember.

Corollary: the active-position computation in `census.active_decision()` becomes
**per (object_address_id, anchor_hit_id, assessor_object_id)** — one active
position per assessor per hit, and a Position Set is the set of those actives.

### 3.4 No default precedence

**Decision.** The engine contains no built-in ordering over assessor types. It
is a defect, reportable as a regression, for any function in `src/ontograph/`
to compare two positions by `assessor_type` for the purpose of choosing one.

**Rejected alternative:** a built-in fallback order (human > rule > agent) used
only when no policy is declared. Rejected because a silent default is precisely
the mechanism by which "human-only" became invisible in the first place.

### 3.5 `Standing` — derived, never stored as truth

Per (hit, object), computed from the Position Set:

| Standing | Condition |
|---|---|
| `unpositioned` | no positions |
| `single-position` | exactly one assessor object has positioned it |
| `concordant` | ≥2 assessor objects of ≥2 independence classes, all same stance |
| `corroborated-weak` | ≥2 assessor objects, same stance, but sharing an independence class |
| `contested` | ≥2 assessor objects, stances differ → **mints a Trace candidate (§2.4)** |

Standing is recomputed on read. It is never persisted as a fact about the hit;
it is persisted only inside an `OperationRecord` as part of that operation's
result, where it is correctly scoped to that operation's conditions.

---

## 4. The census and coverage model

### 4.1 Two independent axes, always reported together

Every object-incidence result carries both, always, with no option to suppress:

```json
"positioning": {
  "eligible_hits": 218,
  "positioned_hits": 218,
  "unpositioned_hits": 0,
  "by_assessor": {"as-mz": 41, "as-triage-opus5-v3": 218, "as-rule-fig-v1": 218}
},
"standing": {
  "unpositioned": 0, "single_position": 0,
  "concordant": 173, "corroborated_weak": 22, "contested": 23
}
```

### 4.2 Modes

| Mode | Requires | Reports |
|---|---|---|
| `anchor` | approved anchors | lexical incidence only (unchanged) |
| `inventory` | nothing | **NEW.** Per-hit standing + per-assessor stances + source return. Never a single prevalence number. Always available. |
| `positioned-full` | every eligible hit ≥1 position **and** a declared Resolution Policy | exact incidence under that policy |
| `positioned-concordant` | every eligible hit `concordant` (≥2 independence classes, 0 contested, 0 single-position) | exact incidence; no policy needed, because there is nothing to resolve |
| `estimated` | §4.6's five conditions | interval + in-sample standing distribution |

`assessed-rule` disappears as a mode. A rule is now an assessor object, so the
old `assessed-rule` is exactly `positioned-full` + `named-assessor(as-rule-*)`
+ a validation receipt (§4.5). One fewer concept, same guarantees.

**The methodological payoff, stated plainly.** `positioned-concordant` is a
*harder* tier than the old `assessed-full`, not an easier one — it requires
independent corroboration, which one researcher alone can never supply at 218
hits. Flat assessment does not lower the bar. It changes the currency: the top
tier becomes reachable by *combining differently-conditioned accesses*, which
is buyable with machine labor, instead of by *exhausting one privileged
access*, which is not.

**`inventory` mode is the tier that makes real work sayable.** After a week on
a 218-hit object a researcher has a partial, heterogeneous, honestly-labelled
arrangement. Before this amendment there was no legitimate way to say what they
had. Now there is, and it is the most ontographic result the apparatus
produces.

### 4.3 `ResolutionPolicy`

```yaml
# research/resolution-policies.jsonl (append-only, versioned)
id:
object_address_id:       # or "*" for a study default
kind:                    # none | concordance | named-assessor | weighted
assessor_object_id:      # required when kind = named-assessor
weights:                 # required when kind = weighted; {assessor_object_id: float}
contested_handling:      # excluded-and-reported | counted-as-undecidable
contestation_threshold:  # float in [0,1] or null. Share of eligible hits that may be
                         #   `contested` before §4.7's ceiling drops to "describe
                         #   locally" regardless of coverage. null = 0.0 (zero
                         #   tolerance: ANY contested hit caps the ceiling until it is
                         #   opened as a Trace and worked through). This is the field
                         #   §4.7's "study-declared threshold" names; it did not exist
                         #   in v1.0.0 of this amendment and is added here to close
                         #   that gap. Declaring a nonzero threshold is itself a
                         #   disclosed methodological choice and appears on every
                         #   result card next to the contestation rate it is being
                         #   measured against.
min_weight_for_inclusion:  # optional float in [0,1] or null. When set, a position with
                         #   a self-reported `weight` (§3.1) below this value is
                         #   excluded from resolution and counted as `unpositioned` for
                         #   that policy's purposes — it never counts toward this
                         #   policy's coverage or standing. Applies only to positions
                         #   from assessor_type != human (a human position with
                         #   reported weight is never excluded this way). null = no
                         #   floor; every position participates regardless of weight.
justification:           # REQUIRED for kind = weighted; free text
declared_by:
declared_at:
version:
```

| kind | Semantics |
|---|---|
| `none` | positions are not composed. Only `anchor` and `inventory` results are computable. |
| `concordance` | a hit counts as occurring only where every positioning assessor says `occurs`; contested hits are excluded from the numerator **and reported separately**, exactly as §8.1.1 already handles ambiguity |
| `named-assessor(<id>)` | compute using one assessor's positions only |
| `weighted(<weights>)` | declared numeric composition; requires `justification`; capped one permission level below the same result under `concordance` (§4.7), because it averages positions and §26 warns against averaging disagreement into synthetic truth |

**Decision — what happens when nothing is declared.** The engine **refuses** to
compute any aggregate object-incidence figure and serves `inventory` mode
instead, with a refusal message naming the policies it could declare and their
consequences. The default is not "human wins." The default is *"you have not
yet said how positions compose, so I will not compose them."*

### 4.4 How a researcher assesses alone, if they want to

Declare `named-assessor(as-<researcher>)`. Position every hit. The result is
numerically **identical** to the pre-amendment `assessed-full`, and it is
labelled on every card as one declared operationalization among others, with
its policy ablation showing what the figure would be under any other declared
policy.

Nothing is lost. The researcher's judgement is fully available, fully
supported, and no longer invisible.

### 4.5 The validated-rule receipt survives, with one change

Execution spec §9's assessed-rule package (id/version, compatibility,
calibration scope, decision space, validation hit IDs, agreement metrics,
thresholds, limits, actor, timestamp) carries over unchanged, with one
substitution: the receipt is no longer "validated *against human review*." It
is **validated against a named reference assessor set**, whoever that is, and
the receipt records which. Agreement with a researcher is one meaningful
reference; agreement with a second independent rule is another. The receipt
still invalidates on corpus/anchor/tokenizer/rule/scope change.

The fixture's `figurative-context-stoplist-v1` remains fixture-only and is
never a real-corpus default (execution spec §9).

### 4.6 `estimated` — the five honesty conditions, carried over intact

1. The frame is the eligible hit set under the field scope, enumerated and
   hashed before drawing.
2. The engine draws and **locks** the sample from a recorded seed before any
   hit is read. A researcher who can choose which sampled hits to position
   destroys the estimator through selective non-response.
3. Non-response is reported as non-response, never dropped. A sampled but
   unpositioned hit appears in the report and widens or blocks the interval.
4. `undecidable` has a pre-registered treatment; the default is an interval
   bracketing both extremes (all-undecidable-as-occurs and
   all-undecidable-as-does-not-occur), so the cost of undecidability is visible
   rather than conventionally hidden.
5. No derived operation may consume an estimate (§27.2 already blocks pairwise
   matrices; extend to ablation and scale-survival).

Plus one addition specific to flat assessment: **the in-sample standing
distribution is reported alongside the interval.** An estimate built on
contested positions is a different object from one built on concordant
positions, and the reader must see which.

Stratification guidance (unchanged, and load-bearing for real studies):
stratify by poet **and** anchor form, and report per stratum. A corpus-wide
interval over 65 poets answers no question a researcher actually has.

### 4.7 Claim Permission, rebuilt for a flat model

The ceiling is a function of **disclosed composition and contestation**, never
of assessor type. Computed by the engine from the `OperationRecord` and
enforced at `record add` (§9.5).

| Condition | Ceiling |
|---|---|
| `anchor` | preserve only |
| `inventory` | describe locally |
| positioning coverage < 100% (any mode but `estimated`) | describe locally |
| `estimated`, all five §4.6 conditions met | describe distribution under declared conditions |
| `positioned-full`, **one** assessor object — of *any* type | describe distribution under declared conditions |
| `positioned-full`, ≥2 assessor objects in ≥2 independence classes, contestation ≤ study-declared threshold | argue cautiously |
| `positioned-concordant` | argue |
| any result under `weighted` resolution | one level below the same result under `concordance` |
| contested share > policy's `contestation_threshold` (§4.3; null = 0.0) | capped at **describe locally**, regardless of coverage, until the contested set is addressed as Traces |

Three properties worth stating explicitly:

1. **A lone researcher gets exactly the same ceiling as a lone rule or a lone
   agent.** That is the flat commitment made enforceable rather than declared.
2. **What buys argumentative permission is independent corroboration plus low
   contestation — not authorship.** This is the OOO-correct answer: a claim is
   warranted because multiple differently-conditioned accesses converged on it,
   not because a privileged type spoke. It is also, incidentally, ordinary
   scientific epistemology.
3. **Contestation is expensive**, which is what stops "bolt on a second
   assessor to buy a tier" from working: a second assessor that disagrees
   *lowers* your permission until the contested set is worked through as
   Traces. The incentive points at the research, not at the number.

`argue` and `argue cautiously` still require explicit researcher confirmation
(execution spec §10) — but note what that now is: a *speech act by the
researcher about how far a proposition may travel*, which is a legitimate
human-specific role, and is entirely separate from *positioning a hit*, which
is not. Splitting those two is the reason this amendment does not reduce the
researcher's standing anywhere that matters.

### 4.8 `ReductionRecord` and `ResidueRecord` become mandatory here

Spec §53's `ReductionRecord` has never been implemented. Under flat assessment
it is no longer optional, because there are now two named reductions that every
partial study carries and that nothing else can express:

- the **unpositioned set** — what this study did not reach, and why;
- the **contested-unaddressed set** — disagreements recorded but not worked
  through as Traces.

A release whose positioning coverage is below 100%, or whose contested set is
non-empty, **must** carry a `ReductionRecord` naming each with a recovery
route, or the release refuses. This replaces the current situation in which
running out of assessment capacity is silently indistinguishable from having
decided the object is small.

`ResidueRecord` (§6.2, ported from ref-wiki) covers the adjacent but distinct
case: a route that was *stopped*, with why.

### 4.9 `weight` — its only two legal consumers, named explicitly

v1.0.0 defined `weight` on `OccurrencePosition` ("never read as a probability") without
giving it a job, which left it vestigial. Closed here: `weight` has exactly two legal
consumers, and resolution is not one of them.

1. **Triage ordering (`positions.py`, `queue_by_weight()`).** For any hit with no human
   position yet, sort the walk/review queue by the highest-confidence non-human position's
   `weight`, descending or ascending per researcher preference (attend to what a triage is
   most confident about first, or spend limited human attention on what it is *least*
   confident about — both are legitimate research strategies and the CLI exposes both via
   `--triage-order confident-first|uncertain-first`). This is Role A's "order the walk
   queue" power from the pre-amendment critique (§2.4-adjacent), now precisely specified.
2. **`min_weight_for_inclusion` (§4.3).** A policy may floor out low-confidence non-human
   positions from its own resolution, as defined in §4.3.

`weight` is never read by `standing_of()`, never breaks a tie in `concordance`, and never
substitutes for `independence_class`. Two positions with different `weight` and the same
`stance` are still just as concordant as two positions with identical `weight` — confidence
is not a form of corroboration.

---

## 5. Appendix revisions

### 5.1 Appendix C.1 — methodological invariants

**Amend:**

> ~~AI proposal remains distinguishable from evidence~~
> **every contribution remains distinguishable by its apparatus and conditions;
> distinguishability never implies precedence**

**Add two:**

> - **no assessor type holds default precedence; how positions compose is
>   always a declared, versioned, ablatable operation;**
> - **a position is never erased or overridden by another object's position;
>   supersession is self-scoped.**

Unchanged: Seed / Object Address / Lexical Anchor / Anchor Hit / Occurrence
[Position] remain distinct. The chain survives the rename intact — only the
last link's *semantics* changed, from verdict to position.

### 5.2 Appendix A — non-equivalence audit additions

- position ≠ verdict
- Position Set ≠ vote
- concordance ≠ truth
- contestation ≠ error
- assessor type ≠ authority
- positioning coverage ≠ certification
- weight ≠ probability
- **a human position ≠ ground truth**

### 5.3 §5 vocabulary table additions

`Occurrence Position`, `Position Set`, `Standing`, `Assessor Object`,
`Resolution Policy`, `Policy Ablation`, `Residue Record` — all project-local
operational constructs under the Ganjoor Ontograph / Mozare column.

---

## 6. What is ported from `ref-wiki`, and where it contradicts this amendment

The researcher's second project (`ref-wiki`, a Living Wiki Kit 1.0.0 instance)
was read for structurally useful patterns. It contains several, and one direct
contradiction that is named here rather than silently resolved.

### 6.1 Ported

1. **`unsupported_zones` and `counter_evidence` as *required* schema fields.**
   `00-system/schemas/claim-object.schema.json` makes both mandatory on every
   claim. This is excellent and fully flat-compatible: it forces a claim to
   disclose its own holes without ranking who found them. **Port to Ontograph's
   `FindingRecord` and `ClaimRecord` as required fields** — a Finding with an
   empty `unsupported_zones` is invalid. The instance's own live phrasing is a
   model for what Ontograph's contested/unpositioned disclosure should sound
   like: *"None recorded in the current candidate record; absence is not a
   completed external search."*
2. **Residue records** ("residue records why a route stopped", SYSTEM_DESIGN
   §2.3; LIFECYCLE Stage 5). This is Ontograph's missing §53 record with a live
   precedent. **Port as `ResidueRecord`**, and keep it *distinct* from
   `ReductionRecord` — ref-wiki folds the two notions together; Ontograph's
   spec already separates "a route was abandoned" (§19 reject-to-residue) from
   "a computation compressed something" (§53). Keep Ontograph's finer
   distinction.
3. **Relations recorded before they are classified** — `06-relations/` with
   `relation_status: candidate` and `use_status: [...]` on the record itself,
   40 of them in practice. This validates Ontograph §13→§14's Trace→
   Relation-Object lifecycle at working scale. **Port the field shape**
   (`relation_status` free string + `use_status` array +
   `current_claim_permission` on the same record).
4. **Graduated claim permission as a schema-enforced enum**
   (`may-note | may-describe | may-argue-cautiously | may-argue | blocked`).
   Ontograph's §16 ladder is prose in a skill file. **Port the enforcement
   mechanism**, keeping Ontograph's own wording.
5. **Handoff template sections** (`00-system/templates/TEMPLATE_handoff.md`):
   *Decisions not made*, *Negative constraints*, *Unresolved findings*,
   *Rollback*. **Port into the Ontograph release report**, where they are
   exactly the sections a partial-coverage release needs and currently lacks.
6. **Write-path convergence with an inert proposal queue**
   (`_proposals/proposals.jsonl`, inert until moved). **Port the file-separation
   mechanism** — a proposal ledger separate from a positions ledger — but see
   §6.2 for the change of rationale.

### 6.2 Where `ref-wiki` contradicts this amendment — named, not resolved

`SYSTEM_DESIGN.md` §2.2 and `AGENTS.md` §2 state an explicit **authority
hierarchy**: "Immutable original, verified external primary, author
confirmation, accepted canonical record, derived witness, interpretive
synthesis, candidate/AI material... **Everything a model produces is level 7.
Fluency never upgrades evidence; only human adjudication or recorded evidence
does.**"

That is a ranked precedence order over contribution types — structurally the
same thing this amendment removes from Ganjoor Ontograph. The tension is real
and should be visible rather than papered over.

Three observations that make the divergence precise:

1. **The defensible core survives translation.** "Fluency never upgrades
   evidence" is *not* a human-supremacist claim at all; it is the claim that
   *plausibility ≠ warrant*, which is fully flat and which Ontograph should
   keep in spirit. Note also that ref-wiki's own sentence contains the escape
   hatch: "only human adjudication **or recorded evidence**." The disjunct
   already admits a non-human upgrade path.
2. **The part that does not survive is indexing the hierarchy on *who produced
   it* rather than on *what conditions were recorded*.** In Ontograph that
   indexing is replaced by `independence_class` + apparatus disclosure +
   contestation rate.
3. **The divergence is justified by purpose, not by inconsistency.**
   ref-wiki's job is fixity and attribution of *externally authored documents*,
   where "who wrote this" genuinely is the primary question and an authority
   hierarchy is the right tool. Ontograph's job is *conditioned encounters with
   a corpus*, where "under what conditions was this seen" is the primary
   question and a hierarchy over producers answers the wrong one. Two systems,
   two purposes, two models — deliberately, and now on the record.

**No recommendation is made here about changing ref-wiki.** Whether its
hierarchy should be revisited is the researcher's call and outside this
document's scope. What is inside scope is that the two systems now differ *by
decision*, and this section is the place that says so.

### 6.3 What is explicitly *not* ported

The proposal queue's rationale. In ref-wiki, `_proposals/` is separate because
*model output is lower tier*. In Ontograph after this amendment, the separation
survives with a different and better justification: **a proposal is a different
speech act from a position.** Any object may propose (a candidate anchor, a
description, a rule). Any *registered assessor object* may position. An agent
issuing an `OccurrencePosition` is positioning, not proposing, and its row goes
in the positions ledger like everyone else's — with its apparatus disclosed and
its independence class recorded.

---

## 7. What this changes about earlier analysis

For continuity with the critique that preceded this amendment:

| Earlier finding | Status |
|---|---|
| L1.1 distinguishability was the real invariant, not human exclusivity | **superseded and strengthened** — distinguishability is necessary but insufficient; non-precedence and non-erasure added (§2.1) |
| L1.2 an `inventory` tier is needed | **adopted** as a first-class mode (§4.2) |
| L1.3 mandatory triage ablation | **generalized** to type-neutral policy ablation (§2.3) |
| L1.4 Trace as the template for disagreement | **adopted and automated** (§2.4) |
| L1.5 `ReductionRecord` unimplemented | **still true, now mandatory** (§4.8) |
| L1.6 split `ambiguous` into ambiguous/deferred | **superseded** — absence of a position is already first-class; no enum change needed (§3.1) |
| L2.3 `agent` proposes / `rule` validates against a human calibration sample | **superseded** — the human-reference assumption is removed; receipts validate against a *named reference assessor set* (§4.5) |
| L2.7 permission ceiling keyed off mode, assuming human-final | **replaced** by §4.7's composition-and-contestation table |
| L3.1, L3.3–L3.11 technical defects | **all still hold**, unchanged by this amendment |
| L3.2 hardcoded `assessor_type="human"` | **still holds, and is now F01** — the first implementation row |

---

## 8. Implementation plan (file/function level)

### 8.1 New modules

| File | Contents |
|---|---|
| `src/ontograph/positions.py` | `OccurrencePosition`, ledger IO on `corpus/occurrence-positions.jsonl`, `active_positions(ledger, hit_id, object_id) -> dict[assessor_id, Position]`, `standing_of()`, `position_coverage()`, `contested_trace_candidates()`, `queue_by_weight(hits, order="confident-first"\|"uncertain-first")` (§4.9) |
| `src/ontograph/assessors.py` | `AssessorObject`, registry IO on `objects/assessor-objects.jsonl`, `resolve_assessor()`, `independence_classes_of()` |
| `src/ontograph/resolution.py` | `ResolutionPolicy`, `resolve(position_set, policy) -> Stance \| None` (applies `min_weight_for_inclusion` before composing, §4.3/§4.9), `policy_ablation(hits, positions, declared, alternatives) -> dict`, `contested_share(hits, positions, policy) -> float` (feeds §4.7's threshold test) |
| `src/ontograph/claims.py` | `ceiling_for(operation_record) -> Permission` implementing §4.7, reading `policy.contestation_threshold` (null treated as 0.0) against `resolution.contested_share()`; `PermissionError` |

### 8.2 `census.py`

- `HitOccurrenceAssessment` (lines 104-129): retained as a **read-only legacy
  shape**. `load_hit_assessments()` (288-311) keeps reading
  `corpus/hit-assessments.jsonl` and maps each row to an `OccurrencePosition`
  with `assessor_object_id = f"legacy:{assessor_type}:{assessor_id or 'unknown'}"`.
- `supersede()` (138-167): add the cross-assessor guard — raise when
  `predecessor.assessor_object_id != new assessor`. **This is §3.3's
  enforcement point.**
- `active_decision()` (170-182) → `positions.active_positions()`, keyed per
  assessor.
- `assessed_full_coverage()` (232-247) → `positions.position_coverage()`
  returning the §4.1 composition dict, not a 2-tuple. The
  `legacy-poem-decision` zero-coverage rule carries over verbatim.
- `enforce_mode_completeness()` (250-267) → `enforce_mode_requirements(mode,
  hits, positions, policy)`: refuses `positioned-full` on any unpositioned hit;
  refuses **every** aggregate mode when `policy is None`; refuses
  `positioned-concordant` on any `single-position`, `corroborated-weak`, or
  `contested` hit.
- `IncompleteAssessmentError` (204-216): message gains the standing
  distribution and the list of declarable policies.
- `resolve_mode_alias()` (219-229): `assessed` and `assessed-full` both become
  deprecated aliases for `positioned-full`, warning on stderr.
- `apply_occurrence_rule()` / `validate_rule_against_reviewed_material()`
  (434-485): emit `OccurrencePosition` rows under a rule assessor object;
  validation report records the *reference assessor set* rather than "human."
- Estimator functions (490-547): unchanged; callers add the in-sample standing
  distribution.

### 8.3 `walk.py` / `walk_state.py` — the hardcoded-human fix (F01)

- **Delete** `assessor_type="human"` at `walk.py:245` and `walk_state.py:262`.
  `run_walk()` gains a **required** `assessor_object_id` parameter with **no
  default**. Refusing to guess who is positioning is the flat commitment made
  operational at the exact line that previously violated it.
- `walk.py:237`'s `supersede(active, ...)` inherits §8.2's cross-assessor guard.
- `walk.py:378` `append_walk_event()` hardcodes `actor_type="human"` — take it
  from the assessor object.
- **Wire `cli.py:459` to `walk_state.run_walk`** (the identity-based state
  machine, currently built, tested, and imported only by tests — see L3.3),
  retire `walk.py`'s position-indexed script reader, expose `--resume`, and fix
  `_widen()`'s non-cumulative sample-size bug (L3.9).

### 8.4 `cli.py`

- `--mode` choices (1278, 1284, 1290, 1296, 1301) →
  `["anchor","inventory","positioned-full","positioned-concordant","estimated",
  "assessed","assessed-full"]` (last two deprecated aliases). This also closes
  the existing divergence where `SKILL.md` documents modes argparse rejects.
- New `--policy {none|concordance|assessor:<id>|weighted:<file>}` on every
  object-incidence verb; absent → the study default from `study.yml`; absent
  there → refuse with the declarable list (§4.3).
- New `--as <assessor-object-id>`, **required**, on `walk` and `assess`.
  `--assessor-type` (1269) is **removed**: the type comes from the registry, so
  it cannot be spoofed per-invocation.
- New `--triage-order {confident-first,uncertain-first}` on `walk`, default
  `uncertain-first` (spend limited human attention where the machine is least
  sure, the more conservative default). Optional; absent means unordered
  (current behaviour). Implements §4.9.
- New verb `ontograph assessor add|list`.
- New verb `ontograph policy declare|list`.
- `_assess_hit()` (408-456): writes an `OccurrencePosition`.
- `_census` / `_map_recurrence` / `_companions` / `_ablate` / `_compare`: every
  result gains `positioning`, `standing`, `resolution_policy`, and
  `policy_ablation` blocks.
- `_record_add()` (734-782): after the existing governed-operation check
  (770-779), enforce `claims.ceiling_for()`; refuse a Finding or Claim whose
  declared permission exceeds the ceiling. **This is the §4.7 enforcement
  point.**
- `_field_build()` (245-286): scope grammar (execution spec §8 / row V201) and
  drop the unconditional `poem_ids` inline at line 283.
- Thread `corpus_snapshot_id` from the index-cache meta into every
  `census_from_index()` call, eliminating the measured 780-second content-signal
  walk (L3.1).

### 8.5 `result_cards.py`

`build_result_card()` gains a mandatory composition sentence — *"218 eligible
hits; positioned by 3 assessors; 173 concordant, 22 weakly corroborated, 23
contested; resolved under `concordance`"* — plus a `contested` count.
`_choices()` (20-41) gains: *open contested hits as Traces*, *position under a
second assessor*, *declare or change the resolution policy*.

### 8.6 `records.py`

Add `ResidueRecord`, `ReductionRecord`, `ClaimRecord`. Add
`unsupported_zones` and `counter_evidence` as **required** on `FindingRecord`
and `ClaimRecord` (§6.1). Widen `cli.py:731`'s `U04_RECORD_TYPES` to include
`relation` (whose class already exists but is unreachable), `residue`,
`reduction`, `claim`.

### 8.7 `release_v2.py` / `report_v2.py`

- Release refuses when coverage < 100% or the contested set is non-empty and no
  `ReductionRecord` covers them (§4.8).
- `report_v2.render_release_reports()` (currently prints candidate
  `proposed_by` but **no assessor provenance at all**) gains an **Assessment
  composition** section: per-assessor counts, apparatus, independence classes,
  standing distribution, contestation rate, resolution policy, policy ablation.
- Add the ported handoff sections: *Decisions not made*, *Unresolved findings*,
  *Negative constraints* (§6.1.5).

---

## 9. Migration

New `migrate.py` step `migrate_to_positions()`, non-destructive, `--apply`-gated,
with a before/after-hash receipt, following the existing §15 conventions.

1. Each `corpus/hit-assessments.jsonl` row → **one** `OccurrencePosition`.
   `accepted→occurs`, `rejected→does-not-occur`, `ambiguous→undecidable`.
   `assessor_object_id = "legacy:<assessor_type>:<assessor_id|unknown>"`, with
   a synthesized `AssessorObject` per distinct value and
   `independence_class = "legacy-unknown"`. **One row in, one row out — never
   fanned**, matching the existing §15.5 rule.
2. `legacy-poem-decision` rows migrate with the marker intact and continue to
   provide zero coverage.
3. Each migrated study gets a `ResolutionPolicy` of kind
   `named-assessor(legacy:human:*)` written **as an explicit declaration with
   `declared_by: "migration"`** — so the old behaviour is preserved *as a
   visible choice*, never as a hidden default. This is the single most
   important migration decision: it converts an invisible assumption into a
   record the researcher can inspect and change.
4. **Existing releases are downgraded, and this is correct.** A pre-amendment
   `assessed-full` result maps to `positioned-full` +
   `named-assessor(single assessor)`, which under §4.7 permits *describe
   distribution under declared conditions*, not *argue*. `release verify`
   reports this explicitly rather than silently re-labelling. Say it plainly in
   the changelog: those results were computed on one access route, and the new
   model declines to call one access route an argument.

### 9.1 Test impact (current: 336 passed / 10 skipped / 1 xfailed)

- **Unchanged, and this is the key compatibility property:** every fixture
  arithmetic assertion (mirror 5/27, companions `[9101,9102,9201]`, ablation
  1/3 and 1/2, the 9106 anchor-vs-assessed canary). With one migrated assessor
  under `named-assessor` resolution the numbers are identical. Make this an
  explicit acceptance criterion of F-row closure: *if a fixture number changes,
  the migration is wrong.*
- **Mechanically modified (~8 sites):** tests asserting literal
  `assessor_type="human"` — `test_t05_per_hit_assessment.py`,
  `test_t06_mode_completeness.py`, `test_t07_walk_state.py`, `test_walk.py`,
  `test_t06_cli_enforcement.py`.
- **Extended:** `test_t06_mode_completeness.py` gains `policy is None` refusal
  and `positioned-concordant` cases; the `--mode` choices test; the
  `SKILL.md` scripted-replay tests.
- **New required discriminating fixture** (in the spirit of execution spec §14,
  and for the same reason EXTERNAL_REVIEW's Finding 1 existed): two assessor
  objects positioning the *same* hits with *differing* stances, such that
  `concordance`, `named-assessor(A)` and `named-assessor(B)` produce **three
  different numbers**. If they do not diverge, the fixture proves nothing and a
  cheating implementation passes green.
- **Nothing is deleted.** Estimated churn: ~15 modified, ~12 added.

---

## 10. Ledger — Phase F (flat assessment)

Rows are in dependency order. One row per iteration; flip to `done` only when
Verify passes; never edit a `done` row's Verify.

| ID | Task | Refs | Verify | Status |
|---|---|---|---|---|
| F01 | Remove hardcoded `assessor_type="human"`; `run_walk` takes a required `assessor_object_id`; cross-assessor `supersede` refusal | §3.3, §8.3 | a walk with no `--as` refuses; a supersede across assessors raises; existing fixture split still reproducible with an explicit `--as` | todo |
| F02 | `assessors.py` + `ontograph assessor add/list` + registry | §3.2 | register 3 assessors incl. two sharing an independence class; round-trip | todo |
| F03 | `positions.py`: record, ledger, `active_positions`, `standing_of`, `position_coverage` | §3.1, §3.5, §4.1 | standing unit tests over all five standings | todo |
| F04 | Migration `migrate_to_positions()` + synthesized legacy policy | §9 | copied workspace migrates; **every fixture number unchanged**; original untouched | todo |
| F05 | `resolution.py` + `ontograph policy declare/list` + `--policy`, incl. `contestation_threshold` and `min_weight_for_inclusion` fields | §4.3 | the divergence fixture yields three different numbers under three policies; a policy with `min_weight_for_inclusion=0.6` excludes a low-weight non-human position from that policy's coverage; an unset threshold behaves as 0.0 | todo |
| F06 | `census.py` rewire: coverage composition, `enforce_mode_requirements`, no-policy refusal | §4.2, §8.2 | no-policy aggregate refuses and names declarable policies; `positioned-concordant` refuses on any contested hit | todo |
| F07 | `--mode` surface: `inventory`, `positioned-full`, `positioned-concordant`; deprecate aliases | §4.2, §8.4 | `inventory` runs with zero positions; `SKILL.md`'s documented modes all parse | todo |
| F08 | Contested → automatic Trace candidates | §2.4 | contested hit mints a TraceRecord carrying every position + source return | todo |
| F09 | Policy ablation on every aggregate result | §2.3, §8.4 | result carries figures under ≥2 policies; absent block = test failure | todo |
| F10 | `claims.py` ceiling + `contested_share()` + enforcement in `_record_add` | §4.7, §8.4 | a Finding claiming `argue` on a single-assessor result refuses; same result under concordance+corroboration passes; a result whose contested share exceeds its policy's `contestation_threshold` caps at "describe locally" even at 100% coverage | todo |
| F13 | `positions.queue_by_weight()` + `walk --triage-order` | §4.9, §8.3, §8.4 | an unpositioned queue sorted `uncertain-first` puts the lowest-weight non-human position first; `confident-first` reverses it; positions with no weight sort last regardless of order | todo |
| F11 | `ResidueRecord`/`ReductionRecord`/`ClaimRecord`; required `unsupported_zones`/`counter_evidence`; release refusal on uncovered reductions | §4.8, §6.1, §8.6 | release with 60% coverage and no ReductionRecord refuses | todo |
| F12 | Release report assessment-composition section + ported handoff sections | §6.1.5, §8.7 | report names per-assessor counts, apparatus, contestation, policy, ablation | todo |

**Not in Phase F, still owed from the prior critique** (independent of this
amendment, and F01/F07 should not wait for them): the 780-second
`corpus_content_signal` on every hit-producing verb (L3.1), the scope grammar
(V201/L3.4), non-reproducible `abs(hash())` candidate IDs (L3.5), the
`needs_vocabulary` flag (L3.6), the 1.6 MB `field build` payload (L3.7), and
`inquire --refresh` writing a SQLite file into the pinned corpus root (L3.8).

---

## 11. Closing rule

The apparatus records how differently-conditioned objects — a researcher, a
rule, a model, a retrieval score, an editorial apparatus — stand toward the
same textual encounter, and declines to decide among them on its own authority.
Where they converge, that convergence is evidence. Where they diverge, that
divergence is the research. Neither outcome is produced by ranking the objects
that produced it.
