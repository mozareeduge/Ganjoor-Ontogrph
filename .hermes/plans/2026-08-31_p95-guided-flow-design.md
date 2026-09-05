# P9.5 Guided Calibration/Assessment Flow — Design for Evaluation

**Status:** provisionally approved by Mozare (voice: "I approve what you proposed for now, go on") — this document is the full design he should evaluate; build proceeds on it, amendments fold in as ledger Notes.
**Scope:** ledger P9.5. Spec refs §9, §27.2, §28.4. Verify target: scripted fixture walkthrough of mirror's 7 hits reaches the exact canonical split in `canonical-study-assessments.json` through the flow itself.

---

## 1. The problem being fixed

The user's own real-corpus test session (the source of Phase 9) did: raw anchor census (483 hits) → ad hoc Python keyword-bucket clustering → **zero calibration, zero `assess` calls**. That is exactly the Anchor Hit ≠ occurrence collapse the apparatus exists to prevent (spec §27.2's whole point). The methodology existed in the engine but nothing *walked* the researcher through it.

## 2. Design principles (binding)

1. **Surface, never bound** (Mozare's recorded rule): at every hit, all legitimate continuations are visible; no mode hides a move.
2. **Batch, not per-hit CLI:** decisions accumulate in-session; one `assess` call writes them.
3. **Deterministic engine, guided shell:** the flow adds no epistemic logic of its own — it sequences existing verbs (`calibrate`, census internals, `assess`) and adds nothing that could silently blur anchor-level vs assessed-level (the 9106 canary).
4. **Reproducible:** every guided session is replayable as a script (same decisions → same state), which is what the verify target exercises.

## 3. The verb

```
ontograph walk <study> --object <addr> [--sample N] [--resume]
```

- Pulls the study's calibrated sample for the object (spec default ~30, adjustable via `--sample`; falls back to the full hit set when smaller).
- For each hit: prints the context ladder (anchor line → couplet → poem header + neighboring couplets), then the decision prompt.
- On exit: writes all decisions through one batched `assess` invocation; prints a summary diff (accepted/rejected/ambiguous counts, any structural changes queued).

## 4. The decision prompt (per hit)

```
—— hit 3/7 · poem 9105 (Hafez, ghazal) ——
anchor 'آینه' — couplet: «...»
ladder: [1] line  [2] couplet  [3] poem context  [4] full poem

decisions  5 accepted · 1 ambiguous · 1 rejected   (this hit undecided)
choices:
  a / r / u   accept / reject / ambiguous          → this hit
  n           narrow the anchor (refine form)      → re-census fork
  s           split the object                     → structural fork
  t           promote this hit to a Trace
  w / x       widen / stop the sample
  ? 1–4       open the context ladder level
  Enter       leave undecided, next hit
  done        finish and write decisions
```

## 5. The choices in detail

| Choice | Effect | Mechanics |
|---|---|---|
| `a`/`r`/`u` | classify this hit as a real occurrence / not / unclear | recorded in the batch; shown as running counts |
| `n` narrow | the hit reveals the anchor form is too broad (spelling variant, homograph) | prompts for the refined form; **forks a sub-census** on the narrowed anchor; original sample pauses; resumed after |
| `s` split | the hit suggests two distinct objects share one anchor | prompts for the second object's address+form; both objects get independent samples; existing decisions stay attached to the object they were made on |
| `t` promote | this hit is itself a finding (relation-worthy) | writes a Trace record immediately (P4.1 records), then continues |
| `w`/`x` widen/stop | adjust sampling mid-flow | widen: increases N via `calibrate`'s rule; stop: ends sampling, proceeds to write-out |
| `?` level | more context before deciding | ladder levels 1–4, non-destructive |
| `Enter` | skip for now | hit stays undecided; surfaced again at write-out as a reminder list |

**Availability rule:** `n`, `s`, `t` are available on *every* hit, mid-sample — no "after the sample" restriction (per Mozare's answer to the fork question: forking mid-sample is allowed; the sample pauses and resumes around the fork).

## 6. Write-out (the batch)

One `assess` call writes: the accepted/rejected/ambiguous decisions (with per-hit rationale prompts — optional free text, defaulting to none), any Trace records, any anchor-narrowing/object-splitting as first-class ledger-visible structural events (new objects get `object add`, narrowed anchors get recorded as anchor revisions, not silent edits).

Undecided hits at write-out: listed explicitly; `assess` writes only decided ones; the census's assessed-mode numbers reflect only written decisions — **never imputed**.

## 7. Scripted mode (how the verify test drives it)

`ontograph walk` accepts a `--script <json>` file: an ordered list of per-hit responses. The fixture test drives mirror's 7 hits with responses reproducing the canonical rationale:

- 9101 a · 9102 a · 9103 a · 9104 a (spelling-variant note: anchor آیینه already covered — no narrow needed) · 9105 **u** ("mirror of the heart") · 9106 **r** ("mirror of memory") · 9201 a.

Assert: written assessments == `canonical-study-assessments.json` exactly, assessed-mode census matches ground truth (assessed prevalence 5/27-scale numbers per P2.2/P2.3).

## 8. Non-goals (this phase)

- No interactive UI beyond the terminal prompt (HTML rendering is P9.8).
- No mediation logic (v0.2, §72).
- No auto-classification: the engine never suggests accept/reject — that would cross the self-certification line the v2.3.0 rework exists to prevent.

## 9. What P9.6–P9.9 inherit

- P9.6 scripts this flow into `persian-poetry-ontograph/SKILL.md`.
- P9.7 re-runs it at HEART scale (41 hits/11 poems).
- P9.8 renders the resulting workspace state (P9.5's summary diff becomes part of the release).
- P9.9 hands a real-corpus dry run to Mozare — the human checkpoint.
