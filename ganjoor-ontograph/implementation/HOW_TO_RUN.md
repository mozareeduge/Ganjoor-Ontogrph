# Researcher runbook

Use this route for every governed study:

**study new → inquire → field/refresh → review → walk → assessed-full operation → source return → Finding → release**

## 1. Start and inquire

Create a study with a pinned corpus root. Then submit the researcher's hunch verbatim with `ontograph inquire`. The agent may prepare `proposal.json` and suggest attributed Persian forms; it must not invent a translation. English-only hunches remain `needs-vocabulary` until the researcher supplies or approves forms.

```text
ontograph study new <study> --corpus-root <corpus> --workspaces-dir <workspaces>
ontograph inquire <study> --hunch "<verbatim hunch>" --actor <researcher> --file proposal.json --workspaces-dir <workspaces> --json
```

## 2. Field and refresh

Build the declared field. If its scope, corpus snapshot, or matcher changes after a catalog was verified, refresh that catalog; refresh appends a superseding catalog and never rewrites the original.

```text
ontograph field build <study> --poet <poet> --workspaces-dir <workspaces> --json
ontograph inquire <study> --refresh <catalog-id> --actor <researcher> --workspaces-dir <workspaces> --json
```

## 3. Review, walk, and operate

The researcher supplies review decisions and a human receipt. The agent writes and runs the review file. Accepted supported candidates promote objects/anchors; review never assesses hits. The researcher then supplies per-hit decisions in a walk script.

```text
ontograph inquire <study> --review <decisions.json> --review-actor <researcher> --receipt <human-receipt> --workspaces-dir <workspaces> --json
ontograph walk <study> --object <object-address> --script <walk.json> --workspaces-dir <workspaces> --json
ontograph census <study> --object <object-address> --mode assessed-full --workspaces-dir <workspaces> --json
```

`assessed-full` is exact only at 100% eligible-hit coverage. Ambiguous hits are assessed and remain in denominators; unassessed hits keep the mode unavailable. `anchor`, `assessed-rule`, and `estimated` are not equivalents.

With one active ResearchSituation, commands inherit it. With none, they refuse and direct the user to `inquire`. With multiple active situations, provide `--situation <id>`; never rely on recency. The sole-situation shortcut is inheritance only.

## 4. Return to source, write a Finding, release

Return to exact poem context from the operation's source manifest before writing a Finding. The agent can prepare the Finding file, but the researcher owns the interpretation and limits.

```text
ontograph source show <study> --operation <operation-id> --workspaces-dir <workspaces> --json
ontograph record add <study> --type finding --file finding.json --workspaces-dir <workspaces> --json
ontograph release <study> --version <version> --workspaces-dir <workspaces> --json
```

A Finding cites governed operations and source support; it is not a report artifact. A release stages inquiry history, records, source manifests, reports, hashes, and verification data. Never treat raw candidate support, co-incidence, or a high count as a relation or claim.

## Boundaries

The CLI is deterministic and append-only. The agent prepares files and executes commands. The researcher supplies semantic candidate review, occurrence decisions, and interpretive claims. Unsupported, stale, mixed-situation, direct-route, and legacy-unframed shortcuts must refuse rather than silently produce zeros or claims.
