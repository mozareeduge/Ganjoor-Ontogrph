# Tasks â€” v02-reality-tracked-update

> The binding one-row protocol is `V0_2_HERMES_EXECUTION_SPEC.md` Â§4: one row per turn, discriminating test observed failing first, focused tests, full suite, `git diff --check`, one commit. These rows do not authorize edits to the historical `IMPLEMENTATION_LEDGER.md`. T/U/V row text remains binding except for the dependency/order overrides explicitly listed below.

## Canonical execution order

Current verified progress as of 2026-09-07:

- Last completed row: U09 (cross-platform CI matrix and static configuration contract).
- First remaining row: U10.
- Latest local verification: U09 static configuration test and YAML mapping validation pass; full suite from ganjoor-ontograph reports 331 passed, 10 skipped, 1 xfailed; git diff --check passes.
- The historical `ganjoor-ontograph/implementation/IMPLEMENTATION_LEDGER.md` is not updated for the OpenSpec W/U continuation. Use git commits plus this task file for post-amendment progress.
- Do not run implementation and independent QA in the same context. Implementation follows one row per turn; QA should be read-only and start from this file, `V0_2_HERMES_EXECUTION_SPEC.md`, and the latest handoff.

```text
T01â€“T13
â†’ U03(base schemas only)
â†’ W01 â†’ W02 â†’ W03 â†’ W04A â†’ W04B â†’ W05 â†’ W06
â†’ U01 â†’ U02
â†’ W07A â†’ W07B â†’ W08
â†’ U04 â†’ U05 â†’ W09A â†’ W09B
â†’ U06â€“U12
â†’ V201 â†’ V202 â†’ V207 â†’ V203 â†’ V204 â†’ V205
â†’ W10A â†’ W10B â†’ W11A â†’ W11B
â†’ V206 â†’ V208 â†’ V209 â†’ V210â€“V213
```

Overrides:

- U03 is narrowed to validated ResearchSituation/Seed schemas and their generic record route. Its conversational onboarding work moves to W02â€“W03.
- U01 must understand inquiry/review state. U06/U07/U11 must use the W flow. U11 is the Rostam ready-made acceptance handoff; it is not duplicated in a W row.
- V207 depends on `U04,V202`, not V206. Until V206 lands, every new Relation-Object is fixed to `claim_permission: preserve only`; any other permission refuses. V206 later adds human-confirmed permission changes and distribution-policy checks.
- V205 precedes W10A because each catalog cell must name compatible OccurrencePolicies.

## Trust and base-record prerequisites

- [x] Execute T01â€“T13 exactly as specified. Do not start W work against poem-keyed assessments, unstable hits, ephemeral operations, or live-workspace release rendering.
- [x] Execute amended U03 after T13: add schema-versioned ResearchSituation and Seed records, validation, append-only persistence, invalid-record tests, and generic `record add/show/list`; do not build `inquire` yet.

## Inquiry rows

### W01 â€” inquiry record schemas and isolated stores

- [x] Test first: an InquiryCatalog and InquiryReview round-trip with schema versions; candidate files are invisible to `_anchors_for`, census loaders, and active object loaders; generic `record add` refuses machine-managed stores.
- [x] Add dataclasses/validators/readers for InquiryCatalog, InquiryReview, and candidate evidence receipts plus append-only JSONL paths and tolerant readers. Do not touch release collection yet.
- [x] Verify focused schema/store tests, full suite, diff check; commit `Ontograph W01: add isolated inquiry records`.

### W02 â€” lossless hunch and proposal parser

- [x] Test first: an English-only hunch preserves verbatim text and yields `needs-vocabulary`; an attributed Persian proposal parses; missing proposer/rationale, unknown kinds, and purported engine-generated contrast candidates fail.
- [x] Add pure functions in `inquiry.py` for display normalization, script/language observations, ResearchSituation field construction, and YAML/JSON proposal validation. No index access or CLI write in this row.
- [x] Verify and commit `Ontograph W02: parse attributed inquiry proposals`.

### W03 â€” `inquire` create CLI and atomic persistence

- [x] Test first: `ontograph inquire <study> --hunch ... [--file ...] --json` writes one ResearchSituation and one candidate InquiryCatalog atomically, emits one JSON object, and changes no field/object/assessment/operation state; invalid input writes nothing.
- [x] Add the create form of `inquire`; emit a review-template path/content and exact next action. Do not add corpus support or review actions yet.
- [x] Verify and commit `Ontograph W03: persist inquiry intake`.

### W04A â€” corpus support and lexical-neighbor computation

- [x] Test first: fixture supplied exact/phrase forms return hand-checked counts and stable examples; zero support remains explicit; English tokens are not queried as Persian motifs; neighbor results pin snapshot/scope/window/filter versions; changed field/snapshot stales the receipt.
- [x] Implement pure cached-index support queries and deterministic lexical-neighbor discovery. Engine output kind is only `lexical-neighbor`; default ordering is declared retrieval order and never relation strength. Do not change the CLI.
- [x] Verify scan/index equivalence for support forms, full suite, diff check; commit `Ontograph W04A: compute candidate support`.

