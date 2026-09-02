# Ganjoor Ontograph — Hermes execution specification through v0.2.0

**Status:** binding forward implementation plan  
**Targets:** v0.1.1, v0.1.2, v0.2.0  
**Methodological authority:** `../Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md`  
**Historical record:** `IMPLEMENTATION_LEDGER.md` remains authoritative for completed work  
**Executor:** Hermes with a light model, one work unit per turn  
**Baseline:** branch `ontograph/v0.1-build`, commit `f19717ddf`; 155 passed, 10 skipped, 1 xfailed

---

## 1. Purpose and final outcome

This document converts the post-v0.1 evaluation into a dependency-ordered implementation program. It is intentionally prescriptive so a light model never has to invent schemas, command behavior, migrations, gates, or task order.

At the end of v0.2.0, a researcher must be able to:

1. create a declared study over a pinned Ganjoor corpus;
2. register token and phrase anchors without silent matcher failure;
3. inspect contextualized Anchor Hits and assess each hit individually;
4. choose lexical, assessed-full, assessed-rule, or estimated incidence without mode collapse;
5. run recurrence, companions, scale, comparison, and ablation operations that persist their provenance and source returns;
6. create Findings, Claims, Relation-Objects, and research-made mediation only through permitted evidence routes;
7. generate a self-contained Research Release reproducible without its live workspace; and
8. complete the normal flow through Hermes/Claude Code without knowing internal vocabulary in advance.

Passing tests is necessary but insufficient. Gates G and H require the user’s human review.

---

## 2. Authority and conflict rules

Use this order:

1. explicit user instruction in the current session;
2. methodological invariants in project spec v2.3.0;
3. this execution spec for v0.1.1–v0.2.0 engineering decisions;
4. `USER_JOURNEY.md` as the target experience;
5. historical build plan/ledger;
6. current implementation when higher sources are silent.

If higher-ranked sources conflict, stop the work unit, record the exact conflict, and ask the user. Never silently choose.

This plan corrects, prospectively and without rewriting history:

- README language that still calls the engine a scaffold;
- stale skill guidance about test count and repeated `--corpus-root`;
- the claim that current reports contain analytical numbers;
- the claim that all advertised walk actions work;
- the poem-level implementation of what the spec defines as per-hit assessment.

---

## 3. Non-negotiable invariants

### Epistemic

- Anchor Hit is not object occurrence.
- Phrase match is not interpretation.
- Co-incidence is not a Relation-Object.
- Partial assessment is not assessed-full.
- Estimate is not census.
- Agent proposal is not evidence.
- Ambiguity remains visible in counts and denominators.
- A renderer never computes research results.
- A result without source return cannot support a scholarly claim.
- A release never depends on mutable live-workspace state.

### Engineering

- Ganjoor JSON is read-only.
- Derived indexes are rebuildable, never source truth.
- Events and research history are append-only; corrections supersede.
- Every result records corpus commit/hash, scope, mode, matcher, normalization, tokenizer, operation version, parameters, limitations, and source manifest.
- Unsupported input fails before computation. Silent zero for an unsupported matcher is forbidden.
- JSON stdout is one well-formed object; diagnostics go to stderr.
- Every schema has `schema_version` and a migration path.
- Tests must discriminate correct behavior from the forbidden shortcut.

### Repository safety

- Preserve untracked `.hermes/` and `ontograph-workspaces/`.
- Never modify `poets/`, `index/`, or `manifest.json`.
- Never commit workspaces, caches, virtualenvs, or SQLite indexes.
- Migrations are atomic and non-destructive.
- A release tag is created only after all artifacts exist and verify.

---

## 4. Hermes light-model execution protocol

Hermes executes exactly one row from Section 13 per turn.

### Start

1. Read this entire document.
2. Read the chosen row and its dependencies.
3. Read only the listed/relevant source and test files.
4. Run `git status --short`; preserve unrelated state.
5. Add the discriminating test first and observe failure.

### Implement

- Change only the chosen row’s scope.
- Do not start dependent rows.
- Prefer explicit dataclasses and pure functions.
- Do not add dependencies unless the row permits one.
- Preserve compatibility until the migration row changes it.
- If an unrelated defect appears, record it; do not expand the row.

### Verify

