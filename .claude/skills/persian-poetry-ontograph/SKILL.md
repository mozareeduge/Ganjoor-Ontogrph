---
name: persian-poetry-ontograph
description: Use when running a governed Ganjoor Ontograph study from hunch intake through inquiry review, walk assessment, assessed-full operations, source return, Finding, and release. Not for open-ended poem discovery, quoting a remembered line, or "what does Ganjoor say about X"; use persian-poetry-mcp for that.
version: 0.1.2
author: Mohammad Zare
license: MIT
metadata:
  hermes:
    tags: [persian, poetry, ontograph, research, corpus-analysis, ooo]
    related_skills: [persian-poetry-mcp]
---

# persian-poetry-ontograph

This skill orchestrates the governed Ganjoor Ontograph research route. It does not interpret a hunch, translate English into Persian motifs, or turn search results into claims. It prepares files, runs the deterministic `ontograph` CLI, checks JSON output and exit codes, and asks the researcher for the semantic review and occurrence decisions that only a human may supply.

If `ontograph` is missing, a command exits non-zero, or stdout is not one well-formed JSON object where JSON is requested, stop and report the exact failure. Never narrate a calculation the CLI did not produce.

## Division Of Labor

- Discovery, quoting, remembered lines, or broad "what does Ganjoor say about X" questions route to `persian-poetry-mcp`.
- A study hunch, ResearchSituation, InquiryCatalog, human review, Object Address, Lexical Anchor, walk, assessed-full operation, Mapping Object, Finding, Relation-Object, or Research Release routes here.
- Agent-authored proposal material stays proposal-tier until an explicit human InquiryReview accepts, rejects, defers, revises, or splits it.
- Review approval means "track this address/use this anchor for retrieval." It is not an OccurrenceAssessment and creates no accepted occurrence.

## Governed Fresh-Session Route

Use this order for a new governed workspace:

```text
study new -> inquire -> field build/refresh evidence -> human review -> walk -> assessed-full operation -> source show/export -> validated Finding -> release
```

The agent prepares proposal, review, walk-script, and Finding files; the researcher supplies the hunch, semantic candidate review, and per-hit occurrence decisions. With one active ResearchSituation, governed commands inherit it. With none, commands must refuse and point to `inquire`. With several, pass `--situation`; never choose the newest situation by recency.

```bash
STUDY="mirror-in-hafez"
WORKSPACES="ontograph-workspaces"
CORPUS_ROOT="."

ontograph study new "$STUDY" --corpus-root "$CORPUS_ROOT" --workspaces-dir "$WORKSPACES"

# Agent prepares templates/inquiry-proposal.md from the researcher's hunch.
# The proposal records proposer type/ID and rationale; it does not create objects.
ontograph inquire "$STUDY" --hunch "<verbatim researcher hunch>" --actor "<researcher-id>" --file proposal.json --workspaces-dir "$WORKSPACES" --json

# Field construction is governed by the active situation. Refresh evidence after
# the Field/scope is present so support receipts match the current scope.
ontograph field build "$STUDY" --poet hafez --workspaces-dir "$WORKSPACES" --json
ontograph inquire "$STUDY" --refresh "<inquiry-catalog-id>" --actor "<researcher-id>" --workspaces-dir "$WORKSPACES" --json

# Researcher supplies the review decisions; the agent writes the file and runs it.
# Accepting a supported candidate promotes provisional Seed/Object/Anchor records.
ontograph inquire "$STUDY" --review "$REVIEW_FILE" --review-actor "<researcher-id>" --receipt "<human-review-receipt>" --workspaces-dir "$WORKSPACES" --json

# Researcher supplies occurrence decisions for each stable Anchor Hit.
# a/r/u decide only the selected Object Address occurrence question.
ontograph walk "$STUDY" --object "<object-address>" --script "$WALK_SCRIPT" --workspaces-dir "$WORKSPACES" --json

# Only use assessed-full wording after the walk or another valid assessment route
# covers every eligible Anchor Hit for the selected object(s).
ontograph census "$STUDY" --object "<object-address>" --mode assessed-full --workspaces-dir "$WORKSPACES" --json
ontograph map recurrence "$STUDY" --object "<object-address>" --unit poem --mode assessed-full --workspaces-dir "$WORKSPACES" --json
ontograph companions "$STUDY" --object "<object-address>" --with "<other-object>" --scale couplet --mode assessed-full --workspaces-dir "$WORKSPACES" --json

ontograph source show "$STUDY" --operation "<operation-record-id>" --workspaces-dir "$WORKSPACES" --json
ontograph source export "$STUDY" --operation "<operation-record-id>" --output sources/ --workspaces-dir "$WORKSPACES" --json

# A Finding cites a governed OperationRecord/source manifest. It is validated
# before release and is never a bare number.
ontograph record add "$STUDY" --type finding --file finding.json --workspaces-dir "$WORKSPACES" --json
ontograph release "$STUDY" --version 0.1.2 --workspaces-dir "$WORKSPACES" --json
```

`--corpus-root` is required when creating or explicitly overriding the study's stored corpus root. Later commands should use the stored root unless a deliberate override is needed and reported. Do not add `--corpus-root` mechanically to every verb.

## Assessment And Walk Rules

- `walk` is the default route for OccurrenceAssessment. Per-hit `assess` is a repair/correction tool; legacy poem-keyed compatibility does not satisfy assessed-full coverage.
- `done` or `x` may stop a walk, but incomplete coverage remains incomplete. The result must list accepted, rejected, ambiguous, and unassessed counts.
- Ambiguous hits are assessed and stay visible in denominators. Unassessed hits keep `assessed-full` unavailable.
- Evidence-tray cues and `c:<candidate-id>` actions are proposals only. They cannot decide a hit or create an Object Address, Trace, Mapping Object, Relation-Object, or claim.

## Modes And Language

Use canonical mode names in researcher-facing text: `anchor`, `assessed-full`, `assessed-rule`, `estimated`. `anchor` is lexical incidence, not object occurrence. `assessed-full` is exact object incidence only when all eligible stable Anchor Hits have active assessments. `assessed-rule` and `estimated` must remain explicitly labelled and cannot be presented as an exact assessed-full census.

Raw neighbors stay in InquiryCatalog. A future DescriptiveCatalog route is assessed-full and operation-backed; until that CLI exists, do not promise a catalog command or render raw-anchor neighbors as object relations.

## Result Cards

Every operation result shown to the researcher includes:

1. one plain-language sentence;
2. raw counts, denominators, scale, mode, and ambiguity/coverage state;
3. OperationRecord and source-manifest IDs;
4. a source-return action;
5. legal next actions such as continue walk, refresh inquiry evidence, source export, draft a Finding, or release;
6. an optional "How was this made?" expansion with parameters, policies, and limitations.

## Permissioning

The project allowlist names specific `ontograph` verbs. Do not request blanket Bash access. Destructive workspace deletion, forced object merge, or history rewrite commands stay outside the allowlist and require explicit confirmation every time.

## References

- `references/terminology.md` - project vocabulary and non-equivalence rules.
- `references/operations.md` - governed operation route and result-card obligations.
- `references/claim-permission.md` - Use-Status and Claim Permission language.

## Templates

- `templates/research-situation.md`
- `templates/inquiry-proposal.md`
- `templates/inquiry-review.md`
- `templates/walk-script.md`
- `templates/finding.md`
- `templates/field-charter.md`
- `templates/relation-object.md`
- `templates/research-release.md`