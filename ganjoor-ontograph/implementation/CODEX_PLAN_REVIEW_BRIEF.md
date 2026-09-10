# CODEX PLAN REVIEW BRIEF — Ganjoor Ontograph, v0.2 track (2026-09-02)

You are evaluating and finalizing a research-apparatus implementation plan. You may EDIT the
plan artifacts listed in §3 (that is your whole write scope). Do NOT touch `src/`, `tests/`,
`fixtures/`, or anything outside that list.

## 1. Project in one paragraph

Ganjoor Ontograph is a command-line research apparatus (Python, `ganjoor-ontograph/` inside this
repo) for OOO-informed close/distant reading over the Ganjoor Persian poetry corpus (132,538 poems,
vendored read-only). Core discipline: a lexical Anchor Hit is never an object occurrence; co-incidence
is never a Relation-Object; estimates are never censuses; ambiguity stays visible; agents propose,
humans decide. v0.1 is DONE: branch `ontograph/v0.1-build` @ f19717ddf, suite 155 passed / 10 skipped /
1 xfailed, real-corpus worked example produced (mirror×rust: 378 poem-scale co-incidences, Saeb
dominant, survives ablation at 60.6%/54.8%). A binding forward spec exists (§3 item 1) with work
units T01–T13 (v0.1.1 trust repair), U01–U12 (v0.1.2 workflow), V201–V213 (v0.2.0 complete apparatus).

## 2. The reality check that triggered this plan revision

The researcher (Mohammad Zare) user-tested the apparatus with a hunch: "cluster Rostam's battle
strategies in the Shahnameh." The session produced a decent 17-episode × 15-label dataset + Persian
dashboard, but it BYPASSED the apparatus: labels were agent judgment, verified by spot-searching,
charted outside the tool. No ResearchSituation, no candidate object catalog, no per-hit assessments,
no censuses. His verdict: "the walk-in process is absent; the machine should guide toward ontography —
descriptive object listing, cataloging, relation mapping — the things the machine can check precisely
better than a human with limited memory. Too many rushed interpretations."

Diagnosis: the engine's epistemic guards all live DOWNSTREAM of object registration, and nothing in
the flow turns a hunch into a governed object catalog BEFORE any analysis runs. The flow never entered
the apparatus, so the guards never fired. The fix is an inquiry layer UPSTREAM, plus re-sequencing the
V rows so relation/mapping infrastructure lands before new analytic surfaces.

## 3. Artifacts to evaluate and improve (your write scope)

1. `ganjoor-ontograph/implementation/V0_2_HERMES_EXECUTION_SPEC.md` — the approved forward spec
   (T/U/V rows, gates A–H, non-negotiable invariants §3, CLI contracts §7). You may APPEND an
   "Amendment 2026-09-02" section; do NOT rewrite completed history.
2. `openspec/changes/v02-reality-tracked-update/proposal.md` — the new change proposal.
3. `openspec/changes/v02-reality-tracked-update/specs/*/spec.md` — four capability deltas
   (inquiry-intake, descriptive-catalog, guided-walk, operation-ledger).
4. `openspec/changes/v02-reality-tracked-update/design.md` — technical decisions.
5. `openspec/changes/v02-reality-tracked-update/tasks.md` — W-rows (inquire, catalog, walk upgrade)
   + the T→U→V resumption order.

Context you may read freely: `ganjoor-ontograph/implementation/SESSION_DIGEST_2026-09-02.md` (full
digest), `ganjoor-ontograph/implementation/IMPLEMENTATION_LEDGER.md` (build history), `ganjoor-ontograph/src/ontograph/*.py`
(current code; note walk.py, records.py, compare.py, census.py), `CLAUDE.md` at repo root.

## 4. Evaluate against these questions

1. Does the inquiry layer (inquire → catalog → walk) actually enforce ontographic discipline, or does
   it just add a ceremony step an agent will skip? What would make the flow the path of least resistance?
2. Are the anti-interpretation guards (candidate-tier catalogs, ambiguity gate, no auto-promotion)
   airtight as spec'd? Find the bypasses an agent session would realistically take and close them.
3. Is the V-row re-sequencing (V201 → V202 → V207 → V203 → rest) right? Anything in the existing
   T/U/V rows that conflicts with the new W-rows? Resolve conflicts explicitly.
4. Is "catalog proposal is corpus-computation, not LLM generation" (co-occurrence from the cached
   index, no model calls) the right call? Consider what hunch-normalization actually needs.
5. Are the tasks bite-sized, test-first, and QA-able by a light model executing one row per turn?
6. Anything missing for the researcher's actual acceptance test: he tests ONLY the ready-made
   version — hand him a flow where his hunch becomes a governed catalog, a walk he can drive,
   and a rendered catalog/report, with all labor done by the agent.

## 5. Output contract

- Edit the §3 artifacts in place (append the amendment to item 1; revise items 2–5 freely).
- Keep every epistemic invariant in the spec's §3 intact — never soften one.
- Keep CLI contracts consistent with existing verb grammar (`ontograph <verb> <study> ...`, `--json`).
- Do not add dependencies. Do not require a network or LLM at runtime.
- Finish with a short summary (≤300 words) of what you changed and why.