1. Run focused tests.
2. Run:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```
3. Run `git diff --check`.
4. Mark the row `done` only after all checks pass.
5. Add commands/results to Notes.
6. Commit one row per commit: `Ontograph <ID>: <imperative summary>`.

Statuses: `todo`, `doing`, `blocked`, `done`. Only one row may be `doing`. Hermes never marks a human gate done.

---

## 5. Version objectives

### v0.1.1 — Trust repair

Eliminate false-negative phrase behavior, false assessment identity, incomplete guided review, ephemeral operation results, and non-reproducible releases. No new interpretive feature.

Release condition: Gates A–D.

### v0.1.2 — Researcher-effective workflow

Add status/next actions, source return, onboarding records, complete docs/skill, package/CI, performance, and one human-reviewed real-corpus release.

Release condition: Gates A–G.

### v0.2.0 — Complete declared apparatus

Add composable scopes, scale mappings, assessed-rule, estimation, formal policies/claims/relation objects, regex anchors, and research-made mediation without weakening earlier trust gates.

Release condition: Gates A–H.

---

## 6. Binding data-model decisions

### 6.1 Study workspace

New `study.yml`:

```yaml
schema_version: 2
study_id: rostam-strategies
display_name: "Rostam strategies"
corpus_root: "C:/.../Ganjoor-Ontogrph"
created_at: "<UTC ISO-8601>"
```

Workspace schema versions are positive integers independent of product semver.
Version 2 is the canonical schema introduced by T01. New IDs match
`^[a-z0-9][a-z0-9._-]{0,63}$`. IDs are not paths; `--workspaces-dir`
chooses the parent. Legacy path-shaped IDs remain readable. Migration preserves
`legacy_study_id` and requires explicit `--new-id` before directory rename.

A `CorpusSnapshot` records commit SHA when available, manifest SHA-256, the
cache content-signal SHA-256, poem count, and dirty/clean status. Its ID is
`cs1-` plus the first 24 lowercase hexadecimal characters of SHA-256 over the
UTF-8 sequence `commit-or-none + NUL + manifest-sha256 + NUL +
content-signal-sha256`. Absolute corpus paths are metadata, not identity, so a
portable clean copy of the same snapshot receives the same ID.

### 6.2 Structured LexicalAnchor

An Object Address keeps the researcher-chosen ASCII-safe `id`,
`preferred_label`, `schema_version`, `version`, active/historical anchor
IDs, status, creation time, and optional `supersedes`. The Object Address ID
is stable across label changes; duplicate IDs are forbidden.

```json
{
  "id": "la1-<stable suffix>",
  "form": "تیر گز",
  "normalized_form": "تیر گز",
  "match_mode": "phrase",
  "status": "approved",
  "version": 1,
  "supersedes": null,
  "created_at": "<UTC ISO-8601>"
}
```

Modes through v0.2:

- `exact`: one normalized token;
- `phrase`: contiguous normalized tokens inside one verse;
- `regex`: v0.2 explicit opt-in only, bounded and versioned;
- `normalized`: legacy alias emitted canonically as `exact`;
- `auto`: CLI-only inference—one token exact, multiple tokens phrase.

Phrase matching never crosses verses. Span runs from first token start to last token end. Overlaps remain separate hits.

“Narrow” creates a replacement version and marks the old anchor `superseded`. It does not leave the broad anchor active. Adding another active anchor is explicitly “broaden/add anchor.”

The anchor ID is `la1-` plus the first 24 lowercase hexadecimal characters of
SHA-256 over `object-address-id + NUL + normalized-form + NUL + match-mode +
NUL + decimal-version`. Timestamps do not participate. Record IDs that
represent historical actions rather than corpus identity—assessments,
operations, events, Findings, and similar records—use their type prefix plus a
standard-library UUID4 lowercase hexadecimal value. No new ID library is
required.

### 6.3 Stable AnchorHit

Required fields:

```yaml
id:
object_address_id:
lexical_anchor_id:
poem_id:
verse_order:
couplet_index:
position:
original_text:
normalized_text:
match_span: [start, end]
matcher_version:
normalization_profile:
tokenizer_version:
corpus_snapshot_id:
```

ID:

```text
"ah1-" + first 24 lowercase hex chars of SHA-256(
  corpus_snapshot_id + NUL + object_address_id + NUL + lexical_anchor_id + NUL +
  poem_id + NUL + verse_order + NUL + start + NUL + end + NUL + matcher_version
)
```

Use UTF-8 string/decimal serialization. `verse_order` is source `VOrder` or deterministic enumeration. Corpus or matcher changes intentionally change IDs.

### 6.4 Per-hit OccurrenceAssessment

```yaml
id:
anchor_hit_id:
object_address_id:
decision: accepted|rejected|ambiguous
rationale:
assessor_type: human|agent|rule
assessor_id:
assessment_policy_version:
created_at:
supersedes:
```

Ledger is append-only. Active decision is latest valid row per `(object_address_id, anchor_hit_id)`; reassessment names its predecessor.

Poem state is derived:

- `present`: at least one accepted hit;
- `ambiguous-only`: none accepted, at least one ambiguous, none unassessed;
- `absent-after-review`: all eligible hits assessed and rejected;
- `incomplete`: no accepted hit and at least one eligible hit unassessed.

### 6.5 Mode completeness

- `anchor`: lexical incidence only.
- `assessed-full`: all eligible hits in scope have active assessments.
- `assessed-rule`: versioned rule plus valid compatible validation receipt.
- `estimated`: recorded sampling frame, strata, seed, estimator, uncertainty, assessed sample.

`--mode assessed` remains an alias for `assessed-full` through v0.2 and warns on stderr. It never means partial review. Incomplete assessed-full fails with coverage counts and legal alternatives.

### 6.6 OperationRecord

Every analytical command persists before returning:

```yaml
id:
schema_version:
study_id:
operation_type:
operation_version:
created_at:
field_charter_version:
scope_spec:
object_address_ids: []
occurrence_policy_ids: []
parameters: {}
result: {}
source_manifest: []
corpus_snapshot:
software_environment:
limitations: []
```

Stdout includes `operation_record_id`. Repetition appends a new immutable record. Source entries contain poem ID, repository-relative path, hit IDs, and verse/couplet coordinates.

### 6.7 Self-contained release

Required layout:

```text
releases/vX.Y.Z/
  release.json
  manifest.sha256
  report.md
  report.html
  records/
    object-addresses.jsonl
    lexical-anchors.jsonl
    occurrence-assessments.jsonl
    occurrence-policies.jsonl
    operations.jsonl
    profiles.jsonl
    mappings.jsonl
    traces.jsonl
    experiments.jsonl
    findings.jsonl
    relation-objects.jsonl
    claims.jsonl
    reductions.jsonl
    events.jsonl
  field/charter.yml
  field/scope.json
  provenance/corpus-snapshot.json
  provenance/software-environment.json
