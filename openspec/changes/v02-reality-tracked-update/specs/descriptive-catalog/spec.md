## ADDED Requirements

### Requirement: Assessed-full descriptive catalog

The system SHALL construct a DescriptiveCatalog only from governed assessed-full object operations under one pinned situation, corpus snapshot, Field scope, typed scale, and compatible OccurrencePolicies. Raw-anchor neighbor exploration SHALL remain in the InquiryCatalog and SHALL NOT be rendered as an object relation catalog.

#### Scenario: incomplete pair becomes a refusal cell

- **WHEN** either object in a pair has unassessed eligible Anchor Hits or a stale/incompatible policy
- **THEN** the cell records coverage counts and a typed refusal reason
- **AND** it contains no assessed co-incidence value or relation description

### Requirement: Complete denominators and ambiguity

Every computed pair cell SHALL carry the eligible-unit denominator, accepted marginal counts, shared accepted-unit numerator, occurrence mode/policy IDs, assessment coverage, ambiguous-only counts/shares for both participants and jointly, typed scale, and source-manifest references.

#### Scenario: zero and minimum support remain honest

- **WHEN** a fully assessed pair has zero shared accepted units or falls below minimum support
- **THEN** the raw observed support remains visible
- **AND** association/lift language is refused with `support_below_minimum`, rather than replacing the observation with a bare zero or fabricated association

### Requirement: Ontographic staging without synthesis

The catalog SHALL use stable object-ID ordering by default and SHALL describe every cell as co-incidence. It SHALL NOT rank objects into an explanatory hierarchy or create a Relation-Object, Claim, Trace, or OccurrenceAssessment.

#### Scenario: high support cannot auto-promote

- **WHEN** a catalog cell has the highest support in the field
- **THEN** it remains a co-incidence cell
- **AND** Relation-Object creation is available only through V207's separately human-confirmed prerequisites, including Trace, Mapping Object, plural candidate descriptions or rationale, counter-evidence, use status, permission, and history

### Requirement: Operation-backed rendering and source return

Catalog computation SHALL persist an immutable OperationRecord, Mapping Object, result, and source manifest before rendering. Markdown/HTML/JSON renderers SHALL read only those persisted records and SHALL perform no counts, joins, ranking, or inference.

#### Scenario: copied release verifies catalog values

- **WHEN** a release containing a DescriptiveCatalog is copied away from its workspace
- **THEN** verification reconstructs every displayed numerator, denominator, refusal, ambiguity count, and source link from staged release records alone
- **AND** tampering with a cell or source reference fails verification
