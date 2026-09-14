# Operations

The governed route is ordered. Do not skip inquiry/review/walk because a command can be called directly. Do not report a number without denominator, scale, mode, OperationRecord/source IDs, and limitations.

| Stage | CLI verb | Requires | Result-card obligation |
|---|---|---|---|
| Create study | `ontograph study new` | study id, pinned corpus root | Record the stored corpus root; no analysis yet. |
| Intake hunch | `ontograph inquire` | verbatim hunch, actor, optional proposal file | Persist ResearchSituation and InquiryCatalog; no object, assessment, operation, or mapping writes. |
| Build Field | `ontograph field build` | active situation, stored or explicit corpus root, scope | Field/scope becomes part of later evidence receipts. |
| Refresh evidence | `ontograph inquire --refresh` | catalog id, active situation | Append a superseding verified InquiryCatalog; supported/unsupported forms stay distinct. |
| Human review | `ontograph inquire --review` | researcher decisions, human actor, receipt | Append InquiryReview; accepted supported candidates promote provisional Seed/Object/Anchor records; no assessment. |
| Walk assessment | `ontograph walk` | reviewed Object Address, active situation, researcher decisions | Persist only completed per-hit OccurrenceAssessments; report accepted/rejected/ambiguous/unassessed. |
| Anchor census | `ontograph census --mode anchor` | Object Address, approved anchors | Label as lexical/anchor incidence, not object occurrence. |
| Assessed-full census | `ontograph census --mode assessed-full` | 100% eligible-hit assessment coverage | State exact object incidence with denominator and ambiguity counts. |
| Recurrence map | `ontograph map recurrence --mode assessed-full` | complete assessments, unit | Show prevalence/spread/concentration with raw counts and source manifest. |
| Co-incidence | `ontograph companions --mode assessed-full` | fully assessed participating objects, scale | Say co-incidence; never relation, causation, or significance without a declared condition. |
| Compare | `ontograph compare --mode assessed-full` | compatible governed fields | Show raw incidence beside ratios/deltas. |
| Ablate | `ontograph ablate --mode assessed-full` | governed operation target/removal | Report before/after/retention; do not infer why without a Finding. |
| Source return | `ontograph source show` | poem pointer or operation id | Resolve stored source manifest to exact poem/verse/couplet context. |
| Source export | `ontograph source export` | operation id, output directory | Write Markdown and JSON source trays from stored manifests only. |
| Finding | `ontograph record add --type finding` | governed OperationRecord/source support | Validate pressure, operation, observation, consequence, and limits before writing. |
| Release | `ontograph release` | study id, version, validated records | Render/stage ResearchRelease with inquiry history, records, sources, reports, and license notice. |

Legal mode language: `anchor`, `assessed-full`, `assessed-rule`, `estimated`. The old `assessed` spelling is an implementation compatibility alias, not the researcher-facing term.

Every card ends with source return, legal next actions, and a "How was this made?" disclosure. Raw neighbors belong to InquiryCatalog; a DescriptiveCatalog is future assessed-full work and must not be faked from raw anchors.