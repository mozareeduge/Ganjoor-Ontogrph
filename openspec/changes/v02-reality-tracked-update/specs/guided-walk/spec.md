## MODIFIED Requirements

### Requirement: Situation-bound walk

Walk SHALL identify the active ResearchSituation and reviewed InquiryCatalog used for the selected Object Address. With no situation it SHALL refuse; with multiple active situations it SHALL require an explicit `--situation`.

#### Scenario: situation is never guessed

- **WHEN** a study contains two active ResearchSituations and walk is called without `--situation`
- **THEN** walk fails before sampling or writing and lists the eligible situation IDs

### Requirement: Per-hit evidence cues, not answer labels

For each Anchor Hit, walk SHALL show a visually separate evidence tray of reviewed candidate objects and lexical-neighbor cues actually located in the displayed verse/couplet. Every cue SHALL carry a candidate/anchor ID, its lexical status, and a stable source pointer. Cues SHALL NOT be described as classifications or recommended occurrence decisions.

#### Scenario: cue cannot decide the hit

- **WHEN** a displayed hit has a high-support lexical-neighbor cue
- **THEN** the current object's decision remains unassessed until the researcher chooses `a`, `r`, or `u`
- **AND** pinning `c:<candidate-id>` records only a candidate encounter event, not an Object Address, OccurrenceAssessment, Trace, Mapping Object, or Relation-Object

#### Scenario: every displayed cue returns to source

- **WHEN** a cue appears in walk
- **THEN** its source pointer resolves through `source show` to the exact poem and verse/couplet coordinates

### Requirement: Completion and ambiguity remain distinct

Walk SHALL allow a researcher to stop without imputing decisions. On `done` or stop it SHALL report accepted, rejected, ambiguous, and unassessed eligible-hit counts plus legal next modes. Ambiguous hits count as assessed but remain visible in denominators; unassessed hits keep assessed-full unavailable.

#### Scenario: done cannot manufacture completeness

- **WHEN** `done` is issued with eligible unassessed hits remaining
- **THEN** walk writes only completed decisions, reports incomplete coverage, and suggests continuation, assessed-rule, or estimated routes
- **AND** a later assessed-full aggregator refuses under the T06 completeness rule

### Requirement: Stable scripted identity

Inquiry additions SHALL preserve the binding stable-Anchor-Hit scripted format. Candidate encounter actions, when present, SHALL name candidate IDs and Anchor Hit IDs; array position SHALL never identify either record.

#### Scenario: stale catalog script refuses atomically

- **WHEN** a script names a superseded candidate or a hit from another snapshot
- **THEN** walk fails before writing any assessment or candidate encounter
