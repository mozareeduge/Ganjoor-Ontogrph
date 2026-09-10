# Design — v02-reality-tracked-update

## Context

The Rostam test showed an upstream governance failure: the agent could move from a hunch to episode labels and charts without creating any apparatus records. Current v0.1 also uses poem-keyed assessments and does not yet persist OperationRecords, so this change must depend on—not duplicate or assume—the T-series trust repair.

The binding method begins ResearchSituation → Seed → Object Address → Lexical Anchor → Anchor Hit → OccurrenceAssessment. This design makes that chain executable while keeping semantic authorship separate from deterministic corpus computation.

## Goals and non-goals

Goals:

- Make a minimal ResearchSituation the easiest and required entry to new governed analysis.
- Preserve a verbatim hunch and attributed semantic proposals without laundering them into engine facts.
- Verify lexical candidates offline against the pinned snapshot and declared scope.
- Require a recorded human review before candidates enter active object/anchor stores.
- Give walk users source-backed lexical cues without suggesting occurrence answers.
- Render inquiry state and, later, complete assessed co-incidence as self-contained catalog artifacts.

Non-goals:

- Semantic translation, motif extraction, strategy classification, or corpus-wide labeling by the runtime.
- Automatic contrast/adversary inference, object promotion, OccurrenceAssessment, Relation-Object promotion, or Claim permission.
- A graph database, browser workbench, dependency, network call, or runtime LLM.
- Pairwise estimated relations or rewriting completed history.

## Decisions

### 1. Inquiry is a governance preflight, not an interpretive phase gate

`inquire` accepts a minimal hunch and cannot reject it for being vague. For new schema-version-2 workspaces, however, Field construction, object/anchor promotion, walk, and analytical verbs require an active ResearchSituation. This prevents the realistic skip while preserving agency over the hunch's content.

Legacy workspaces remain readable. A legacy operation with no situation is labeled `legacy-unframed`, carries a limitation, and may be inspected, but it cannot support a Finding, Claim, Relation-Object, or verified scholarly release. The remedy is a new situation and a rerun, never mutation of old history.

If exactly one situation is active, commands inherit it. With zero, they refuse and print the `inquire` command. With more than one, they require `--situation`; they never select by recency.

### 2. “Normalization” is lossless; semantic proposals are attributed

The engine stores:

- the verbatim hunch;
- Unicode/whitespace-normalized display text;
- language/script observations;
- authored ResearchSituation fields; and
- attributed candidate entries from a YAML/JSON proposal file.

It may tokenize Persian lexical forms explicitly supplied in that file. It does not translate English to Persian, infer “cunning,” synthesize motifs, or call co-occurring tokens “objects.” An English-only hunch with no supplied Persian lexical forms validly yields `needs-vocabulary`; this is not a silent empty catalog.

The agent can do the semantic drafting for the researcher, but every entry records `proposed_by_type`, `proposed_by_id`, and rationale. The researcher reviews the proposal once; the engine does the repetitive corpus verification.

### 3. InquiryCatalog and DescriptiveCatalog are different types

An `InquiryCatalog` is an append-only proposal envelope:

```yaml
schema_version: 1
id: ic1-...
situation_id: rs1-...
corpus_snapshot_id: cs1-...
field_charter_version: 1|null
scope_spec: {}
parameters: {}
candidates:
  - id: cand1-...
    kind: seed-object|lexical-anchor|authored-contrast|non-object-note|lexical-neighbor
    label: ""
    object_candidate_id: null
    form: null
    proposed_by_type: human|agent|engine
    proposed_by_id: ""
    proposal_rationale: ""
    support_status: supported|unsupported|not-applicable
    anchor_hit_count: null
    poem_count: null
    poet_count: null
    evidence: []
limitations: []
created_at: ""
supersedes: null
```

Supported lexical candidates have at least one stable `CandidateEvidenceRef`/source pointer. That probe reference is not an Anchor Hit or object occurrence. Unsupported forms have exact zero counts and no fabricated pointer. Nonlexical candidates are `not-applicable`, not zero-support anchors.

A `DescriptiveCatalog` is a persisted view over assessed-full Mapping Objects. It is not stored in the inquiry candidate file and is never produced from raw neighbor counts.

### 4. Candidate verification is corpus computation; hunch semantics are not

The cached index performs exact/phrase support queries and deterministic lexical-neighbor discovery around verified seed anchors. The receipt pins snapshot, Field scope, anchor/matcher/tokenizer versions, window/unit, minimum support, stop-token/filter version, and example-selection rule. A Field or corpus change makes it stale and requires `inquire --refresh`.

Engine-generated candidates are named `lexical-neighbor`, ordered by a declared retrieval score, and labeled raw-anchor exploration. The engine never generates semantic contrast/adversary candidates; those must be authored proposals. Common words remain visible when filters do not exclude them. A retrieval rank is not an explanatory hierarchy or relation strength.

### 5. Candidate review is append-only and separate from occurrence review