### W04B â€” inquiry refresh CLI

- [x] Test first: `ontograph inquire <study> --refresh <catalog-id> --json` appends one superseding verified catalog; stale/unknown/mixed-situation input writes nothing; stdout is one JSON object.
- [x] Wire only W04A's verifier to refresh and emit the review template/next command. Never rewrite the original catalog.
- [x] Verify and commit `Ontograph W04B: refresh inquiry evidence`.

### W05 â€” atomic human review service

- [x] Test first: accept/reject/defer/revise/split decisions append history; supported acceptance atomically creates Seed/Object Address/LexicalAnchor; review creates no assessment; agent-attributed, stale, duplicate, mixed-situation, and zero-support ordinary acceptance all fail without partial writes.
- [x] Implement the pure review/promotion service through the same object/anchor validators introduced by T02/T03. `accept-unsupported` requires human rationale and preserves unsupported state.
- [x] Verify and commit `Ontograph W05: govern candidate promotion`.

### W06 â€” review CLI and direct-route guard

- [x] Test first: `ontograph inquire <study> --review decisions.json --json` reports promoted/rejected/deferred IDs; direct `object add`, `object anchor add`, and generic record routes cannot bypass review in a governed workspace; legacy compatibility behavior is explicit.
- [x] Add review CLI, atomic staging/write, human actor/confirmation receipt, and equivalent confirmation reference for deliberate direct object routes. Emit the next walk command for each promoted object.
- [x] Verify and commit `Ontograph W06: expose reviewed object promotion`.

## Workflow integration rows

### U01 and U02 prerequisites

- [x] Execute U01 with the amended decision table in the execution-spec amendment: a fresh study suggests inquiry, not object census; candidate/review/staleness states have legal next actions.
- [x] Execute U02 source return. Its poem/hit coordinates are the resolution target for W08 evidence cues.

### W07A â€” operation inquiry schema and selector

- [x] Test first: OperationRecord schema 3 round-trips situation fields; tolerant readers mark old rows `legacy-unframed`; a pure selector inherits one active situation, refuses zero, and refuses multiple without explicit ID before calling a computation spy.
- [x] Add only the schema/tolerant reader and pure situation-selection/preflight service. Do not wire verbs or status yet.
- [x] Verify and commit `Ontograph W07A: define governed operation context`.

### W07B â€” governed command and evidence wiring

- [x] Test first: Field construction and every analytical command use the shared preflight; legacy-unframed operations cannot support higher records/release; status shows the full chain and orphan/stale records; every refusal occurs before computation/write.
- [x] Wire W07A into governed commands, higher-record eligibility validation, and status. Never retro-link an old record.
- [x] Verify all command spies and commit `Ontograph W07B: bind operations to inquiry`.

### W08 â€” walk evidence tray and candidate encounter

- [x] Test first: every displayed cue is actually present in the fixture verse/couplet and resolves through `source show`; cues never change `a/r/u`; `c:<candidate-id>` writes only a proposal event; stale hit/catalog scripts fail atomically; canonical stable-ID 5/1/1 replay is unchanged.
- [x] Add situation selection, reviewed-candidate/lexical cue tray, identity-based candidate encounter action, and four-way completion summary to the T07/T08 walk state machine. `done` remains a stop, not an aggregation or completeness override.
- [x] Verify all Gate C actions plus cue tests; commit `Ontograph W08: add inquiry evidence to walk`.

### U04, U05, then W09A/W09B

- [x] Execute U04 and U05 after W08 so CRUD/result-card validators can cover inquiry provenance and forbid ungoverned supporting records.

### W09A â€” inquiry release collection and verification

- [x] Test first: a release contains ResearchSituations, Seeds, InquiryCatalogs, InquiryReviews, and candidate encounter events; empty types are explicit; copied verify succeeds and reference/hash tampering fails.
- [x] Extend only the release collector/layout and standalone verifier. Do not change Markdown/HTML rendering.
- [x] Verify Gate D fixtures and commit `Ontograph W09A: collect inquiry history`.

### W09B â€” inquiry status cards and reports

- [x] Test first: status and staged-only Markdown/HTML show review state, unsupported/stale entries, assessment coverage, and provenance links exactly as stored; renderer-computation spies remain untouched.
- [x] Add status cards and report sections from W09A staged records only. No descriptive co-incidence grid is added.
- [x] Verify Gate E fixture and commit `Ontograph W09B: render inquiry history`.

## Finish v0.1.2 and Gate G

Resume implementation here. Each U row is one implementation turn and one commit.