```

Rules:

- Release references only internal relative paths and SHA-256 values.
- Reports read only staged release content—no workspace fallback.
- Empty types get explicit empty files/sections.
- Stage in a temporary sibling directory; validate; render; hash; verify; atomically rename; git-add/commit; tag last.
- `manifest.sha256` lists every release file except itself.
- Existing directory or tag causes clean refusal.

---

## 7. Binding CLI contracts

All support `--json`.

### Study

```text
ontograph study new <id> --display-name <text> --corpus-root <path>
ontograph study status <id>
ontograph workspace migrate <path> [--new-id <valid-id>] [--apply]
```

Status reports schema/corpus pin, field, objects/anchors, hit and assessment coverage, ambiguity/incompleteness, operations/records, latest release, and methodologically legal `next_actions`.

### Objects/anchors

```text
ontograph object add <study> --address <id> --label <text>
  --anchor <form> [--anchor-mode auto|exact|phrase]

ontograph object anchor add <study> --object <id>
  --form <text> --mode auto|exact|phrase|regex

ontograph object anchor revise <study> --object <id>
  --anchor-id <id> --form <replacement> --mode <mode> --reason <text>
```

Duplicate object IDs fail. Identical active anchors are idempotent. Invalid form/mode fails before write.

### Guided walk

```text
ontograph walk <study> --object <id> [--sample 30] [--seed 0]
  [--resume] [--script responses.json] [--assessor-id <id>]
