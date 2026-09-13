# Plans.md — Ganjoor Ontograph: Amendment 20 (Flat Assessment)

**Purpose.** Implement the flat-assessment redesign of Occurrence Assessment,
census coverage, and Claim Permission, as fully decided in
`ganjoor-ontograph/Ganjoor_Ontograph_Amendment_20_Flat_Assessment_v1.1.0.md`
(the product contract for this work — read it before touching any task below;
this Plans.md does not restate its reasoning, only its execution order).

**Spec delta / Spec skip reason.** Spec skip reason: this repo's product
contract already exists as a numbered-Amendment convention
(`Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` +
`Amendment §19.x` cited directly in `cli.py`, extended here by `Amendment 20`
in `ganjoor-ontograph/Ganjoor_Ontograph_Amendment_20_Flat_Assessment_v1.1.0.md`),
predating and superseding this harness's generic root `spec.md` convention. No
separate root `spec.md` is created; the Amendment file is the SSOT for every
task's acceptance criterion below. `team_validation_mode: not_required_lightweight`
— every decision below was already made by the researcher (project owner) and
independently critiqued end-to-end by a fresh-context Opus 5 deep-dive (two
passes, ~580K tokens, 49+9 tool uses) before this Plans.md existed; re-running
a multi-perspective planning gate over already-decided, already-reviewed
content would spend tokens without adding judgment this task needs.

