# This repository hosts two projects

Read this first — `AGENTS.md` describes only one of the two, and says
"everything an agent needs to know lives in this file," which is true for
its own project but not for the other one.

## 1. Ganjoor Ontograph — the active project (`ganjoor-ontograph/`)

An OOO-informed close/distant-reading research apparatus over the Ganjoor
Persian poetry corpus: a deterministic Python engine + CLI + Claude Code
skills for running declared research studies (field construction,
calibration, census, occurrence assessment, comparison, ablation,
release). This is a *new* project built on top of this repo, not part of
the upstream fork below.

Start here:
- `ganjoor-ontograph/README.md` — what's in the package and how it's organized.
- `ganjoor-ontograph/Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` — the full spec.
- `ganjoor-ontograph/implementation/IMPLEMENTATION_LEDGER.md` — build status (Phases 0-8; v0.1's automated ledger is complete, 134 tests passing, all 5 implementation gates green).
- `ganjoor-ontograph/implementation/BUILD_PLAN.md` — phase rationale and the v0.1 stop condition.
- `ganjoor-ontograph/implementation/HOW_TO_RUN.md` — how to resume the build loop, if there's more to build.
- `.claude/skills/persian-poetry-ontograph/` — the researcher-facing skill (uses the finished `ontograph` CLI to run studies).
- `.claude/skills/ontograph-build/` — the build-loop skill (for continuing Ontograph's own implementation).
- The `ontograph` CLI operates on this repo's own vendored corpus (`poets/`, `manifest.json` at this root) via `--corpus-root .` — no separate clone needed.

If the task at hand mentions a Seed, Object Address, Lexical Anchor, Field
Charter, calibration, census, Occurrence Assessment, Mapping Object,
comparison, ablation, Relation-Object, or Research Release — it belongs
here, not to the fork below.

## 2. `persian-poetry-ai-agent-plugin` — the upstream fork (repo root, everything else)

The original project this repo was forked from: converts the Ganjoor
corpus into an agent-ready, QMD-searchable Markdown database (MCP
retrieval server). Fully described in `AGENTS.md` — read that file for
anything about discovery, quoting, semantic search, the QMD index, or the
MCP server itself.

## Which one applies?

- "find/quote/discover a poem," "what does Ganjoor say about X," semantic
  or BM25 search → `AGENTS.md` / the upstream fork.
- Anything naming Ontograph's own vocabulary (above), or asking to
  continue/test/build/run the research apparatus → this file's section 1.
- Unsure → check `ganjoor-ontograph/implementation/IMPLEMENTATION_LEDGER.md`'s
  own status header before assuming either project's state.
