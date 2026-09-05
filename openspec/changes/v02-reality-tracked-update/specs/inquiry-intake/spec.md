## ADDED Requirements

### Requirement: Lossless hunch intake

The system SHALL persist a free-form Persian or English hunch as a ResearchSituation before a new governed workspace constructs a Field, promotes objects, starts walk, or runs analytical commands. Intake SHALL preserve the verbatim text, distinguish deterministic display normalization from authored semantic fields, and SHALL NOT translate, infer motifs, or generate strategy labels.

#### Scenario: vague English opening remains honest

- **WHEN** a researcher submits “I keep noticing Rostam winning by cunning” without Persian lexical forms
- **THEN** the ResearchSituation stores the verbatim hunch and attributed authored fields
- **AND** the InquiryCatalog reports `needs-vocabulary` rather than fabricating Persian anchors or running a census

#### Scenario: intake precedes analysis

- **WHEN** a new governed study has no active ResearchSituation
- **THEN** Field construction, object/anchor promotion, walk, and analytical commands refuse before computation or write
- **AND** `study status` offers `ontograph inquire <study> ...` as the next action

### Requirement: Attributed candidate proposal

The system SHALL accept a schema-validated proposal file containing candidate Seeds, Object Addresses, lexical forms, authored contrasts, and non-object notes. Every semantic proposal SHALL record proposer type/ID and rationale and SHALL remain candidate-tier.

#### Scenario: agent proposal remains a proposal

- **WHEN** an agent-authored proposal file is ingested
- **THEN** its entries are stored only in an InquiryCatalog
- **AND** no active Object Address, approved LexicalAnchor, OccurrenceAssessment, census result, or Mapping Object is created

### Requirement: Deterministic corpus verification

The system SHALL verify supplied exact/phrase forms and derive lexical-neighbor candidates only from the cached pinned corpus under the current Field scope. Verification SHALL record snapshot, scope, matcher, tokenizer, window/unit, filters, counts, spread, and located examples.

#### Scenario: supported and unsupported forms remain distinct

- **WHEN** proposed forms are verified
- **THEN** every supported form has positive hit/poem counts and at least one stable source pointer
- **AND** a zero-hit form is retained in an explicit `unsupported` state with zero counts and no fabricated pointer
- **AND** a nonlexical candidate is `not-applicable`, not represented as a zero-hit anchor

#### Scenario: field change stales evidence

- **WHEN** the corpus snapshot or Field scope differs from a candidate's verification receipt
- **THEN** promotion refuses and directs the user to append a refreshed InquiryCatalog

### Requirement: Human review before promotion

The system SHALL keep candidate stores inaccessible to object/census loaders and SHALL require an append-only, explicitly human-attributed InquiryReview before materializing a provisional Object Address or approved retrieval anchor. Review approval SHALL NOT create an OccurrenceAssessment.

#### Scenario: reviewed candidate becomes addressable but unassessed

- **WHEN** a human accepts a supported object/anchor candidate
- **THEN** promotion atomically creates the Seed/Object Address/LexicalAnchor records and a review event
- **AND** the new object has zero accepted occurrences until its Anchor Hits are assessed through walk or another valid assessment route

#### Scenario: bypass routes are refused

- **WHEN** an agent-authored review, stale candidate ID, generic `record add`, or unreferenced direct object-add route attempts to write governed active objects
- **THEN** the command fails before any write

### Requirement: Append-only review lifecycle

Inquiry review decisions SHALL be `accept`, `accept-unsupported`, `reject`, `defer`, `revise`, or `split`; corrections SHALL supersede prior review rows. Accepting an unsupported lexical form SHALL require a human rationale and SHALL preserve its unsupported status.

#### Scenario: revised candidate retains history

- **WHEN** a candidate form is revised after review
- **THEN** the old proposal and review remain readable
- **AND** a new candidate/verification/review chain is appended rather than mutating the old rows
