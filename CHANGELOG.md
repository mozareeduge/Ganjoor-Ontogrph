# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/) — see policy below.

## Versioning policy (data + tooling project)

This project ships both code and a generated data artifact (the Markdown
corpus + QMD index). Semver applies to the combination:

- **MAJOR** — a change that breaks compatibility with previously-built
  corpora/indexes or previously-written agent integrations: a change to the
  Persian normalization map or search-text pipeline (SPEC.md §5), a change
  to the Markdown frontmatter/heading format, or a change to the MCP tool
  surface agents depend on. Any of these **requires a full corpus rebuild
  and re-embed** — old `md/` and `.qmd/index.sqlite` are invalid afterward.
- **MINOR** — new data or capability that is additive and backward
  compatible: a new populated collection (e.g. `ganjoor-en` going from empty
  to populated in v0.2), a new command, a new supported harness.
- **PATCH** — bug fixes, doc fixes, CI/workflow changes, performance work
  that do not change the data format or the corpus's meaning.

Rule of thumb: if an agent or script that worked against version X would
silently get wrong or missing results against version Y without any code
change on its part, that is at least a MINOR bump, and MAJOR if it also
requires rebuilding data already on disk.

## [Unreleased]

Work in the current cycle, on branch `claude/quirky-meitner-x9xmhx`, not yet
released. See [ROADMAP.md](ROADMAP.md) for status tracking of each item.

### Added
- Cross-platform, stdlib-only CLI `scripts/ganjoor.py` — one entrypoint
  (`doctor`, `setup`, `corpus`, `index`, `embed`, `search`, `query`, `mcp`,
  `demo`) that wraps `qmd` and the project's own scripts consistently across
  Linux/macOS/Windows, including a pure-Python `--offline` search path that
  needs no Node, no `qmd`, and no model download.
- Windows shims `scripts/ganjoor.cmd` and `scripts/ganjoor.ps1`.
- Multi-harness MCP integration: checked-in `.mcp.json`, `CLAUDE.md` (fast
  entrypoint for Claude Code), `.claude/settings.json`, the
  `.claude/skills/persian-poetry/SKILL.md` query playbook, and
  `docs/HARNESSES.md` (per-harness setup for Claude Code CLI/Desktop/web,
  Codex CLI/cloud, Hermes/generic MCP clients, plus a capability matrix).
- `.github/workflows/ci.yml` — cross-platform smoke test (ubuntu/macos/
  windows runners): syntax-checks the Python entrypoints and builds+searches
  a tiny 2-poet corpus subset, without ever downloading a model or building
  the full corpus.
- This governance/hand-off document set: `SPEC.md`, `ROADMAP.md`,
  `CHANGELOG.md` (this file), `CONTRIBUTING.md`, `docs/DECISIONS.md`,
  `docs/HANDOFF.md`, and an extended provenance section in `NOTICE.md`.

### Changed
- `.github/workflows/release.yml` hardened (release build/packaging
  robustness).
- `scripts/build.sh`, `scripts/mcp-server.sh` adjusted alongside the new
  `scripts/ganjoor.py` entrypoint.
- `src/ganjoor2md.py`, `src/enrich.py` — Windows-safe stdout/stderr handling
  (force UTF-8 so Persian text in progress output can't crash on a cp1252
  console) and related robustness work.

### Fixed
- `scripts/web-demo.py` — search failures are now distinguished from
  genuine "no results": the UI explicitly reports an engine failure (`qmd`
  missing, index absent, model download blocked/offline) in Persian instead
  of silently showing an empty results state.

## [0.1.0] — 2026-08-16 to 2026-08-17

Reconstructed from the git history of the upstream fork
(`erfanbashar1/persian-poetry-ai-agent-plugin`), whose commits this repo's
history carries. This is the release the current README/AGENTS.md describe
as "v0.1.0 released — corpus artifact `ganjoor-md-v0.1.0.tar.gz`" — that
artifact exists on the **upstream fork's** Releases page; publishing the
equivalent on **this** repo is tracked as `GO-011` in ROADMAP.md.

### Added
- Initial import of the Ganjoor JSON corpus export (`Initial commit`;
  `manual commit - public data export`; `data: export 234 poets / 132591
  poems`).
- `src/ganjoor2md.py` converter and the three-collection QMD search layer
  (`feat: agent-ready Markdown + QMD search layer for the Ganjoor corpus`).
- MCP server script and `AGENTS.md` agent quickstart (`feat: MCP server
  script + AGENTS.md agent quickstart`).
- Release workflow building the Markdown corpus into a GitHub Release
  artifact (`ci: release workflow — build MD corpus → GitHub Release
  artifact`).
- `persian-poetry-mcp` skill and a non-technical web search demo (`feat:
  persian-poetry-mcp skill + non-technical web demo`).
- `Makefile` with `setup`/`corpus`/`index`/`embed`/`all`/`search`/`mcp`
  targets (`feat: Makefile`, part of `docs: bilingual READMEs + status
  sync; feat: Makefile; fix: scoped embed in build.sh`).
- Bilingual README (`README.md` + `README.fa.md`) and demo video, later
  moved to a Release asset for reliable inline playback (`docs: add demo
  video to README`, `docs: host demo video as release asset for inline
  playback`, `docs: show demo as linked poster frame`).

### Changed
- Installation playbook made explicit, README quickstart aligned with
  Release-artifact distribution instead of committing `md/` (`docs:
  explicit installation playbook (AGENTS.md) + README quickstart aligned
  with Release-artifact distribution`).
- MCP protocol documentation corrected from live testing against QMD 2.5.3
  (session header behavior, tool surface, typed query schema, `get`
  resource format) (`docs: MCP protocol details from live testing`).
- Persian README rewritten in a more natural voice, English technical terms
  kept for MD/index/embed/MCP (`docs(fa): humanized Persian README`).
- Release-artifact contents documented precisely: v0.1 is Persian-complete
  (poems + bios + categories + خلاصه mirrors); English summaries are v0.2
  scope (`docs: remove machine-specific qmd note; document artifact
  contents`).

### Fixed
- `scripts/build.sh` embed step scoped correctly to the summary collections
  (`fix: scoped embed in build.sh`).
- `scripts/web-demo.py` result parsing switched to line-based hit parsing
  with an explicit collection→directory map (`fix: web-demo parsing —
  line-based hit parsing + collection→dir map`).

### Notes on the data numbers
- The initial export commit message records **234 poets / 132,591 poems**.
- The later-verified, currently-cited build count (SPEC.md, ROADMAP.md,
  AGENTS.md) is **234 poets / 132,538 poems / 2,261 categories / 0 errors**.
  The discrepancy between 132,591 and 132,538 is not explained in the commit
  history available to this document set — recorded here rather than
  silently reconciled. Do not average or guess between them; treat the
  verified build count as current unless a fresh `doctor`/build run says
  otherwise.