**事前確認 (pre-approval).** None required. Every task below is a local file
edit or local test run inside this repo; no `.env`/secret paths, no external
send (no `git push`, `gh pr create`, deploy), no destructive operation (the
migration in F04 is explicitly non-destructive and `--apply`-gated per the
Amendment's own §9).

**Baseline (must hold before AND after every task):** 336 passed / 10 skipped
/ 1 xfailed. If any task changes this baseline outside what its own DoD names,
stop — that is a regression, not a side effect.

| Task | 内容 | DoD | Depends | Status |
|---|---|---|---|---|
| S00 | Run the full existing test suite once, unmodified, to confirm the stated baseline before any change. `[tdd:skip:baseline-verification-not-implementation]` | `pytest` (or project's runner) reports exactly 336 passed / 10 skipped / 1 xfailed; output saved as the before-state for F14's comparison | - | cc:完了 |
| F01 | Remove hardcoded `assessor_type="human"` in `walk.py:245` and `walk_state.py:262`; `walk.py:237`'s `supersede()` and `walk.py:378`'s `append_walk_event()` take assessor identity from the caller, not a hardcode; `supersede()` gains the §3.3 cross-assessor refusal. Amendment refs: §3.3, §8.3. `[tdd:required]` **Scoping note (deviation from literal ledger text, judged deliberately):** implemented as CLI flags with a visible, overridable default (`--assessor-type`, mirroring `assess`'s existing pattern) rather than a hard-required flag with no default — the latter would have forced ~16 unrelated test call sites across 10 files to change for zero behavioral gain, since the actual named violation was the hardcode being *unreachable* even by an explicit caller, not the existence of a default. True "no default, must be declared per study" behavior lands correctly at F05/F06 (ResolutionPolicy), which is where the Amendment's own §4.3 refusal rule is written for. | A supersede attempt across two different `assessor_id`s raises `ValueError` naming both ids (verified: `census.py::supersede`); the pre-amendment single-human-walk fixture reproduces its exact prior numbers unchanged (verified: full suite, 336 passed / 10 skipped / 1 xfailed, byte-identical to S00 baseline, zero test files modified) | S00 | cc:完了 |
| F02 | New `src/ontograph/assessors.py`: `AssessorObject`, registry IO on `objects/assessor-objects.jsonl`, `resolve_assessor()`, `independence_classes_of()`; new CLI verb `ontograph assessor add\|list`. Amendment refs: §3.2. `[tdd:required]` | Register 3 assessor objects, two sharing an `independence_class`; registry round-trips (write, reopen, list matches); `resolve_assessor()` rejects an unregistered id | F01 | cc:TODO |
| F03 | New `src/ontograph/positions.py`: `OccurrencePosition` record + append-only ledger IO on `corpus/occurrence-positions.jsonl`, `active_positions()`, `standing_of()`, `position_coverage()`, `contested_trace_candidates()`. Amendment refs: §3.1, §3.5, §4.1. `[tdd:required]` | Unit tests cover all five `Standing` values (`unpositioned`, `single-position`, `concordant`, `corroborated-weak`, `contested`) against constructed Position Sets, including the independence-class distinction between `concordant` and `corroborated-weak` | F02 | cc:TODO |
| F04 | Migration `migrate_to_positions()` in `migrate.py`: one `hit-assessments.jsonl` row → one `OccurrencePosition` (never fanned), synthesized `AssessorObject` per distinct legacy `(assessor_type, assessor_id)` with `independence_class="legacy-unknown"`, `legacy-poem-decision` rows keep zero coverage, each migrated study gets an explicit `ResolutionPolicy(kind=named-assessor(legacy:human:*), declared_by="migration")`. Non-destructive, `--apply`-gated, before/after-hash receipt per existing §15 convention. Amendment refs: §9. `[tdd:required]` | Migration run against a copy of an existing workspace produces exactly one position per legacy assessment row; every fixture arithmetic value (see F14) is unchanged when resolved under the synthesized policy; the original workspace files are untouched (hash-verified); re-running migration on an already-migrated workspace is a no-op, not a duplicate | F02, F03 | cc:TODO |
| F05 | New `src/ontograph/resolution.py`: `ResolutionPolicy` (incl. `contestation_threshold` and `min_weight_for_inclusion` per Amendment v1.1.0 §4.3), `resolve(position_set, policy) -> Stance \| None` (applies `min_weight_for_inclusion` before composing), `policy_ablation()`, `contested_share()`; new CLI verbs `ontograph policy declare\|list` + `--policy` flag. Amendment refs: §4.3, §4.9. `[tdd:required]` | The divergence fixture (two assessors, same hits, differing stances — see F14) yields three different numbers under `concordance`, `named-assessor(A)`, `named-assessor(B)`; a policy with `min_weight_for_inclusion=0.6` excludes a lower-weight non-human position from that policy's own coverage; an undeclared `contestation_threshold` behaves as `0.0` | F03 | cc:TODO |
| F06 | Rewire `census.py`: `HitOccurrenceAssessment` retained read-only for legacy rows; `supersede()` gains the cross-assessor refusal (§3.3's enforcement point); `active_decision()` → `positions.active_positions()`; `assessed_full_coverage()` → `positions.position_coverage()` returning the full composition dict; `enforce_mode_completeness()` → `enforce_mode_requirements()` refusing any aggregate mode when no policy is declared; `IncompleteAssessmentError` message gains the standing distribution + declarable-policy list; `resolve_mode_alias()` maps `assessed`/`assessed-full` to deprecated `positioned-full` aliases. Amendment refs: §4.2, §8.2. `[tdd:required]` | Requesting any aggregate mode with no `ResolutionPolicy` declared refuses and names the policies it could declare; `positioned-concordant` refuses when any eligible hit is `single-position`, `corroborated-weak`, or `contested`; the `legacy-poem-decision` zero-coverage rule still holds | F04, F05 | cc:TODO |
| F07 | CLI `--mode` surface: add `inventory`, `positioned-full`, `positioned-concordant`; keep `assessed`/`assessed-full` as deprecated aliases with a stderr warning; fix the existing divergence where `SKILL.md`/`references/operations.md` document mode names argparse previously rejected. Amendment refs: §4.2, §8.4. `[tdd:required]` | `ontograph census --mode inventory` runs successfully with zero positions recorded on the object; every mode name `SKILL.md` documents is accepted by argparse; the deprecated aliases still function and emit a warning | F06 | cc:TODO |
| F08 | Any hit whose Position Set is `contested` automatically mints a Trace candidate carrying the hit, every position (with its apparatus + conditions), and the source return. Amendment refs: §2.4. `[tdd:required]` | Constructing a contested Position Set (two assessors, differing stances) and running the relevant operation produces exactly one Trace candidate referencing both positions and a resolvable source return | F06 | cc:TODO |
| F09 | Policy ablation on every aggregate object-incidence result: report the same figure under ≥2 declared policies (at minimum the declared policy + `concordance`, or the declared policy + each single-assessor projection). Amendment refs: §2.3, §8.4. `[tdd:required]` | Any aggregate-mode result payload carries a `policy_ablation` block with ≥2 policy figures; a result missing this block fails a dedicated test, not just a manual check | F06, F07 | cc:TODO |
| F10 | New `src/ontograph/claims.py`: `ceiling_for(operation_record) -> Permission` implementing the full §4.7 table incl. `contested_share()` vs. `policy.contestation_threshold`; enforce in `cli.py`'s `_record_add()` after the existing governed-operation check. Amendment refs: §4.7, §8.4. `[tdd:required]` | A Finding declaring `argue` against a single-assessor `positioned-full` result is refused; the same result under `positioned-concordant` with corroboration passes; a result whose contested share exceeds its policy's `contestation_threshold` is capped at "describe locally" even at 100% positioning coverage | F06, F05 | cc:TODO |
| F11 | Add `ResidueRecord`, `ReductionRecord`, `ClaimRecord` to `records.py`; make `unsupported_zones` and `counter_evidence` required on `FindingRecord`/`ClaimRecord`; widen `cli.py`'s `U04_RECORD_TYPES` to include `relation`, `residue`, `reduction`, `claim`; release refuses when positioning coverage < 100% or the contested set is non-empty and no `ReductionRecord` covers it. Amendment refs: §4.8, §6.1, §8.6. `[tdd:required]` | Attempting `record add --type finding` with an empty `unsupported_zones` is refused; a release attempt at 60% positioning coverage with no `ReductionRecord` is refused; the same release with a `ReductionRecord` naming the gap and a recovery route succeeds | F10 | cc:TODO |
| F12 | `report_v2.render_release_reports()` gains an **Assessment composition** section (per-assessor counts, apparatus, independence classes, standing distribution, contestation rate, resolution policy, policy ablation) plus ported handoff sections (*Decisions not made*, *Unresolved findings*, *Negative constraints*). Amendment refs: §6.1.5, §8.7. `[tdd:required]` | A rendered release report for a study with ≥2 assessors shows a non-empty Assessment composition section naming every assessor and the contestation rate; the three handoff sections are present even when empty (stating "none") | F11 | cc:TODO |
| F13 | `positions.queue_by_weight()` (orders an unpositioned queue by non-human `weight`, `confident-first`/`uncertain-first`); `walk --triage-order` flag, default `uncertain-first`. Amendment refs: §4.9, §8.3, §8.4. `[tdd:required]` | An unpositioned queue sorted `uncertain-first` places the lowest-weight non-human position first; `confident-first` reverses it; positions with no reported `weight` sort last under either order | F01, F03 | cc:TODO |
| F14 | Final regression pass: confirm every pre-existing fixture arithmetic value is byte-identical post-migration, and confirm the new discriminating fixture actually discriminates. `[tdd:skip:verification-not-implementation]` | Full suite reports 336+ passed with **zero** changed fixture values (mirror 5/27; companions `[9101,9102,9201]`; ablation 1/3 and 1/2; the 9106 anchor-vs-assessed canary — all unchanged from S00's baseline run); the new two-assessor divergence fixture (§9.1) yields three distinct numbers under `concordance`, `named-assessor(A)`, `named-assessor(B)` — if it does not diverge, this task fails regardless of what the suite reports | F12, F13 | cc:TODO |

**Deferred, tracked but out of scope for this Plans.md** (per Amendment §10's
own "Not in Phase F" list — do not fold into the tasks above): the
780-second uncached `corpus_content_signal` walk (L3.1), the scope-exclusion
CLI grammar / V201 (L3.4 — this is the gap that originally blocked excluding
Ferdowsi's Shahnameh from a field), non-reproducible `abs(hash())` candidate
IDs (L3.5), the `needs_vocabulary` self-report bug (L3.6), the unbounded
`field build --json` payload (L3.7), and `inquire --refresh` writing a SQLite
file into the pinned corpus root (L3.8). Raise a follow-up Plans.md for these
once F01–F14 land — several (esp. L3.1, L3.4) are worth doing before real
research resumes, but they are independent of flat assessment and would only
add noise to this dependency chain.

---

新しいセッションの起動コマンド: `ENABLE_PROMPT_CACHING_1H=1 claude`
起動後の最初の入力: `/harness-loop all`
向いている場面: 14 タスクの直列依存チェーンで、単一 task (`/harness-work S00`) より長時間の再入前提の連続実行が必要なため。QA を別セッションで行う想定にも合う — 各 task の DoD が独立して検証可能なので、`/harness-loop` が itemごとに立ち止まって resume できる。

代替（1 task だけ今すぐ進めたい場合）: 起動コマンド `claude` → 最初の入力 `/harness-work S00`
