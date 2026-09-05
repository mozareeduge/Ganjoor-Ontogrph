# Ganjoor Ontograph — Completion Plan (Phase 9 + session leftovers)

**Goal:** Carry the Ontograph apparatus from "v0.1 gates green on fixture, real-corpus integrated, Phase 9 half-started" to "P9.9 human-reviewed checkpoint" — finishing the interrupted session's work first, then Chains A and B, plus the non-ledger items (env, sync loop, upstream contributions) it left hanging.

**Architecture:** All work happens in
`C:\Users\Zarinpal\Documents\Personal Formal Documents\Artworks\digital art\Ganjoor-Ontograph\Ganjoor-Ontogrph\ganjoor-ontograph\`
on branch `ontograph/v0.1-build` (remote `origin` = mozareeduge/Ganjoor-Ontogrph; upstream = erfanbashar1 fork). The ledger (`implementation/IMPLEMENTATION_LEDGER.md`) remains the single source of truth: mark row in-progress → implement → verify → flip to done → commit+push, exactly as Phases 0–8 were built. Phase 9 is explicitly guided (user present at chain closeouts and before finalizing P9.5's design) — never loop-driven.

**Standing evidence rules (from the project's own discipline):**
- Fixture (134 passed / 10 honestly-skipped / 1 strict-xfail) is the regression floor; every P9 row re-runs the whole suite plus a real-corpus check, since Phase 9 touches `field.py`, `cli.py`, `census.py`.
- Never silently blur anchor-level vs assessed-level (the 9106 divergence is the canary).
- Real findings get ledger Notes, not silent fixes. Never edit a done row's Verify to make it pass.

---

## Track 0 — Resume-safe baseline (do first, before any new work)

**Why:** the interrupted session left uncommitted, half-wired work; the current environment can't even run the suite.

- **T0.1 — Environment:** `pip install -e .` + `pytest` into a project venv at
  `Ganjoor-Ontogrph\ganjoor-ontograph\.venv\` (system Python 3.11 has no pytest; `ontograph` unimportable today). Verify: `python -c "import ontograph"` and a quick `pytest tests/test_workspace.py -q` (4 passed).
- **T0.2 — Land P9.1's surviving half** (the working-tree diff is correct as far as it went — `new_study(corpus_root=...)`, `read_study_config()`, `_resolve_corpus_root()` on 8 verbs — but incomplete):
  1. `cli.py:389` — `--corpus-root` is still `required=True`; make it optional on all corpus-consuming verbs (`required=False`, `default=None`). This is the actual point of P9.1.
  2. Write the P9.1 fixture test (TDD: write first, watch it fail on `required=True`, then pass): `study new --corpus-root <fixture>` then `census <study> --object <addr>` with **no** `--corpus-root` succeeds and matches the explicit-flag result; explicit flag still overrides a stored value; no stored root and no flag → clean `CLIError` (exit 1, stderr, empty stdout).
  3. Also verify `field build` and `assess` (non-`with_corpus` verbs that gained the resolver) behave the same way.
  4. Run full suite (expect 134+new green). Flip ledger row P9.1 → done with honest Notes (including that this resumed an interrupted session, and which verbs were rewired). Commit+push.
- **T0.3 — Sync hygiene:** after the T0.2 push, local == origin. If the user wants the continuous two-way sync loop (cloud↔local, "keep the better/more complete version, ask on ambiguity"), set it up as a Hermes cronjob *after* confirming design with the user — do not silently auto-commit; ambiguity (uncommitted local edits vs cloud changes) triggers a question, per the user's own words.
- **T0.4 — Offline queue:** clean out `.claude/sessions/` + `.claude/state/` (untracked harness-mem leftovers from the offline session) — either gitignore or delete, decided by inspection of what the harness expects.

## Track 1 — Chain A: infrastructure (P9.2–P9.5-A)

> Chain A's Verify bar: full suite green after each row + real-corpus check; closeout requires materially faster wall time than P8.2's numbers (P8.2 recorded: `field build` 1m21s; single-word census timed out at 2min).

- **T1.1 (P9.2) — Corpus-root-keyed index cache.**
  - New module `src/ontograph/index_cache.py` (or extension of `corpus.py`): cache SQLite index under a deterministic path derived from **corpus root + content signal** (manifest hash + file count + a cheap per-shard fingerprint — never mtime alone).
  - Reuses the already-proven `corpus.build_index()` (240s cold on real corpus — that cost is paid once).
  - Cache-invalidation test: change the corpus root (fixture copy), assert stale results are never served.
  - Ledger P9.2 → done, commit.
- **T1.2 (P9.3) — Rewire census verbs onto the cache.**
  - `census`/`calibrate`/`map recurrence`/`companions`/`ablate`/`compare`/`field build` all go through the cache; fixture numbers must not change at all.
  - Full suite unmodified-green + a timing assertion on the real corpus (warm call in seconds, not minutes). Ledger P9.3 → done, commit.
- **T1.3 (P9.4) — Field scope becomes a real filter.**
  - `field build` writes `field/scope.json`; `census`/`companions`/etc. read it and intersect with their own query.
  - Regression test: field scoped to `sample1` + object present only in `sample2`'s poems → 0 hits inside the study.
  - Watch for: scope intersection must not break P9.1's stored-corpus flow. Ledger P9.4 → done, commit.
- **T1.4 (P9.5-A) — Chain-A closeout (checkpoint with user).**
  - One command: full suite green + `p8_2_worked_example_smoke_test.py` re-run with timed numbers, materially faster than P8.2's originals.
  - **Stop here; report to the user before starting Chain B.**

## Track 2 — Chain B: methodology (P9.5–P9.9, guided)

> Chain B's binding constraints (user's own words, recorded in the ledger): P9.5 must surface possible continuations without bounding the researcher's agency; P9.8 defaults to artifact/HTML + Markdown report.

- **T2.1 (P9.5) — Guided calibration/assessment flow. Design first, present before building.**
  - Sketch the interaction shape (sample pull → per-hit context-ladder walkthrough → next-action choices: accept/reject/ambiguous, narrow anchor, split object, widen/stop sample, promote to Trace; batched `assess` calls at the end).
  - **Present this design to the user before implementing** (the ledger requires the user review before another round of their own testing).
  - Then build: fixture walkthrough of mirror's 7 hits reaches the exact accepted/rejected/ambiguous split of `canonical-study-assessments.json` without calling `assess` per hit.
  - Ledger P9.5 → done, commit.
- **T2.2 (P9.6) — SKILL.md concretely scripts the flow** (not just naming `assess`). Manual run from a fresh session reproduces P9.5's test. Commit.
- **T2.3 (P9.7) — HEART-object-scale test** (41 hits/11 poems, real sampling fraction, not just mirror's 7). Assessed-mode census/companions match hand-verified ground truth. Commit.
- **T2.4 (P9.8) — Release rendering.** `ontograph release` (or a light verb) renders Profiles/Findings/comparison/ablation numbers/Traces as HTML + Markdown by default. Fixture test: full Field Charter → calibrate → assess → compare → release produces both files with numbers matching ground truth (5/27 assessed prevalence; mirror×rust co-incidence divergence). Commit.
- **T2.5 (P9.9) — Chain-B closeout: real-corpus dry run.** A mid-size hit set (structurally similar to the جن task) through the whole guided flow to a rendered release. **Hand real output to the user; stop. Do not self-certify.** The user reviews before Phase 9 is called done.

## Track 3 — After P9.9 (out of ledger scope; only with user's Research-Situation justification)

- P8.2's open human-literary-review item: reading the mirror/rust real-corpus results (378-poem co-incidence, Saeb-Tabrizi dominance, 60.6% post-ablation retention, the Rumi couplet) against §45's narrative — genuinely the user's, not an agent's.
- Potential upstream contributions (real findings made in this repo's Phase 8: `PoemsCount` staleness at 132,591 vs 132,538; `_cat.json` slugging quirk) — as PRs to erfanbashar1 fork / ganjoor upstream, only if user wants.
- v0.2 mediation layer (§72) — out of scope until user asks.

## Risks / open questions

1. **The two earlier-session transcripts** were referenced but not received; plan is built from the ledger (which encodes their findings), the code state, and git history. If they contain requirements not in the ledger's Phase 8/9 notes, amend this plan.
2. **Real-corpus timing baselines** for P9.2/P9.3 depend on this machine's current load; the plan compares against P8.2's recorded numbers and states assumptions in the ledger Notes.
3. **The sync loop** (Track 0, T0.3) needs the user's confirmation on cadence and conflict policy before a cronjob is created — "keep the better version, ask on ambiguity" needs one concrete rule set before automating.
4. **Index-cache correctness** (P9.2) is the one genuinely novel engineering risk: a cache that serves stale or wrong-scoped results would silently corrupt every downstream number. Mitigation: content-signal keying + the invalidation test + full-suite re-run on every touch.
5. **Environment**: the project venv must be created before anything runs; if pip/network fails offline, the plan stalls at T0.1 — flag early.
