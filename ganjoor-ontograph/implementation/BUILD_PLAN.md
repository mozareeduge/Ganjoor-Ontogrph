# Build plan — Ganjoor Ontograph engine, CLI, and skill

This is the plan a fresh Claude Code context executes, one bounded task at
a time, to go from "spec + skill scaffold" (what exists today) to a
working v0.1 apparatus that produces exactly the outputs described in
`../USER_JOURNEY.md`. It is designed to be run under `/loop` from a fresh
context with no memory of how it was written — see `HOW_TO_RUN.md` for the
literal kickoff instructions and `.claude/skills/ontograph-build/SKILL.md`
for the per-iteration algorithm. This file is the *why* and the *what*;
`IMPLEMENTATION_LEDGER.md` is the *right now, exactly this task*.

## Source of truth

Every task below cites a section of
`../Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md`. Where this
plan and the spec disagree, the spec wins — fix this plan, not the spec,
unless the disagreement is itself a spec bug (in which case: stop, don't
silently pick a side, flag it the same way `EVALUATION.md` flagged the
v2.2.0 commit-SHA contradiction).

## Provisional engineering defaults (Appendix C.3 — replaceable, not invariant)

These are decided here so the loop never has to invent them mid-build and
two different iterations never disagree:

- **Language / packaging:** Python 3.11+, `src/` layout, `pyproject.toml`,
  installed as an editable console script named `ontograph` (spec §59, §62).
- **Test runner:** `pytest`. Every ledger row's Verify command is a pytest
  invocation or the literal CLI call it's testing.
- **Storage:** SQLite for the derived research index (§57); JSONL/YAML for
  workspace records (§60); each workspace is a git repo (§60, v2.3.0).
- **Fixture corpus:** `../fixtures/mini-ganjoor/` — a small, hand-built,
  schema-accurate synthetic corpus with known ground truth (§67), used for
  every automated test. The real `ganjoor-data`/fork corpora are used only
  in Phase 8, manually, never inside the automated loop (they require a
  multi-GB clone the loop should not attempt unattended).
- **Estimator default:** stratified proportion estimator + Wilson score
  interval, per spec §27.2/Appendix C.3 as amended in v2.3.0.

## Phases

Each phase is a dependency boundary — later phases assume earlier ones are
`done` in the ledger. Within a phase, rows can be done in any order unless
a row's Depends-on column says otherwise.

### Phase 0 — Bootstrap and ground truth

Nothing downstream is trustworthy without a fixture corpus whose true
answers are known in advance (spec §67: "crafted miniature corpora where
the true distribution is known"). Phase 0 builds that corpus and the
package skeleton every later module imports.

### Phase 1 — Deterministic core

Normalization, field construction, anchor/hit census, the SQLite index,
and workspace-as-git-repo. This is the layer the spec calls the
"deterministic corpus channel" (§25) — it must be right before anything is
built on top of it, because every later mode/gate distinction (anchor vs.
assessed vs. estimated, §8.1) depends on this layer never silently
blurring "matched" into "occurred."

### Phase 2 — Calibration and occurrence assessment

The anchor→object gate (§8.1, §9, §70). This phase is where the estimator
default and the ambiguous-hit denominator rule (both v2.3.0 additions) get
implemented and tested — they have no precedent to copy from the fork's
retrieval layer, so they need their own fixtures.

### Phase 3 — Metrics and mapping operations

Everything in spec Part V operation packs A–D (Trace an Object, What Meets
This Object, Relation Scale Profile, Compare Fields) plus Ablation (pack E).
Mediation (pack after Relation-Objects exist) is explicitly v0.2 scope
(§72) and is not in this phase.

### Phase 4 — Records, events, release

Trace, Relation-Object, Profile, Experiment, Finding records; the
append-only EventRecord log; the ResearchRelease generator including the
v2.3.0 `data_license_notice` requirement.

### Phase 5 — CLI

Wires every prior phase's functions to the `ontograph` console script with
`--json` output, matching the exact verb names in spec §62 (and the
disambiguation note in §25 v2.3.0: never `search`/`query` as Ontograph verb
names — those belong to the fork's separate surfaces).

### Phase 6 — Claude Code binding

Point the already-scaffolded `.claude/skills/persian-poetry-ontograph/`
skill at the now-real CLI, and add the settings.json allowlist from spec
§79.

### Phase 7 — Tests and gates

The deterministic corpus tests (§65), epistemic contract tests (§66), and
close–distant loop tests A–F (§67) all run against the fixture corpus.
Phase 7 closes with the five implementation gates (§69) and the
occurrence-assessment scalability gate (§70), evaluated against the
fixture. **v0.1 is done when Phase 7 passes in full** — this is the loop's
stop condition (see `.claude/skills/ontograph-build/SKILL.md`).

### Phase 8 — Real-corpus integration (manual, outside the loop)

Not part of the automated ledger. Once Phase 7 passes, a human (or a
separately-invoked, explicitly-approved session) points the pinned-corpus
config at the real corpus, rebuilds the real SQLite index, and runs the
spec's own worked example (§45, mirror/rust in Hafez) as a smoke test.
This repository (`mozareeduge/Ganjoor-Ontogrph`, forked from
`erfanbashar1/persian-poetry-ai-agent-plugin`) already vendors the real
`ganjoor-data` corpus at its root — no multi-GB clone is needed here the
way it was when this package lived in a separate scratch repo. Phase 8
stays excluded from the automated loop anyway: pointing the engine at
~132,000 real poems and manually checking the worked example's narrative
against real output is exploratory human review, not a mechanically
verifiable ledger row, and an unattended loop declaring it "done" on its
own would be exactly the kind of self-certification EXTERNAL_REVIEW.md
warned against.

## Definition of done for v0.1

All Phase 0–7 ledger rows `done`, and re-running the Phase 7 gate check
produces a clean pass with no `blocked` rows anywhere in the ledger. At
that point the correct status (per spec §69's own words) changes from
"implementation specification" to "v0.1 apparatus, gates passed on fixture
corpus, real-corpus integration pending" — not "finished," since Phase 8 and
the v0.2 reflexive relation layer (§72) remain.

**"Gates passed" must mean what it says.** An independent external review
(`../EXTERNAL_REVIEW.md`) found that the original fixture let a gate report
green while proving nothing: co-incidence/scale/ablation tests (P3.3, P3.6,
P3.8) had identical targets whether the engine correctly used assessed
occurrences or silently fell back to raw anchors, and the estimator gate
(P7.5/§70) was tested only at a tautological 100% sampling fraction. The
fixture and ledger have since been reworked (a divergence case, a
substring/token-boundary trap, a larger estimator-testable object, a
periodic Appendix A invariant audit — P3.9, re-run at P7.4) specifically so
that a cheating implementation cannot pass Phase 7 green. If a future
change to the fixture or ledger ever makes anchor-level and assessed-level
targets identical again, or makes the estimator gate testable only at
100% sampling, that change has silently undone this fix and should be
treated as a regression, not a simplification.

## What this plan deliberately does not include

Per spec §73–74: no matrix decomposition/latent-factor views, no
spectral/community diagnostics, no intermedial ontographic machines, no
graph database, no corpus-wide LLM labeling, no universal Persian
lemmatizer, no browser workbench. If a ledger row ever drifts toward one of
these, that row is out of scope — flag it, don't build it.
