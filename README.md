# Ganjoor-Ontograph

**English** | [**فارسی**](README.fa.md)

**Agent-ready Persian poetry, and a research instrument in progress.** The
complete [Ganjoor](https://ganjoor.net/) corpus — 234 poets, 132,538 poems,
2,261 categories — converted into a searchable, multilingual, agent-friendly
Markdown database, exposed to AI agents over MCP.

Third link in a fork chain: [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
→ [erfanbashar1/persian-poetry-ai-agent-plugin](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin)
→ **Ganjoor-Ontograph** (this repo). Full provenance and licensing:
[NOTICE.md](NOTICE.md).

> **Repo URL note:** the project's name is **Ganjoor-Ontograph**, but it is
> currently hosted at `github.com/mozareeduge/Ganjoor-Ontogrph` (missing the
> second "a" — a rename is planned, see `ROADMAP.md` GO-010, but hasn't
> happened). Every clone command and link below uses the spelling that
> actually works today.

## What this is for

What exists today is a conversion + indexing + retrieval pipeline: Ganjoor's
JSON export becomes agent-ready Markdown, searchable locally (exact text
always; semantic search when a model is reachable) and queryable by AI
agents over MCP. What it's *for* is bigger: a research instrument over the
Persian classical archive — cross-poet thematic exploration, structural
analysis across 132K+ poems, eventually an explicit ontology/graph layer
over poets, poems, forms, metres and themes (the "ontograph" in the name).
**That layer does not exist yet.** See [SPEC.md](SPEC.md) for the full
framing and [ROADMAP.md](ROADMAP.md) for what's actually in progress.

## Quickstart

```bash
# Prerequisite: Python 3.10+. That's it for offline/exact search.
# Semantic search additionally needs QMD 2.5+ (2.8.3 currently verified)
# and network access to huggingface.co to download an embedding model.

git clone https://github.com/mozareeduge/Ganjoor-Ontogrph.git
cd Ganjoor-Ontogrph

# 1. Check what your environment can actually do — run this first
python3 scripts/ganjoor.py doctor

# 2. Get the Markdown corpus (there is no GitHub Release on this repo yet —
#    ROADMAP GO-011 — so build it locally from the checked-in JSON):
python3 scripts/ganjoor.py corpus          # all 234 poets, ~6 min on 4 cores
python3 scripts/ganjoor.py corpus --poets hafez,saadi,rumi   # or just a subset

# 3. Index it (fast, no network, no model)
python3 scripts/ganjoor.py index

# 4. Search
python3 scripts/ganjoor.py search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
python3 scripts/ganjoor.py search "همای رحمت" --offline    # no qmd, no Node, no models at all

# 5. Expose it to agents via MCP
python3 scripts/ganjoor.py mcp             # stdio, for harness configs like .mcp.json
```

**Semantic search** (`embed`, `query`) needs to download an embedding model
from `huggingface.co` — unavailable in sandboxed/offline environments
(Claude Code web/mobile, Codex cloud, air-gapped machines). That's an
architectural constraint, not a bug. In those environments, use exact search
(`search`, `search --offline`) instead. `ganjoor-en` (English semantic) is
additionally empty until the v0.2 enrichment ships.

`build.sh`, `mcp-server.sh`, and `make setup|corpus|index|embed|all|search|mcp|demo`
still work — they're thin wrappers around `scripts/ganjoor.py` now, kept for
existing muscle memory. Run `python3 scripts/ganjoor.py --help` and
`<subcommand> --help` for the full flag reference.

## Using this from an agent harness

Any MCP-capable agent can query the `persian-poetry` server (`.mcp.json`,
stdio). Claude Code auto-detects it; other harnesses (Codex, Hermes, generic
MCP clients) need a config — see **[docs/HARNESSES.md](docs/HARNESSES.md)**
for exact setup and a per-harness capability matrix. Claude Code additionally
gets the query playbook from
[`.claude/skills/persian-poetry/SKILL.md`](.claude/skills/persian-poetry/SKILL.md).
Deep operational detail for any agent: [AGENTS.md](AGENTS.md).

## Demo

*You tell your AI agent — in Persian — that you miss someone you love. It
reaches into 700 years of Persian poetry and answers with the poem that
meets you there.*

[![Watch the demo — a real exchange with the MCP server](docs/assets/demo-poster.jpg)](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)

**[▶ Watch the demo video](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)** — a real exchange with the MCP server: a Persian message about missing a beloved → semantic search over 132,538 poems → [Fakhr al-Din Iraqi, Ghazal 106](https://ganjoor.net/eraghi/divane/ghazale/sh106). 30s. Pure Persian, fully local. (Hosted on the upstream fork's release, per `ROADMAP.md` GO-014 — this repo has no Release yet.)

## Architecture

```
Ganjoor JSON (poets/, index/)               ← upstream, read-only
        │  src/ganjoor2md.py (converter)
        ▼
md/poets/<slug>/…            → collection "ganjoor"     → Persian exact search (BM25, no vectors)
md/summaries-fa/<slug>/…     → collection "ganjoor-fa"  → Persian semantic search (خلاصه only)
md/summaries-en/<slug>/…     → collection "ganjoor-en"  → English semantic search (empty until v0.2)
        │  .qmd/index.yml (checked-in, project-local)
        ▼
qmd / scripts/ganjoor.py (search, query, mcp)
```

Embeddings run only on the two summary collections, by design — full poems
stay in a vector-free lexical collection for exact-line search, and every
summary carries a `poem:` pointer back to the real Persian text. Why: see
[docs/DECISIONS.md](docs/DECISIONS.md).

## Status

- Data verified: 234 poets, **132,538** poems, 2,261 categories, 0 errors,
  263,603 Markdown files, ~1.4 GB, ~6 min to build on 4 cores. (An older
  commit claims 132,591 poems — see `CHANGELOG.md` for that discrepancy;
  132,538 is the verified figure.)
- Cross-platform: one entrypoint (`scripts/ganjoor.py`) works identically on
  Linux/macOS/Windows (`ganjoor.cmd`/`ganjoor.ps1` shims), CI-tested on all
  three (`.github/workflows/ci.yml`).
- MCP server, Claude Code skill, multi-harness docs, and the web demo are
  live; the web demo now reports engine failures honestly instead of
  claiming "no results".
- No GitHub Release on this repo yet (`ROADMAP.md` GO-011) — build the
  corpus locally for now.
- English semantic summaries (`ganjoor-en`) not yet generated — v0.2
  (`ROADMAP.md` GO-020).
- The ontology/graph layer is a stated direction, not built — v0.3+
  (`ROADMAP.md`, exploratory).

Full task ladder: [ROADMAP.md](ROADMAP.md). What shipped, when:
[CHANGELOG.md](CHANGELOG.md).

## Attribution & licensing

See [NOTICE.md](NOTICE.md). Classical Persian poetry is public domain; the
Ganjoor compilation and its AI summaries belong to the Ganjoor project. Our
code is MIT; our generated English summaries are MIT. Upstream
(ganjoor-data) declares no license — respect the source, and thank
[Ganjoor](https://ganjoor.net) for the treasure.
