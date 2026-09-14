# Migration guide: pre-inquiry studies to the governed route

U06 made the inquire-first route the supported researcher workflow. Existing workspaces remain readable, but the old “study → object → census” shortcut is not the v0.2 route.

## New order

Use **study new → inquire → field/refresh → review → walk → assessed-full operation → source return → Finding → release**. `field build` is the field step; `inquire --refresh` is required when a verified catalog is stale because the field, corpus snapshot, or matcher changed.

The concrete commands are documented in [`README.md`](README.md) and [`implementation/HOW_TO_RUN.md`](implementation/HOW_TO_RUN.md). The actual review command is `ontograph inquire <study> --review <decisions.json>`, and the occurrence route is `ontograph walk`; there is no implicit automatic promotion or assessment.

## Who supplies what

The agent may prepare proposal, review, walk-script, and Finding files and execute deterministic commands. The researcher supplies the verbatim hunch, semantic candidate approvals/rejections, human review receipt, per-hit occurrence decisions, and interpretation. Agent attribution is not human evidence.

## Situation selection

A sole active ResearchSituation is inherited by governed commands. With no active situation, the command refuses and directs the user to `inquire`. With multiple active situations, pass `--situation <id>` explicitly; the engine never picks the newest one. This is an intentional non-equivalence: sole-situation inheritance is not silent situation creation or recency selection.

## Terminology that must not be collapsed

- Anchor Hit ≠ object occurrence; candidate support ≠ evidence.
- Review promotion ≠ occurrence assessment; review creates no assessment.
- `anchor` ≠ `assessed-full`; the latter requires 100% eligible-hit coverage.
- Ambiguous ≠ unassessed; ambiguity remains in assessed-full denominators.
- `assessed-rule`/`estimated` ≠ exact assessed-full census.
- Source return is required before a result supports a scholarly Finding.
- Finding ≠ report artifact; raw co-incidence/high support ≠ Relation-Object.
- Legacy-unframed operations are readable history, not support for Findings or verified releases.

## Legacy workspaces and records

Do not rewrite append-only history to resemble the new route. Read legacy operation records as `legacy-unframed`, rerun the study through `inquire`, review, walk, and a governed operation, then return to sources before drafting a Finding. A release must be staged and verified from its own immutable contents.