- [x] **U06 â€” researcher skill:** update the skill, references, templates, and settings for the governed inquire-first route. Verify with a fresh-session scripted fixture replay; the agent prepares files/runs commands and the researcher supplies semantic review and occurrence decisions. Verified: `tests/test_u06_researcher_skill.py -q` -> 4 passed; full suite -> 328 passed, 10 skipped, 1 xfailed.
- [x] **U07 — documentation:** rewrite README/runbook, migration guide, and changelog so the quickstart is verbatim `study new → inquire → field/refresh → review → walk → assessed-full operation → source return → Finding → release`. Verified: focused U07 test -> 1 passed; full suite -> 329 passed, 10 skipped, 1 xfailed; `git diff --check` passes.
- [x] **U08 â€” packaging:** complete package metadata and dev dependency group; build wheel and sdist, then run a clean-wheel smoke test.
- [x] **U09 - CI:** add Windows/Ubuntu x Python 3.10/3.12 coverage. Verified: static configuration test failed first then passed; YAML mapping check; wheel smoke/reconstruction/U09 focused run -> 3 passed; full suite -> 331 passed, 10 skipped, 1 xfailed; remote matrix awaits GitHub execution.
- [ ] **U10 â€” pinned fast path:** implement the clean-git corpus cache key from commit SHA + manifest hash + cache schema; use a full signal or explicit refusal for dirty/non-git corpora. Verify the unchanged warm command target of â‰¤2s, or record a user-approved measured exception.
- [ ] **U11 â€” Gate G candidate:** execute the ready-made flow on a copy/continuation-safe Rostam workspace. Handoff must include the verbatim hunch, candidate and unsupported lists, human review receipt, governed objects with real support, at least one fully driven walk, ambiguity/incompleteness, source tray, Finding eligibility, self-contained report, timings, and comparison with the original 15-label draft. Only Mohammad may pass Gate G.
- [ ] **U12 â€” v0.1.2 release:** execute only after explicit Gate G approval; re-run Gates Aâ€“G and verify version/tag consistency.

## v0.2 relation/mapping-first rows

- [ ] Execute V201, then V202.
- [ ] Execute amended V207 next. Test co-incidence cannot auto-promote; required Trace/Mapping/candidate descriptions/counter-evidence/use status/history must be supplied; permission is hard-fixed to `preserve only` until V206.
- [ ] Execute V203, V204, then V205. Estimated pair relations remain blocked.

### W10A â€” DescriptiveCatalog pure computation

- [ ] Test first: hand-derived fixture matrix has correct eligible denominators, marginals, shared numerators, ambiguity-only counts/shares, coverage, scales, policy IDs, and source IDs; incomplete/stale pairs are refusal cells; zero/below-minimum support retains raw support but refuses association language; no relation records change.
- [ ] Implement pure deterministic catalog construction over V202 Mapping Objects and V205 policies with stable object-ID ordering. Do not add workspace writes, CLI, source export, or rendering.
- [ ] Verify and commit `Ontograph W10A: compute assessed descriptive catalogs`.

### W10B â€” immutable catalog persistence

- [ ] Test first: the public catalog service appends OperationRecord, Mapping Object, DescriptiveCatalog, and source manifest atomically before return; concurrent/partial writes fail cleanly; no relation records change.
- [ ] Wrap W10A in the T09 append discipline. Do not add CLI or rendering.
- [ ] Verify and commit `Ontograph W10B: persist descriptive catalogs`.

### W11A â€” catalog CLI and source return

- [ ] Test first: `ontograph catalog <study> --mode assessed-full --scale ... --json` persists before stdout; anchor/estimated/partial input refuses without writes; source show/export resolves each computed cell.
- [ ] Add only the CLI over W10B and source-return integration.
- [ ] Verify and commit `Ontograph W11A: expose descriptive catalogs`.

### W11B â€” catalog render, collect, and standalone verify

- [ ] Test first: Markdown/HTML/JSON match stored W10B values; renderer-computation spies remain untouched; copied release verifies; cell/source tampering fails.
- [ ] Add renderer and collector/verify integration. Every displayed link uses `co-incidence`; Relation-Object actions route through V207.
- [ ] Verify Gate D/E plus catalog fixture; commit `Ontograph W11B: render governed descriptive catalogs`.

## Resume remaining v0.2 rows and Gate H

- [ ] Execute V206 after W11B. It may add `argue cautiously`/`argue` only with explicit human confirmation and valid V205 policy links; it must revalidate existing preserve-only Relation-Objects without rewriting them.
- [ ] Execute V208, V209, V210, V211, V212, V213 in order.
- [ ] Gate H includes a ready-made Rostam release comparing the original 15-label/raw-anchor draft with governed inquiry/catalog/walk results. The report states exactly which labels remained proposals, which objects were supported, what assessment coverage/ambiguity allowed, and how scale/ablation/policies changed the conclusion. Only Mohammad passes Gate H and authorizes the final tag.