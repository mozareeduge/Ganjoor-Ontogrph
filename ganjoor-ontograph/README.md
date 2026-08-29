# Ganjoor Ontograph

A research-apparatus specification for OOO-informed close/distant reading over
the [Ganjoor](https://ganjoor.net/) Persian poetry corpus, plus a starting
Claude Code skill scaffold for implementing it.

- `Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` — the project
  specification (drop-in revision of v2.2.0; see `EVALUATION.md` for the diff
  and why each change was made).
- `EVALUATION.md` — the review that produced v2.3.0: a verified factual
  correction, real gaps closed, and the new Claude Code runtime binding
  (Part XIII of the spec).
- `USER_JOURNEY.md` — the concrete experience flow: how a research session
  actually starts, branches, and ends, with real example outputs at every
  step. This is the UX target the build plan below is built against.
- `fixtures/mini-ganjoor/` — a small, schema-accurate, hand-verified
  synthetic corpus with known ground truth, used by every automated test
  so the build never depends on cloning the real multi-GB corpora.
- `implementation/` — the actual build package: `BUILD_PLAN.md` (phases,
  rationale, engineering defaults), `IMPLEMENTATION_LEDGER.md` (the exact
  task-by-task backlog), and `HOW_TO_RUN.md` (how to kick off the build
  loop from a fresh Claude Code session).
- `../.claude/skills/persian-poetry-ontograph/` — the researcher-facing
  skill scaffold named in the spec's Part XIII (uses the finished engine).
- `../.claude/skills/ontograph-build/` — the build-loop skill (builds the
  engine in the first place). Different audience, different job: one is
  for using the apparatus, the other is for finishing it.

This is the project's dedicated home: `mozareeduge/Ganjoor-Ontogrph`, a fork
of `erfanbashar1/persian-poetry-ai-agent-plugin` (which itself vendors the
`ganjoor/ganjoor-data` corpus at its repository root — `poets/`, `index/`,
`manifest.json`). Everything above the fork notice in the repository's root
`README.md` is that original upstream project, unmodified; everything under
this `ganjoor-ontograph/` directory and `.claude/skills/` is the Ontograph
addition. An earlier draft of this package briefly lived in a separate
scratch repository (`mozareeduge/test-experiment-toolset`, PR #1) before this
repository existed — this directory supersedes that copy.

Related repositories referenced by the spec:

- `ganjoor/ganjoor-data` — the pinned documentary corpus (vendored at this
  repo's root via the fork chain above; a workspace should still record the
  exact upstream commit it was vendored from, not just "the repo root," per
  spec §56).
- `erfanbashar1/persian-poetry-ai-agent-plugin` — this repository's own fork
  parent; the existing Markdown/QMD/MCP retrieval layer this spec builds
  alongside, not on top of (spec §25).
