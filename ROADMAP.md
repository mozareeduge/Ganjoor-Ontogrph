# ROADMAP — Ganjoor-Ontograph

Status-bearing task ladder. Each item: stable ID, one-line statement,
status, dependency, acceptance criterion where relevant. See
[SPEC.md](SPEC.md) for what the system is, [docs/DECISIONS.md](docs/DECISIONS.md)
for why, [CHANGELOG.md](CHANGELOG.md) for what has actually shipped in each
release.

Status values: `done`, `in-progress`, `blocked`, `planned`. `exploratory`
marks speculative future-direction items that are not committed scope.

Last reviewed: 2026-09-12. When you change an item's status, update this
line and add a CHANGELOG entry.

## Milestone v0.1 — foundation (search/MCP over the Persian corpus)

| ID | Statement | Status | Dependency | Acceptance criterion |
|---|---|---|---|---|
| GO-001 | Convert full Ganjoor JSON corpus to agent-ready Markdown (`src/ganjoor2md.py`) | done | — | 234 poets / 132,538 poems / 2,261 categories / 0 errors, verified Windows-safe (no invalid chars, no reserved names, longest path 66 chars, no case collisions) |
| GO-002 | Three-collection QMD architecture (`ganjoor` BM25-only, `ganjoor-fa`/`ganjoor-en` embedded summaries) | done | GO-001 | `.qmd/index.yml` checked in; `qmd update` + `qmd embed -c ganjoor-fa` succeed on a clean checkout |
| GO-003 | Persian summary quality gate + AI-prefix stripping | done | GO-001 | `clean_ai_summary`: drops summaries < 100 chars, strips «هوش مصنوعی:» |
| GO-004 | MCP server wired to the project-local index | done | GO-002 | `qmd mcp` (stdio) answers `query`/`get`/`multi_get`/`status` against this repo's `.qmd/index.sqlite` only |
| GO-005 | Release-artifact distribution of the Markdown corpus (no `md/` committed) | done (v0.1.0, upstream fork repo) / **blocked** (this repo) | GO-001, CI release workflow | A `ganjoor-md-v*.tar.gz` exists on **this repo's** Releases page; today it only exists on the upstream fork (`erfanbashar1/persian-poetry-ai-agent-plugin`) |
| GO-006 | Cross-platform single entrypoint (`scripts/ganjoor.py`): doctor/setup/corpus/index/embed/search/query/mcp/demo, stdlib-only, offline search path | done (this cycle) | GO-001, GO-002 | Runs on Linux/macOS/Windows with only Python 3.10+; `--offline` search needs no Node/qmd/model |
| GO-007 | Windows shims (`ganjoor.cmd`, `ganjoor.ps1`) | done (this cycle) | GO-006 | Present in `scripts/`; **not yet verified on a real Windows machine** — CI covers `windows-latest` runners only |
| GO-008 | Multi-harness MCP integration docs + configs (`.mcp.json`, `CLAUDE.md`, `.claude/settings.json`, `.claude/skills/persian-poetry/SKILL.md`, `docs/HARNESSES.md`) | done (this cycle) | GO-004 | Covers Claude Code (CLI/Desktop/web-mobile), Codex (CLI/cloud), Hermes/generic MCP, with a capability matrix and troubleshooting table |
| GO-009 | CI hardening: cross-platform smoke test (subset corpus build + offline search, no model download) | done (this cycle) | GO-006 | `.github/workflows/ci.yml` matrix over ubuntu/macos/windows |
| GO-010 | Rename repository `Ganjoor-Ontogrph` → `Ganjoor-Ontograph` | planned | none (GitHub Settings action) | Repo renamed; `git remote -v` and every doc URL updated to the new spelling in one pass; old URL redirects (GitHub does this automatically) |
| GO-011 | First GitHub Release published on **this** repo (`mozareeduge/Ganjoor-Ontogrph`) | planned | GO-005, GO-009 | A tagged release with a `ganjoor-md-v0.1.x.tar.gz` asset exists on this repo; README download instructions resolve without 404 |
| GO-012 | Governance/hand-off kit: SPEC, ROADMAP, CHANGELOG, CONTRIBUTING, DECISIONS, HANDOFF, NOTICE lineage extension | done (this cycle — this document set) | none | This file set exists and cross-links correctly |
| GO-013 | Verify Windows shims + full pipeline on a real (non-CI) Windows machine | planned | GO-007 | Owner or an agent with Windows access runs `ganjoor.cmd doctor`/`setup`/`corpus`/`index` end to end and reports pass/fail |
| GO-014 | Demo video / Release asset links resolve on this repo | blocked | GO-011 | README demo link currently points at the upstream fork's release asset; needs re-hosting once this repo has releases |

## Milestone v0.2 — English semantic layer

| ID | Statement | Status | Dependency | Acceptance criterion |
|---|---|---|---|---|
| GO-020 | Run `src/enrich.py` over the full corpus to populate `md/summaries-en/**` | planned | GO-001, an LLM API key (any OpenAI-compatible provider) | `ganjoor-en` collection non-empty; `topics_en`/`summary_model`/`summary_date` populated in poem frontmatter |
| GO-021 | Re-embed `ganjoor-en` after enrichment | planned | GO-020 | `qmd embed -c ganjoor-en` completes; `qmd query -c ganjoor-en` returns relevant English-semantic hits |
| GO-022 | v0.2 Release artifact including `summaries-en/` | planned | GO-020, GO-011 | Release asset tarball contains non-empty `md/summaries-en/` |
| GO-023 | Update docs (README, HARNESSES capability matrix) once English semantic search is live | planned | GO-021 | "empty until v0.2" language removed where it no longer applies |

## Milestone v0.3+ — toward the ontograph (exploratory)

Everything below is a stated future direction, **not committed scope**. No
part of the current codebase implements any of this. Treat as brainstorming
inputs for later planning, not as tasks to start pulling on unprompted.

| ID | Statement | Status | Notes |
|---|---|---|---|
| GO-030 | Entity extraction over poems/summaries (poets, places, themes, motifs, cross-references) | exploratory | Would need a schema decision and almost certainly LLM-assisted extraction at 132K-poem scale — cost/quality tradeoffs unexamined |
| GO-031 | Graph/ontology layer connecting poets ↔ poems ↔ themes ↔ metres ↔ historical period | exploratory | Storage technology unchosen (property graph? RDF? just richer frontmatter + a query layer over QMD?) — no decision made, see DECISIONS.md for related but distinct decisions already made |
| GO-032 | Cross-poet thematic exploration tooling (e.g. "who else wrote about X the way Hafez did") | exploratory | Depends on GO-020/21 (English semantic layer) at minimum; graph layer likely improves it further |
| GO-033 | Ganjoor founder outreach / non-technical presentation | planned (owner-stated intent) | Not a code task — a relationship/communications step mentioned in prior README status, unrelated to the technical roadmap above |

## How to use this file

- When you finish work, flip the relevant row's status and, if you completed
  something not yet listed, add a new row with the next free ID in the
  right milestone block.
- `blocked` rows must name what they are blocked on in the Dependency
  column.
- Do not delete completed rows — they are the project's memory of what was
  decided and finished. Historical accuracy here is worth more than tidiness.
- Cross-check against [CHANGELOG.md](CHANGELOG.md) `[Unreleased]` before
  marking anything `done` — if it isn't in the changelog yet, add it there
  too.
