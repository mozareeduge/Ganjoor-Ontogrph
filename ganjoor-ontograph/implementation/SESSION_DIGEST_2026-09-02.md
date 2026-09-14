# Session digest — Ganjoor Ontograph, 2026-09-02

Digest of: the build history (ledger + sessions 20260831_144820_acdef0 / 20260901_193123_e0b6f7e8),
the user's Rostam test, the wiki theory spine, and the verified current state.
Written for evaluation; nothing here rewrites the ledger or the V0.2 execution spec.

---

## 1. What exists (verified this session)

- **Branch** `ontograph/v0.1-build` @ `f19717ddf`, pushed. Phase 0–9.8 ledger rows all `done`.
- **Test suite re-run just now:** **155 passed, 10 skipped, 1 xfailed in 7.36s** (venv `ganjoor-ontograph\.venv`, bare `pytest -q` from `ganjoor-ontograph/`).
- **Untracked (expected):** `.hermes/`, `ontograph-workspaces/` — preserved, never commit.
- **Untracked (gap):** `implementation/V0_2_HERMES_EXECUTION_SPEC.md` — the binding forward plan is
  NOT committed. It should be committed before any v0.1.1 work starts, so the plan survives sessions.
- **P9.9 dry run staged** at `C:\Users\Zarinpal\AppData\Local\hermes\Temp\p99_dry_run\`:
  walk (3 decisions in a 30-hit sample: 2 accepted / 1 ambiguous / 27 undecided — honest partial coverage),
  census anchor (12,589 mirror hits / 8,792 poems) vs assessed (2 accepted poems / 132,538 denominator),
  companions (support 0 → lift correctly refused, not computed), ablation (no assessed relation to remove from),
  release `report.md` + `report.html` rendered. This is the human-review gate — awaiting Mohammad.

## 2. The work, overall — five layers

### Layer 1 — Spec (methodological authority)
`Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md`. Its intake into mozare-wiki
(`01-inbox/ganjoor-ontograph/EVALUATION.md`) fixed ten real defects: commit-SHA contradiction (§1.1),
ambiguous-denominator rule (§8.1.1), Wilson/FPC estimator default, `summarizer_model_version`
provenance, `data_license_notice`, git-versioned workspaces, MCP session protocol, qmd verb
disambiguation, and Part XIII runtime binding. Non-equivalence spine: anchor hit ≠ object occurrence;
co-incidence ≠ relation; estimate ≠ census; ambiguity stays visible; renderer computes nothing.

### Layer 2 — Engine v0.1 (Phases 0–7, all done)
Fixture `mini-ganjoor` with hand-derived ground truth (incl. the 9105/9106 ambiguous/rejected canaries);
deterministic core (normalization, ZWNJ-aware tokenizer, FieldCharter/ScopeSpec, SQLite index);
calibration sampling; per-hit OccurrenceAssessment with supersession; metrics (Gries DP dispersion
always carrying raw counts, lift with minimum-support refusal, typed co-incidence AᵀA vs raw A_anchor
that provably diverge); ablation retention; append-only EventLog; ResearchRelease + git tag;
CLI with `--json` and explicit-failure discipline; epistemic/loop/invariant test suites; gates 1–5 green.

### Layer 3 — Real corpus (Phase 8, done)
132,538 poems / 234 poets (manifest's 132,591 reconciled as stale top-level metadata; per-category
indices are internally consistent). §45 worked example: Hafez-only rust = 0 hits (the narrated
co-incidence does not occur there under `زنگار` alone); whole corpus mirror×rust = 378 poem-scale /
310 couplet-scale across 84 poets, Saeb Tabrizi dominant (149/378), ablation removing Saeb retains
60.6% / 54.8% — the relation survives. Two real crash bugs + the poet-dates field-name bug (P8.4,
found via the user's own earlier test session) fixed along the way.

### Layer 4 — Usability hardening (Phase 9, Chains A+B done)
- Chain A: studies remember `--corpus-root` (P9.1); content-signal-keyed SQLite cache — cold build
  7,559s paid once, warm census 3.3s (P9.2); all verbs rewired to the cache with fixture numbers
  byte-identical (P9.3); stored field scope is a real filter with unknown-kind refusal (P9.4).
- Chain B: the `walk` guided flow — surface choices, never force (the user's binding design
  instruction); batched per-hit decisions; narrow/split/trace/widen as first-class append-only events;
  scripted `--script` replay reproducing canonical ground truth (P9.5); skill rewritten to script
  the flow, verified fresh-session (P9.6); HEART-scale 41-hit test (P9.7); release renders
  `report.md`+`report.html` by default, renderer adds no epistemic logic (P9.8).

### Layer 5 — The V0.2 execution spec (not started)
`V0_2_HERMES_EXECUTION_SPEC.md`: T01–T13 (v0.1.1 trust repair: stable hit IDs, structured anchors,
per-hit assessment identity, mode completeness, OperationRecords, self-contained releases) →
U01–U12 (v0.1.2: status/next-actions, source return, packaging, CI, Gate G real study) →
V201–V213 (v0.2.0: scope grammar, scale mappings, assessed-rule, estimation, Claim/Relation-Object
guards, regex anchors, Gate H three scholarly releases). Protocol: one row per turn, discriminating
test first, full suite green, one commit per row. Only the user passes Gates G/H.

## 3. The user's test — 20260901_193123_e0b6f7e8 (Telegram, 166 msgs)

**What was asked:** cluster/categorize Rostam's battle strategies in the Shahnameh; then refine to a
multi-label scheme (one episode, many labels, covering set).

**What was produced:**
1. **Dataset** `mozare-wiki\others\research\rostam-strategies\rostam-strategies-dataset.json` —
   17 episodes × 15 labels (RECON, RECRUIT, EXPLOIT_NATURE, FRAME_SWITCH, FEIGN, CONCEAL, TIMING,
   VULNERABILITY, ASYMMETRIC, TERRAIN, RAKHSH, RITUAL, ENDURE, RECLASSIFY, RECEIVED). Label counts:
   ASYMMETRIC 8, VULNERABILITY 5, FRAME_SWITCH 5, TIMING 4, FEIGN 4, RAKHSH 3, TERRAIN 3, RITUAL 3,
   RECON 3, CONCEAL 3, RECEIVED 2, EXPLOIT_NATURE 2, ENDURE 1, RECRUIT 1, RECLASSIFY 1.
   Every `verified` record carries verse quotes located in the vendored corpus (99,220 verses);
   `prose-only` flagged, never upgraded. `verification-results.json` holds per-label corpus hits.
   Signature finding: «ابا او کنون چاره باید نه زور» — hapax in the whole Shahnameh (RECLASSIFY).
2. **Persian dashboard** `rostam-charts\dash\index-fa.html` — RTL, Vazirmatn woff2 embedded,
   pure-HTML Persian signature card (the matplotlib reshaping corruption fixed), HTML bar tables,
   corpus-anchor terms (کمند، جگر، تیر گز، سیمرغ، وارونه) used directly, zero-count rows kept red
   as findings (uniqueness, not error).
3. **An Ontograph study workspace seeded** `ontograph-workspaces/rostam-strategies/` — 13 object
   addresses with Persian anchors (lasso/کمند, pits/چاه, night/بخوابید, dagger/خنجر, tamarisk/تیر گز,
   simorgh/سیمرغ, liver/جگر, exploit-nature/وارونه, rakhsh/رخش, …) — but **no census, no
   assessments, no events persisted there**. It is a prepared-but-unrun study.

**Evaluation of the test against the apparatus:**
- **Governance: mostly correct.** Verse-level verification against the pinned corpus, quarantine
  folder placement, prose-only flags visible, no claims of occurrence-level certainty. The dashboard
  is a display artifact; its numbers are label counts, not censuses, and it says so.
- **Channel: it bypassed Ontograph.** No study, no Anchor Hits, no per-hit assessment; the 15 labels
  were assigned by agent judgment from episode knowledge + spot verification. Under the spec's own
  authority hierarchy these labels are candidate-tier (level 7) material — exactly what the wikis
  say fluency can never upgrade. The work is a genuine scholarly *draft*, produced by the method the
  apparatus exists to replace.
- **Root cause is a real scope signal, not operator error:** Ontograph's object model is
  anchor-form-centric; "label an episode with strategy tags" is a research-made Mapping/Claim task
  (v0.2's V202/V206/V207 territory). The apparatus could not natively express the user's ask yet.
- **The honest bridge already exists:** the seeded 13-object workspace. Running it through the
  corrected flow (census → walk → assessed companions) converts the test's impressions into
  assessed occurrences with denominators — e.g. RECLASSIFY's «چاره باید نه زور» has corpus-wide
  frequency 1 and would enter a census as an assessed anchor, not a chart label.

## 4. The wiki spine (ontography ↔ ontograph ↔ engine)

- **mozare-wiki** (`03-objects/concepts/ontography.md`, `03-objects/projects/ontograph.md`):
  ontography = inscriptive practice staging a crowded field without premature synthesis;
  "ontographic recurrence" is a relation type that never proves causal continuity — the direct
  theory counterpart of the engine's companions/recurrence non-equivalence. The Ontograph
  architecture reservoir's governing formula maps one-to-one onto engine artifacts:
  *Structure holds the relation* (Object Address), *Profile lets it appear* (ProfileRecord),
  *Permission governs its use* (Claim permission, V206), *Event preserves its becoming*
  (append-only events.jsonl), *Residue preserves its failure* (rejected/ambiguous assessments kept).
  Relation-before-type = V207's promotion guards. 46 canonical mozare-wiki objects already cite
  ontograph — the theory spine is pre-wired.
- **OOO-living-wiki**: 302 objects / 273 relations with `claim_permission` (e.g. `may-argue`),
  `verification_status`, `mapping_strength` fields — a working instance of exactly the record
  vocabulary v0.2 formalizes. Harman's withdrawn object supplies the epistemic justification for
  anchor hit ≠ object: no lexical access exhausts the object; OccurrenceAssessment is the record of
  an access condition, not of the thing.
- **Open intake item (from INTAKE-NOTE.md, never executed):** register "Ganjoor Ontograph" as a
  `03-objects/projects/` child of ontograph + a PROJECT_ROUTE_REGISTER row — via /wiki-intake, not
  ad hoc. Left for the user to order.

## 5. Finalization checklist before v0.1.1 work begins

1. **Commit the execution spec** (currently untracked) — `Ontograph: add V0.2 Hermes execution spec`.
2. **P9.9 human review** — Mohammad reviews `hermes\Temp\p99_dry_run\` (release report + run
   artifacts). Mechanically complete per P9.5–P9.8 tests; the report is intentionally thin on real
   corpus (few assessments yet); that is the honest state, not a defect.
3. **Decide the fate of the seeded rostam-strategies workspace** — recommended: make it the Gate G
   real study (mid-sized, already seeded with 13 objects), which would simultaneously satisfy
   U11's "full real-corpus study" and close the loop on the user's test.
4. Optional: /wiki-intake for the Ganjoor Ontograph project record (user-ordered).

## 6. Next steps (binding order per the V0.2 spec)

Start **T01** (schema constants + backward-compatible readers, schema_version 2) under the
light-model protocol: read the row + dependencies, discriminating test first, one row per turn,
`pytest -q` fully green, `git diff --check`, one commit per row. T03's migration preview must be
tested on a **copy** of the rostam workspace, never the live one. Gates A–D close v0.1.1;
only then U-rows; Gate G is the user's own real study; then V-rows to v0.2.0 and Gate H.

Effectiveness target already in sight: the spec requires "at least one conclusion materially
narrowed by the method" (§16). The Rostam test is the natural case — its label-frequency chart,
re-derived as assessed censuses with per-hit decisions and denominators, is precisely the
raw-anchor-vs-method comparison Gate H case 3 asks for.
