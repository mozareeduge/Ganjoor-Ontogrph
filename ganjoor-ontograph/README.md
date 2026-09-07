# Ganjoor Ontograph

Ganjoor Ontograph is a governed research apparatus for close and distant reading over the Ganjoor Persian poetry corpus. The researcher remains the source of semantic and occurrence decisions; the CLI records, validates, and renders those decisions.

## Governed quickstart

The complete route is:

**study new → inquire → field/refresh → review → walk → assessed-full operation → source return → Finding → release**

The executable form is:

```text
ontograph study new <study> --corpus-root <corpus> --workspaces-dir <workspaces>
ontograph inquire <study> --hunch "<verbatim hunch>" --actor <researcher> --file proposal.json --workspaces-dir <workspaces> --json
ontograph field build <study> --poet <poet> --workspaces-dir <workspaces> --json
ontograph inquire <study> --refresh <catalog-id> --actor <researcher> --workspaces-dir <workspaces> --json
ontograph inquire <study> --review <decisions.json> --review-actor <researcher> --receipt <human-receipt> --workspaces-dir <workspaces> --json
ontograph walk <study> --object <object-address> --script walk.json --workspaces-dir <workspaces> --json
ontograph census <study> --object <object-address> --mode assessed-full --workspaces-dir <workspaces> --json
ontograph source show <study> --operation <operation-id> --workspaces-dir <workspaces> --json
ontograph record add <study> --type finding --file finding.json --workspaces-dir <workspaces> --json
ontograph release <study> --version <version> --workspaces-dir <workspaces> --json
```

`field build` establishes the field. If the field or corpus snapshot changes after inquiry evidence is verified, use `inquire --refresh <catalog-id>` before review or promotion. “Field/refresh” is one governed stage, not a command literally named `field/refresh`.

The agent prepares the attributed proposal, review-file template, stable walk script, and Finding-file template, and runs the CLI. The researcher supplies the verbatim hunch, approves or rejects semantic candidate proposals, supplies the human review receipt, and decides each hit as occurrence, rejection, or ambiguity. Agent proposals are never evidence or automatic promotion.

With one active ResearchSituation, governed commands inherit it. With no situation they refuse and point to `inquire`. With multiple active situations, pass `--situation <id>`; the CLI never chooses the newest situation. A sole active situation is inherited, not silently duplicated.

## What the records mean

An Anchor Hit is lexical incidence, not an object occurrence. A candidate catalog is inquiry evidence, not a Finding or relation. Review promotes a supported candidate to an Object Address/Lexical Anchor but creates no occurrence assessment. `walk` is the default per-hit assessment route; `done` stops interaction but does not make incomplete coverage complete. `assessed-full` requires every eligible stable hit to have an active assessment, keeps ambiguity in the denominator, and is not equivalent to `anchor`, `assessed-rule`, or `estimated`.

A source return through `source show` (or `source export`) resolves the stored source manifest to exact poem context. A Finding is a validated record that cites governed operations and source support; a report or release file is not itself a Finding. Raw co-incidence, high support, or an agent interpretation does not become a Relation-Object without its governed route and human permission. Legacy-unframed operations remain readable but cannot support a Finding or verified scholarly release.

## Further reading

- [`implementation/HOW_TO_RUN.md`](implementation/HOW_TO_RUN.md) — researcher runbook and decision boundaries.
- [`MIGRATION.md`](MIGRATION.md) — moving from the pre-inquiry flow.
- [`CHANGELOG.md`](CHANGELOG.md) — release history.
- [`../.claude/skills/persian-poetry-ontograph/SKILL.md`](../.claude/skills/persian-poetry-ontograph/SKILL.md) — agent-facing execution detail.
- `Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` — methodological specification.