An `InquiryReview` records one decision per candidate ID: `accept`, `reject`, `defer`, `revise`, or `split`, with actor, rationale, predecessor, and evidence receipt. Only an explicitly human-attributed review can materialize a provisional Seed/Object Address or approve a retrieval anchor. An accepted zero-support form requires the distinct decision `accept-unsupported` plus rationale and remains visibly unsupported.

Candidate files are not read by census/object loaders. Generic `record add` cannot write machine-managed inquiry, review, assessment, operation, mapping, relation, or claim stores. Direct `object add`/`object anchor add` in governed workspaces must reference a valid review event or record an equivalent explicit human confirmation. Thus an agent cannot bypass review by writing the active JSONL path through another CLI route.

Review approval means “track this address/use this anchor for retrieval.” It is never an OccurrenceAssessment and creates no accepted occurrence.

### 6. Walk shows cues, not candidate labels

Answer-suggesting “candidate labels per hit” would recreate the Rostam failure inside the walk. Instead, each hit displays a separate evidence tray containing reviewed candidate objects and lexical-neighbor cues actually located in that verse/couplet. Each card includes candidate/anchor ID, observed form, support label, stable hit/source pointer, and why it is being shown.

The `a/r/u` response still answers only the selected Object Address occurrence question. Optional `c:<candidate-id>` pins a candidate encounter to the current hit as a proposal event; it cannot create an object, assessment, Trace, Mapping, or relation. Script identity remains Anchor Hit based.

`done` may end a walk but cannot make incomplete coverage complete. It reports accepted/rejected/ambiguous/unassessed counts and legal next modes. Ambiguous assessments are completed assessments that remain in denominators; unassessed hits trigger the existing assessed-full refusal in T06. No `--allow-partial` escape hatch is added.

### 7. Descriptive catalog is assessed-full and operation-backed

`ontograph catalog <study> --mode assessed-full ...` writes an immutable OperationRecord plus Mapping Object/source manifest before rendering. Each deterministic object-pair cell contains:

- typed scale and eligible-unit denominator;
- accepted marginal counts and shared accepted-unit numerator;
- ambiguous-only counts/shares for each participant and jointly;
- assessment coverage for both participants;
- occurrence-policy and source-manifest IDs;
- raw support even when zero; and
- typed refusal reasons for incomplete coverage, stale policy, unsupported scale, or support below the declared minimum.

Minimum support refuses association/lift language, not the raw observed count. Incomplete pairs produce refusal cells and no assessed co-incidence number. Default ordering is stable object ID, not association rank. Every cell says `co-incidence`; Relation-Object language is unavailable without V207's separate human promotion route.

### 8. Situation provenance is mandatory for governed operations

OperationRecord schema 3 adds `situation_id` and `inquiry_status: governed|legacy-unframed`. The selected situation is recorded automatically after preflight. `study status` displays situation → catalog/review → object/assessment → operation → Finding links and orphan/unframed records.

Higher-order record validators require supporting governed OperationRecords and source manifests. Reports and release verification apply the same rule, preventing an external dashboard or raw JSON from being imported as if it had passed the apparatus.

### 9. Re-sequencing resolves dependencies explicitly

- T01–T13 remain first; W work cannot use stable hits, complete modes, operations, or releases before they exist.
- U03 supplies base ResearchSituation/Seed schemas. W01–W06 (including W04A/W04B) then build isolated inquiry stores, intake, verification, and review/promotion. U01/U02 follow so status and source return can expose the complete route. W07A/W07B, W08, and W09A/W09B add provenance preflight, guided-walk cues, and inquiry release/report integration before U11.
- After U12, V201 and V202 establish shared scopes and scale-aware Mapping Objects.
- V207 moves ahead of V203 with an amended dependency on `U04,V202`: it implements promotion prerequisites and fixes new Relation-Objects to `claim_permission: preserve only`. V206 later adds human-confirmed argument permissions and distribution-policy checks after V205. This removes the original V207→V206 dependency cycle without weakening permission guards.
- V203–V205 follow V207 so catalog cells have general compatible OccurrencePolicies. W10A/W10B and W11A/W11B then add the DescriptiveCatalog; V206 and the remaining v0.2 rows resume afterward.

## Failure and atomicity rules

- Invalid proposal/review files, stale candidate IDs, stale snapshot/scope receipts, unsupported matcher modes, or mixed situations fail before writes.
- Multi-record promotion stages all outputs and appends atomically; a partial promotion is forbidden.
- Refresh and correction append superseding records. No proposal, review, operation, or event is rewritten.
- JSON stdout remains one object; diagnostics and compatibility warnings use stderr.

## Acceptance

The fixture must distinguish these forbidden shortcuts: English-to-Persian fabrication; candidates loaded as active objects; review mistaken for occurrence assessment; stale evidence accepted; candidate cues deciding a hit; partial review entering assessed-full; raw-anchor catalog presented as assessed; high support promoted to relation; unframed output supporting a Finding; renderer recomputation.

The real Rostam handoff must be generated from a clean ready-made installation. The agent performs proposal drafting, corpus verification, command execution, source export, and rendering. Mohammad supplies the hunch and explicit catalog/walk decisions, then reviews the release. Timings, unsupported candidates, ambiguity, incomplete coverage, and every departure from the original 15-label draft remain visible.