```

Every hit displays hit ID, progress/coverage, poet/title/poem/category/source, highlighted verse, couplet, neighboring couplets, and actions.

Actions:

- `a/r/u`: per-hit decision;
- `n`: replacement anchor, reason, preview re-census, then confirmation;
- `s`: create second object and split event; hit stays undecided;
- `t`: create Trace with source return;
- `w`: enlarge deterministically and keep prompting;
- `x`: stop and write completed decisions;
- `?1..?4`: match, couplet, neighboring context, full poem;
- Enter: undecided;
- `done`: finish with coverage and legal next modes.

Scripted format is identity-based:

```json
{
  "schema_version": "1.0",
  "object_address_id": "mirror",
  "corpus_snapshot_id": "...",
  "responses": [
    {"anchor_hit_id": "ah1-...", "action": "accepted", "rationale": "literal surface"}
  ]
}
```

Unknown/stale hit IDs fail. Array order is not identity.

### Source return

```text
ontograph source show <study> --poem-id <id>
ontograph source show <study> --operation <operation-id>
ontograph source export <study> --operation <operation-id> --output <dir>
```

Show is read-only. Export makes UTF-8 Markdown+JSON source tray from the stored manifest and never rewrites corpus data.

### Analytical commands

```text
ontograph census <study> --object <id> --mode anchor|assessed-full|assessed-rule|estimated
ontograph map recurrence <study> --object <id> --unit poem|couplet|verse --mode <mode>
ontograph companions <study> --object <a> --with <b> --scale poem|couplet|verse|window --mode <mode>
ontograph compare <study> --object <id> --field <scope> --field <scope> --mode <mode>
ontograph ablate <study> --remove <scope> --rerun <operation-or-relation-id> --mode <mode>
```

Every call writes an OperationRecord. Pairwise assessed operations require valid policies for all participants.

### Research records

```text
ontograph record add <study> --type <type> --file <yaml-or-json>
ontograph record show <study> --id <id>
ontograph record list <study> [--type <type>]
```

Types: ResearchSituation, Seed, Profile, Mapping, Trace, Experiment, Finding, Relation-Object, Claim, Reduction. All routes validate schemas.

### Release

```text
ontograph release <study> --version X.Y.Z
ontograph release verify <release-directory>
```

Verify runs without workspace access and checks hashes, files, schemas, corpus pin, internal IDs, mode/coverage labels, reports, and stored operation reconstruction.

---

## 8. Shared scope grammar through v0.2

```text
all
none
poet:<slug>
category:<numeric-id>
path:<ganjoor-relative-category-path>
union(<scope>,<scope>)
intersect(<scope>,<scope>)
difference(<scope>,<scope>)
```

One parser/evaluator serves every command. Categories resolve by ID/path, never guessed title. Unknown references fail. Stored Field Charter scope always intersects operation-local scope. Derived chronological scopes preserve proxy rule and date uncertainty; they are never poem dates.

---

## 9. Rule and estimate contracts

### Assessed-rule package

Required: ID/version, object, implementation, compatible corpus/scope/anchors/tokenizer, calibration scope, decision space, validation hit/assessment IDs, agreement/precision/recall/ambiguity metrics, thresholds, limits, actor, timestamp.

The fixture figurative stoplist is never a default real-corpus rule. A receipt invalidates when corpus, anchor, tokenizer, rule, or relevant scope changes. Rule decisions become assessments with `assessor_type: rule`.

### Estimated incidence

Use current provisional default: stratified proportion, Wilson interval, finite-population correction above 10% sample fraction.

Persist population, frame, strata, seed, sampled hit IDs, active assessments, decision counts, point/interval, FPC, incomplete/non-response handling, and limitations. Always label `estimated`.

Positional IDs without recorded sampling design are invalid. Pairwise estimated relation matrices remain blocked through v0.2 absent an explicit methodological amendment.

---

## 10. Claim, relation, and mediation guards

### Claim

ClaimRecord includes text, scope, supporting records, evidence routes, counter-evidence, permission, uncertainty, actor, history.

- `argue` and `argue cautiously` require explicit human confirmation.
- Agent-created claims begin `preserve only`.
- Distribution claims name occurrence mode/policy.
- Raw companions cannot authorize relation language.

### Relation-Object

Promotion requires a human-retained Trace, a Mapping Object, candidate descriptions (plural or explicit reason), counter-evidence field, use status, claim permission, and history. Missing prerequisites produce a refusal, never auto-filled evidence.

### Research-made mediation

Only after Relation-Objects exist. Keep separate corpus recurrence, research events, actors, release persistence, and formula. High attention is not high recurrence. Fixture must make their rankings diverge.

---

## 11. Documentation, skill, packaging, CI

### README/runbook

Include purpose/non-purpose, install on Windows/Linux/macOS, five-minute fixture quickstart, modes, supported anchors/scopes, release example, relation to sibling retrieval project, current status and limitations.

### Researcher skill

It must call status before proposing next work, reuse corpus root, default to corrected walk, use stable hit IDs, use source show, refuse partial-as-full, persist consequential records, verify releases, and avoid hard-coded test counts. Narrowly allowlist new non-destructive commands including walk/status/source/record/migrate/release verify; never deletion/forced merge.

### Packaging

Add README, license, URLs, classifiers, optional dev group (pytest plus chosen linter). Build wheel/sdist and smoke-test installed `ontograph --help`.

### CI

Separate Ontograph workflow on PR/push: Windows+Ubuntu, Python 3.10+3.12, install/wheel smoke, full fixture suite, lint/format, standalone release reconstruction. No real-corpus download, LLM, or network dependency.

---

## 12. Verification gates

### Gate A — Matching

Token-boundary canary; phrase positive; split-across-verses negative; overlaps; scan/index equivalence; real `چاره باید` non-zero; unsupported mode fails.

### Gate B — Assessment

Different decisions for two hits in one poem; supersession per hit; exact mixed-poem aggregation; assessed-full refusal below 100% coverage.

### Gate C — Walk

Captured context display; positive/failure tests for every action; widen prompts new hits; narrow alters active population; split creates object/event; stable-ID replay and stale-script refusal.

### Gate D — Release

Fixture `5/27` appears in OperationRecord, release references, Markdown and HTML. Tag contains all artifacts. Copied release verifies without workspace. Tampering fails.

### Gate E — Workflow

Fresh fixture: study → field → object → walk → assessed operation → source return → Finding → release. Status suggests only legal actions. Result card has sentence, denominator, source, choices, optional construction detail.

### Gate F — Distribution

CI matrix green; wheel works cleanly; README quickstart succeeds verbatim.

### Gate G — v0.1.2 human gate

One mid-sized real-corpus study through corrected flow. User reviews phrase recall, walk, sources, Finding, report, reproducibility. Only user passes.

### Gate H — v0.2 scholarly gate

Three releases:

1. assessed-full;
2. estimated or assessed-rule with uncertainty/limits;
3. Relation-Object plus mediation where recurrence and attention diverge.

One case compares Ontograph with naive raw-anchor analysis and documents how calibration, scale, ablation, ambiguity, or estimation changed the conclusion. Only user passes.

---

## 13. Atomic implementation ledger

### v0.1.1 — Trust repair

| ID | Work unit | Depends | Verification | Status |
|---|---|---|---|---|
| T01 | Schema constants and backward-compatible readers | — | old fixture/current copied workspace loads | todo |
| T02 | Structured anchors; auto/exact/phrase in scan+SQLite | T01 | Gate A fixture, scan/index equivalence | todo |
| T03 | Non-destructive migration; ID/duplicate validation | T01–T02 | copied rostam workspace migrates; original unchanged | todo |
| T04 | Verse order, corpus snapshot, stable hit IDs | T01 | warm/cold deterministic identity | todo |
| T05 | Per-hit assessments and supersession | T04 | Gate B mixed-hit fixture | todo |
| T06 | Mode names and completeness enforcement | T05 | partial-full refusal; alias warning | todo |
| T07 | Walk state machine, context rendering, stable scripts | T04–T06 | context and stale-script tests | todo |
| T08 | Fix narrow/split/trace/widen/context/stop/resume | T07 | all Gate C actions | todo |
| T09 | OperationRecord and automatic persistence/source manifests | T06 | append, provenance, stdout ID | todo |
| T10 | Release collector and self-contained layout | T03,T05,T09 | required files/references | todo |
| T11 | Reports solely from release; actual values/limits/sources | T10 | 5/27 in JSON+MD+HTML | todo |
| T12 | Atomic release; standalone verify; commit/tag last | T10–T11 | Gate D clean-copy/tamper tests | todo |
| T13 | Version/changelog v0.1.1; close Gates A–D | T01–T12 | full suite + diff check | todo |

Implementation locks:

- T02 phrase uses ordered token n-grams within verse. Test normalization, ZWNJ, overlaps, repeated tokens, boundaries. Whitespace+explicit exact fails.
- T03 previews counts/inferred modes/orphans before `--apply`; atomic files; migration event+hashes; never touch live user workspace in tests.
- T04–T06 remove poem-keyed compatibility calculation. Coverage is active assessed hits / eligible hits.
- T07–T08 separate state machine from terminal I/O. Resume selects active unassessed hits on same snapshot. Anchor revision preserves now-stale decisions as history but excludes them from new population.
- T09 writes after successful computation/source construction; concurrent JSONL writers fail instead of interleaving.
- T10–T12 collect → render → hash/verify → atomic rename → commit → tag. `release verify` must not import live workspace readers.

### v0.1.2 — Researcher-effective workflow

| ID | Work unit | Depends | Verification | Status |
|---|---|---|---|---|
| U01 | `study status` and legal next actions | T13 | state decision table | todo |
| U02 | `source show/export` from manifests | T09 | exact contextual passages; corpus unchanged | todo |
| U03 | ResearchSituation+Seed records and onboarding route | T01 | vague opening produces records | todo |
| U04 | Validated CRUD for all declared research records | T01,T09 | round-trip+invalid schemas | todo |
| U05 | Result cards/Findings linked to operations/sources | U01–U04 | Gate E fixture | todo |
| U06 | Update skill/references/templates/settings | U01–U05 | fresh-session scripted replay | todo |
| U07 | Rewrite README/runbook; migration guide/changelog | U06 | quickstart verbatim | todo |
| U08 | Package metadata/dev group/wheel/sdist | T13 | clean wheel smoke | todo |
| U09 | Windows/Ubuntu Python 3.10/3.12 CI | U08 | Gate F | todo |
| U10 | Pinned clean-corpus fast cache path | T13 | unchanged warm command target ≤2s, or user-approved measured exception | todo |
| U11 | Full real-corpus study, hand artifact to user | U01–U10 | Gate G | todo |
| U12 | Release v0.1.2 | U11 | Gates A–G; version/tag consistency | todo |

Status decision table:

| State | Required suggestion | Forbidden |
|---|---|---|
| no field | declare/build field | assessed census |
| field/no object | register object/anchor | companions |
| object/no hits | revise anchors or preserve lexical negative | claim object absence |
| hits/incomplete | walk, rule, or estimate | assessed-full |
| full review | assessed operation/source return | forced Relation-Object |
| operation/no Finding | inspect/retain Finding or Trace | automatic argument |
| releaseable | release/continue/reopen | finality claim |

U10 fast path:

- clean git corpus: commit SHA + manifest hash + cache schema;
- dirty git corpus: full signal or explicit refusal;
- non-git corpus: full signal;
- never mtime-only.

### v0.2.0 — Complete apparatus

| ID | Work unit | Depends | Verification | Status |
|---|---|---|---|---|
| V201 | Shared scope grammar/category/path/combinators | U12 | round-trip + real category spot check | todo |
| V202 | Verse/couplet/window recurrence and Mapping Objects | T09,U04 | scale-divergence fixture | todo |
| V203 | General validated assessed-rule mode | T05–T06 | pass/fail receipts | todo |
| V204 | End-to-end stratified estimate | T05–T06 | non-100% known target | todo |
| V205 | OccurrencePolicy records for every object operation | V203–V204 | no unlinked object result | todo |
| V206 | Claim permissions/human confirmation | U04,V205 | forbidden agent argument | todo |
| V207 | Relation-Object prerequisites/history | U04,V202,V206 | co-incidence cannot auto-promote | todo |
| V208 | Research-made mediation | V207 | recurrence/attention divergence | todo |
| V209 | Bounded regex anchors/provenance | T02 | safety+positive tests | todo |
| V210 | Release/report all v0.2 records and policies | V201–V209 | standalone verification | todo |
| V211 | Skill/docs/templates for v0.2 choices | V210 | conversational scenarios | todo |
| V212 | Three scholarly cases; hand releases to user | V211 | Gate H | todo |
| V213 | Release v0.2.0 | V212 | Gates A–H; CI/package/tag | todo |

Implementation locks:

- V201 uses one parser/evaluator. Difference denominator is resolved remainder. Field scope intersects local scope.
- V202 keeps poem/couplet/verse/window typed; Comment verses never receive fabricated couplets; window records tokenizer+N.
- V203–V205 invalidate receipts on corpus/anchor/tokenizer/rule/scope changes. No fixture rule as real default. Estimated pair relations blocked.
- V206–V208 preserve human actors, initiating traces, counter-evidence, and attention/recurrence separation.
- V209 never infers regex. Reject empty/empty-matching patterns; record flags+engine; bounded execution. Add the smallest safe dependency only if standard library cannot bound execution.

---

## 14. Required discriminating fixtures

Add ground truth first for:

1. two hits in one poem with different decisions;
2. contiguous Persian phrase;
3. same tokens split across verses (no match);
4. overlapping phrase matches;
5. category scopes that diverge;
6. partial assessment causing full-mode failure;
7. non-100% stratified sample with hand-computed estimate/interval;
8. nearly identical valid/invalid rule receipts;
9. recurrence rank opposite attention rank;
10. release with actual operation values and tampered-copy failure.

Each fixture note explains how a forbidden shortcut would yield a different answer.

---

## 15. Migration and compatibility

1. Detect legacy by missing `schema_version`, never filename.
2. Preview counts, inferred modes, invalid IDs, duplicate objects, orphan assessments, and writes.
3. Require explicit `--apply`.
4. Infer exact for one token, phrase for whitespace; flag empty/regex-like forms.
5. Never fan poem-level legacy decisions across multiple hits. Store as `legacy-poem-decision` and require re-review.
6. Preserve legacy path IDs; request valid new ID for rename.
7. Append receipt with before/after hashes.
8. Old releases remain readable but verify reports their limitations.
9. `--mode assessed` and old `object add --anchor` remain through v0.2.
10. Alias removal is out of scope before v0.3.

---

## 16. Effectiveness measures

Record for Gates G/H:

- time to first contextualized hit;
- time for 30-hit review;
- executable-anchor percentage;
- phrase recall spot check;
- coverage/ambiguity;
- warm latency;
- commands to release;
- clean-copy verification;
- descriptive inter-assessor agreement;
- whether Ontograph narrowed/changed raw-anchor conclusion.

Targets:

- zero silently unsupported anchors;
- 100% source manifests for persisted analytical results;
- 100% release hash verification;
- 30-hit session completable without leaving walk;
- no exact object incidence below 100% eligible-hit coverage;
- at least one conclusion materially narrowed by the method.

---

## 17. Non-goals through v0.2

Do not add without user amendment:

- graph database or browser workbench;
- spectral/community detection;
- universal Persian lemmatizer;
- corpus-wide LLM labeling;
- automatic symbolic interpretation;
- multi-user server/merge protocol;
- cloud deployment;
- pairwise estimated relation matrices;
- destructive workspace cleanup.

Correct the terminal/conversational workflow before hiding it behind another interface.

---

## 18. Completion rule

Hermes may call v0.2 technically ready only when all T/U/V rows are done, Gates A–F pass, and candidate artifacts for G/H exist. Only the user may approve Gates G/H and authorize final tags.

If a session ends early, stop after the last verified work unit. Durable state is this ledger, commits, and test evidence. Never compress unverified rows into a claim of completion.

---

## 19. Amendment 2026-09-02 — reality-tracked inquiry and catalog flow

**Status:** binding prospective amendment  
**Evidence:** researcher test 20260901_193123 (“cluster Rostam's battle strategies”)  
**Row checklist:** openspec/changes/v02-reality-tracked-update/tasks.md

This section appends to, and does not rewrite, the plan above. Every §3 invariant remains intact. Explicit dependency, CLI, release-layout, gate, and future-row changes below control under §2.

### 19.1 Finding and ruling

The Rostam session produced useful candidate-tier material—17 episodes, 15 agent-authored labels, source spot checks, and a dashboard—but no ResearchSituation, governed candidate review, stable per-hit assessment, complete census, OperationRecord, Mapping Object, or source-returnable release. The guards never fired because the flow never entered the apparatus.

The runtime SHALL NOT pretend to translate an English hunch into Persian motifs or infer strategies from token co-occurrence. The governed chain is:

    verbatim hunch and attributed proposals
    → corpus verification and raw lexical-neighbor proposals
    → explicit human candidate review
    → provisional Object Address and approved retrieval anchor
    → stable Anchor Hits and per-hit walk
    → complete assessed operation
    → descriptive co-incidence catalog and source return

Agent authorship remains visible; review approval is not OccurrenceAssessment; lexical neighbor is not object; co-incidence is not Relation-Object.

### 19.2 Governed entry and bypass closure

For a new schema-version-2 workspace, a minimal active ResearchSituation is required before Field construction, active object/anchor promotion, walk, or analytical computation. Inquire accepts a vague hunch without judging it. Study new/status, inquire, migration, record show/list, read-only source show, and standalone release verify remain legal beforehand.

Situation selection is deterministic: inherit one active situation; with none, refuse and offer inquire; with several, require --situation; never select the newest. Validate selection before computation or write.

Legacy unframed operations remain readable and immutable as legacy-unframed with limitations. They cannot support a Finding, Claim, Relation-Object, DescriptiveCatalog, or verified scholarly release. Repair is a governed rerun, never retro-linking history.

Candidate stores are invisible to active object, anchor, census, assessment, and relation loaders. Generic record add refuses machine-managed inquiry/review, assessment, operation, mapping, relation, and claim stores. In governed workspaces, direct object add/object anchor add must cite a human InquiryReview or equivalent human confirmation receipt. Raw anchor exploration remains lexical and cannot become object evidence.

### 19.3 Inquiry records and computation boundary

ResearchSituation extends the §48 record with schema_version, study_id, verbatim_hunch, normalized_display_hunch, language_observations, premature_decisions, status, actor, and supersession. Normalization is Unicode/whitespace display normalization only. Semantic fields are authored and attributed. English-only input without supplied Persian forms yields needs-vocabulary, never fabricated forms or a silent empty result.

InquiryCatalog is an append-only proposal envelope containing situation/snapshot/Field/scope IDs, parameters, limitations, and stable candidates. Candidate kinds are seed-object, lexical-anchor, authored-contrast, non-object-note, and lexical-neighbor. Every candidate records proposer type/ID and rationale. Lexical candidates record supported, unsupported, or not-applicable, plus hit/poem/poet counts and located examples.

Lexical verification uses the cached pinned corpus and current Field scope. It pins matcher, normalization, tokenizer, unit/window, support/filter, and ordering versions. A supported form has positive counts and at least one CandidateEvidenceRef with repository-relative path, poem ID, verse/couplet coordinates, match span, and snapshot. This probe reference is not an Anchor Hit or object occurrence. Unsupported forms retain exact zero and no fabricated pointer. Nonlexical candidates are not-applicable.

Only verified supplied seed forms drive deterministic lexical-neighbor proposals. The engine never generates semantic contrasts/adversaries. Neighbor ordering is declared raw retrieval priority, never relation strength or explanatory rank. Snapshot/Field/matcher/tokenizer changes stale the receipt and require an appended refresh.

InquiryReview is append-only. Decisions are accept, accept-unsupported, reject, defer, revise, or split, with stable candidate ID, human actor, rationale, receipt, predecessor, and outputs. Accept-unsupported requires rationale and retains that status. Promotion stages all Seed/Object/Anchor/event writes atomically through T02/T03 validators. It creates no Anchor Hit, assessment, Trace, Mapping, or relation. Historical inquiry IDs use type prefix plus UUID4 hex per §6.2.

### 19.4 CLI additions

All support --json:

    ontograph inquire <study> --hunch <text> [--file <yaml-or-json>]
      [--situation <id>]
    ontograph inquire <study> --refresh <inquiry-catalog-id>
      [--situation <id>]
    ontograph inquire <study> --review <decisions.yaml-or-json>
      [--situation <id>]

Create, refresh, and review are mutually exclusive. Create persists no census or analytical OperationRecord. It emits a review template and exact next command; review emits walk commands.

Amend governed object routes with:

    [--review-id <inquiry-review-id> | --confirmation-file <file>]

Add --situation to Field construction, walk, analytical commands, evidence-citing record creation, catalog, and release. Sole-situation inheritance avoids repeated typing.

W11A implements the following after V201/V202/V205/V207 and W10B:

    ontograph catalog <study> --mode assessed-full
      [--situation <id>] [--object <id> ...]
      [--scale poem|couplet|verse|window]
      [--window <N>] [--min-support <N>]

Catalog has no anchor, partial assessed, assessed-rule, or estimated mode through v0.2. Raw neighbors belong to InquiryCatalog; estimated pair matrices remain blocked.

### 19.5 Walk and ambiguity

Walk SHALL display a separate evidence tray, not machine “candidate labels.” It contains reviewed candidates and lexical cues actually located in the current verse/couplet, each with ID, raw lexical status, reason shown, and source pointer. It never recommends a/r/u.

The occurrence question remains whether this Anchor Hit may count for the selected Object Address. Optional c:<candidate-id> pins an append-only candidate-encounter proposal to the stable hit; it cannot promote, assess, trace, map, or relate. Scripts name both stable IDs; stale/mismatched IDs fail atomically.

Done/x may stop but never aggregate or manufacture completeness. Walk reports accepted, rejected, ambiguous, and unassessed eligible-hit counts. Ambiguous is assessed and remains visible in denominators; unassessed remains incomplete and T06 refuses assessed-full. No --allow-partial escape hatch is added.

### 19.6 Operations and DescriptiveCatalog

OperationRecord schema 3 adds situation_id and inquiry_status: governed|legacy-unframed. Study status shows:

    hunch → situation → catalog/review → object/anchor/coverage
    → operation/mapping → Finding → release

Stale, orphan, unsupported, and unframed records are listed separately.

DescriptiveCatalog is immutable and operation-backed over assessed-full Mapping Objects and compatible OccurrencePolicies. Every pair cell carries situation/snapshot/Field/scope, typed scale, eligible-unit denominator, accepted marginals, shared numerator, ambiguity-only counts/shares for each participant and jointly, coverage, policy/mapping/operation/source IDs, raw support including zero, and typed refusal/limitation codes.

Incomplete coverage or stale/incompatible inputs produce a refusal cell with coverage and no assessed co-incidence value. Below-minimum support preserves raw support but refuses association/lift language. Default ordering is stable object ID. Every cell says co-incidence. Construction never writes assessment, Trace, Relation-Object, Claim, or permission.

Persist OperationRecord, Mapping/result, and source manifest before returning. Renderers read persisted records only and perform no counts, joins, ranking, or inference.

### 19.7 Release additions

Add explicit files, empty when necessary:

    records/research-situations.jsonl
    records/seeds.jsonl
    records/inquiry-catalogs.jsonl
    records/inquiry-reviews.jsonl
    records/descriptive-catalogs.jsonl

Events, operations, mappings, and sources remain in their canonical stores. Standalone verify checks inquiry/review references and actors, snapshot/scope receipts, operation situation eligibility, catalog cells/source manifests, and existing hashes/invariants.

### 19.8 Binding row order and conflict resolution

    T01–T13
    → U03(base ResearchSituation/Seed schemas only)
    → W01 → W02 → W03 → W04A → W04B → W05 → W06
    → U01 → U02
    → W07A → W07B → W08
    → U04 → U05 → W09A → W09B
    → U06–U12
    → V201 → V202 → V207 → V203 → V204 → V205
    → W10A → W10B → W11A → W11B
    → V206 → V208 → V209 → V210–V213

T01–T13 stay first; no W row may emulate T04 stable hits, T05 per-hit identity, T06 completeness, T09 persistence, or T10–T12 release isolation.

- U03 is narrowed to base validated ResearchSituation/Seed schemas and generic record routing; onboarding moves to W02/W03.
- U01 covers inquiry, review, unsupported, and stale states. U04/U05 enforce governed supporting evidence. U06/U07 document the inquire-first route. U11 is the ready-made Rostam handoff below.
- V207 now depends on U04,V202, not V206. It enforces all §10 promotion prerequisites but fixes claim_permission to preserve only. Any other permission refuses until V206.
- V206 remains after V205; it adds human-confirmed argue permissions and distribution-policy validation, without rewriting preserve-only history.
- V205 precedes W10A because catalog cells require compatible OccurrencePolicies. V203/V204 do not feed pair catalogs.
- W01–W11B are atomic, test-first rows defined in the OpenSpec tasks file; letter suffixes are separate rows/commits, never bundled work.

### 19.9 Status and gates

Extend U01:

| State | Required suggestion | Forbidden |
|---|---|---|
| no situation | inquire | field/object promotion or analysis |
| no vocabulary | supply attributed candidates | invented translation |
| unverified/stale candidates | refresh | promotion |
| pending review | human review | agent/automatic promotion |
| reviewed object/no hits | revise/preserve lexical negative | object-absence claim |
| hits/incomplete | walk, rule, or estimate | assessed-full/catalog cell |
| full assessed participants | mapping/catalog/source return | automatic relation |
| legacy-unframed operation | inquire and rerun | higher-record/release support |

Gate E becomes study → inquire → field/refresh → human catalog review → object/anchor → walk → assessed-full operation → source return → Finding → inquiry report/release.

Required discriminating fixtures include: English no-fabrication; supported/unsupported/nonlexical candidates; candidate-store isolation; stale receipt refusal; agent/direct-route bypass refusal; review creates no assessment; cue cannot decide hit; ambiguity versus unassessed completion; unframed higher-record refusal; exact catalog denominators/marginals/ambiguity; incomplete/below-support refusal; high support leaves relations unchanged; copied release verify and tamper failure.

Gate G uses a clean ready-made installation and the Rostam workspace. The agent performs proposal drafting, verification, commands, sources, and rendering; the user supplies hunch and explicit catalog/walk decisions. Handoff includes every unsupported/deferred candidate, review receipt, governed object catalog/counts, at least one driven walk, ambiguity/incompleteness, source tray, eligible Finding, self-contained report, timings, and comparison with the original agent-label draft. Only the user passes.

Gate H additionally requires a DescriptiveCatalog release. The Rostam comparison states which original labels stayed proposals, became reviewed objects, had executable anchors, and survived assessed coverage, scale, ablation, ambiguity, and policy. High support never satisfies Relation-Object prerequisites. Only the user passes.

No W row completes from prose or rendered appearance. Its test must discriminate the forbidden shortcut. The v0.2 tag remains last after all T/U/V/W rows, standalone verification, CI/package consistency, and explicit user authorization.


