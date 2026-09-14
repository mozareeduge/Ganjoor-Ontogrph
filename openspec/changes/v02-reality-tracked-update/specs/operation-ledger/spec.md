## MODIFIED Requirements

### Requirement: Inquiry provenance on operations

Every new OperationRecord SHALL carry `situation_id` and `inquiry_status: governed|legacy-unframed`. A governed operation SHALL reference an active ResearchSituation compatible with its study. A sole active situation MAY be inherited; multiple active situations SHALL require explicit selection.

#### Scenario: provenance chain is visible

- **WHEN** an operation created after inquiry is shown via `study status`
- **THEN** status displays hunch → situation → InquiryCatalog/review → object/assessment → operation → Finding using record IDs
- **AND** it separately lists orphan, stale, or unframed records

### Requirement: Unframed history cannot become governed evidence

Legacy operations with no situation SHALL remain readable and immutable with a `legacy-unframed` limitation. They SHALL NOT support a Finding, Claim, Relation-Object, DescriptiveCatalog, or verified scholarly release. Governance SHALL be restored by rerunning the operation under a situation, never by mutating or retro-linking the old record.

#### Scenario: imported dashboard is not apparatus evidence

- **WHEN** a record or report cites external counts without a governed OperationRecord and source manifest
- **THEN** higher-order record validation refuses the citation
- **AND** the material may be retained only as an attributed proposal or legacy artifact

### Requirement: Inquiry preflight is atomic

Situation selection and compatibility SHALL be validated before corpus computation or workspace writes. The selected situation ID SHALL be written into the OperationRecord automatically; callers SHALL NOT be able to supply a different ID only at render or release time.

#### Scenario: ambiguous active situations fail cleanly

- **WHEN** an analytical command runs in a study with two active situations and no `--situation`
- **THEN** it exits non-zero before computation, diagnostics go to stderr, stdout remains empty, and no OperationRecord is appended
