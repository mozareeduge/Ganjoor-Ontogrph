---
name: persian-poetry-ontograph
description: Use when running a declared Ganjoor research study — field construction, calibration, census, mapping, comparison, ablation, and release. Not for open-ended poem discovery, quoting a remembered line, or "what does Ganjoor say about X"; use persian-poetry-mcp for that.
version: 0.1.0
author: Mohammad Zare
license: MIT
metadata:
  hermes:
    tags: [persian, poetry, ontograph, research, corpus-analysis, ooo]
    related_skills: [persian-poetry-mcp]
---

# persian-poetry-ontograph

This skill orchestrates a Ganjoor Ontograph research study as specified in
`Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` (Part VII, §41–44;
Part XIII, §75–80). It does not perform interpretation itself. It translates a
researcher's conversational intent into calls against the deterministic
`ontograph` CLI, shows the plain-language result the CLI returned, and always
offers a source-return action.

## Status

This SKILL.md is a **scaffold**, not a finished skill. The Python engine
(`src/ontograph/*`, §59), the CLI (§62), and the fixture test suite (Part XI)
it shells out to do not exist yet. Do not simulate their output. If
`ontograph` is not on PATH, say so explicitly and stop — never narrate a
result the CLI did not actually produce (§78).

## Division of labor

- Discovery, quoting, "find a poem about X" → route to `persian-poetry-mcp`.
- Anything that names or implies a Seed, Object Address, Lexical Anchor,
  Field Charter, calibration, census, mapping, comparison, ablation,
  Relation-Object, or Research Release → this skill.
- A candidate lexical companion surfaced during discovery enters here only
  as a **candidate anchor** (spec §28.4) pending explicit researcher
  approval — never silently promoted to an accepted Object Address.

## Invocation pattern

```bash
ontograph field build "$STUDY" --poet hafez --category ghazal --json
ontograph object add "$STUDY" --label "آینه" --anchor "آینه" --anchor "آیینه" --json
ontograph calibrate "$STUDY" --object mirror --sample 30 --json
ontograph census "$STUDY" --object mirror --json
ontograph map recurrence "$STUDY" --object mirror --unit poem --json
ontograph companions "$STUDY" --object mirror --scale couplet --min-support 5 --json
ontograph compare "$STUDY" --field A --field B --json
ontograph ablate "$STUDY" --remove poet:hafez --rerun relation:mirror-rust --json
ontograph release "$STUDY" --version 0.1.0 --json
```

Every call:

1. runs via the Bash tool with `--json`;
2. is checked for a zero exit code and well-formed JSON before anything is
   shown to the researcher;
3. on failure (non-zero exit, missing executable, malformed JSON), reports
   the exact failure to the researcher and stops — this is the "must fail
   explicitly" rule from spec §61/§78, not a suggestion.

## Progressive disclosure (spec §43)

Every result is shown as:

1. one plain-language sentence describing the finding;
2. raw counts and denominators;
3. a source-return action (open the passages behind the number);
4. next-action choices (narrow, split, promote, compare, ablate, retain as trace);
5. an optional "How was this made?" expansion with the operation, formula,
   parameters, and limitations — never shown by default.

## Permissioning (spec §79)

Corpus-mutating and release-creating verbs (`field build`, `object add`,
`calibrate`, `release`) should be named explicitly in the project's
`.claude/settings.json` allowlist. Destructive verbs (workspace deletion,
forced object merge) must never be allowlisted; always ask.

## References

- `references/terminology.md` — the project-local vocabulary (Seed, Object
  Address, Lexical Anchor, Anchor Hit, Occurrence Assessment, Profile,
  Trace, Relation-Object, Mapping Object, Experiment, Finding, Use-Status,
  Claim Permission), kept short enough to load every turn.
- `references/operations.md` — the operation packs (spec Part V) with their
  CLI verb, required parameters, and the one-sentence result-card template
  for each.
- `references/claim-permission.md` — the Use-Status / Claim Permission
  vocabulary and when each level is appropriate, so the agent doesn't
  invent claim language beyond what the spec allows.

## Templates

- `templates/research-situation.md`
- `templates/field-charter.md`
- `templates/relation-object.md`
- `templates/research-release.md`

Each mirrors the corresponding YAML record in the spec (Part VIII) as a
fill-in-the-blank form the agent completes with the researcher rather than
inventing fields ad hoc.
