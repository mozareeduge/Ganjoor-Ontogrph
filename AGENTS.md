# AGENTS.md — Playbook for AI agents working with this repository

This repository turns the Ganjoor Persian poetry corpus (ganjoor.net) into an
**agent-ready, QMD-searchable markdown database**, exposed over MCP. It is
the third link in a fork chain — see [NOTICE.md](NOTICE.md) for full
provenance: [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
→ [erfanbashar1/persian-poetry-ai-agent-plugin](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin)
→ **Ganjoor-Ontograph** (this repo).

Everything an agent needs for day-to-day operation lives in this file. For a
cold start on this repo, read in this order: **[docs/HANDOFF.md](docs/HANDOFF.md)**
(the start-here protocol) → **[SPEC.md](SPEC.md)** (what the system is and
its invariants) → **[ROADMAP.md](ROADMAP.md)** (status) → this file
(operational commands). If you are Claude Code specifically, `CLAUDE.md` is
a fast-path pointer back to this file. If your task involves MCP or you're
unsure what your environment can do, read **[docs/HARNESSES.md](docs/HARNESSES.md)**.

---

## 1. What this repo contains

| Path | What it is |
|---|---|
| `poets/`, `index/`, `manifest.json`, `metres.json`, `languages.json`, `API.md` | Upstream Ganjoor JSON data (poets, categories, poems) — do not edit |
| `src/` | The converter + enrichment scripts (JSON → Markdown) |
| `scripts/ganjoor.py` | **Primary cross-platform entrypoint** — stdlib-only, identical on Linux/macOS/Windows |
| `scripts/ganjoor.cmd`, `scripts/ganjoor.ps1` | Windows shims for `ganjoor.py` |
| `scripts/build.sh`, `scripts/mcp-server.sh` | Thin shell wrappers around `ganjoor.py`, kept for existing muscle memory |
| `md/` | **Generated** — the QMD-ready Markdown corpus (gitignored) |
| `.qmd/index.yml` | **Checked-in project-local QMD config** — this repo's own isolated search index |
| `queries/` | Example QMD queries (English + Persian) |
| `.mcp.json`, `.claude/skills/persian-poetry/SKILL.md` | Claude Code MCP server config + query playbook |
| `docs/HARNESSES.md` | Per-harness MCP setup (Codex, Hermes, Claude Code web/mobile) + capability matrix |
| `SPEC.md`, `ROADMAP.md`, `CHANGELOG.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md` | Governance/hand-off document set — what the system is, what's done, why, and how to pick this up cold |

## 2. The big idea

- **Semantic retrieval happens in English**, Persian content stays Persian.
- Each poem Markdown document contains (in order): YAML frontmatter (id, poet,
  format, metre, rhyme, url, topics_en, summary_model...), the **vocalized**
  couplets (canonical text), a `## متن ساده` section (unvocalized, ZWNJ
  normalized — this is what matches how people actually type Persian),
  a `## خلاصه` Persian summary (when Ganjoor's summary passes the quality
  gate), and a `## Summary (EN)` English semantic summary (when enriched).
- The corpus has **three collections** (strict "summary-only embedding" model):
  - `ganjoor` → `md/poets/**` — full Persian poems, poet bios, category indexes.
    **BM25 only (no vectors)** — this is the lexical layer: Persian exact-line search.
  - `ganjoor-en` → `md/summaries-en/**` — English semantic summaries, one per
    poem. Embedded. Use for English semantic search and English BM25.
    **Empty until v0.2 enrichment ships** (`ROADMAP.md` GO-020).
  - `ganjoor-fa` → `md/summaries-fa/**` — Persian خلاصه summaries, one per poem.
    Embedded. Use for Persian semantic search on summaries.
  - Every summary file's frontmatter has a `poem:` pointer to the full Persian
    poem — the bridge from any summary hit back to the real text.
- **The search index is project-local** (`.qmd/index.yml` + `.qmd/index.sqlite`).
  It never touches the machine's global QMD index or any other profile's index.
- **Never embed `ganjoor`.** Rationale: `SPEC.md` §4 and `docs/DECISIONS.md` ADR-001.

## 3. Installation & operation

There is no magic installer. Everything needed is in this repo. **This repo
has no GitHub Release yet** (`ROADMAP.md` GO-011) — build the corpus locally
rather than expecting a downloadable tarball.

### Step 0 — Prerequisites

- Python 3.10+ (`python3 --version`) — this alone gets you exact/offline search.
- For semantic search: [QMD](https://github.com/tobi/qmd) 2.5+ on `PATH`
  (`npm install -g @tobilu/qmd`, then `qmd --version`). QMD **2.8.3** is the
  version currently published and verified against this repo's docs.
- ~2 GB free disk for the data, ~4 GB for the built corpus + index.
- Run `python3 scripts/ganjoor.py doctor` first, always — it reports exactly
  what's available (Python, Node, qmd, corpus, index, huggingface.co
  reachability) and what to do next. Pass `--strict` to make it exit
  non-zero when nothing works (useful in scripts/CI).

### Step 1 — Get the code and the corpus

```bash
git clone https://github.com/mozareeduge/Ganjoor-Ontogrph.git
cd Ganjoor-Ontogrph
```

Build `md/` (the Markdown corpus) with the primary entrypoint:

```bash
python3 scripts/ganjoor.py corpus                          # all 234 poets (~6 min on 4 cores)
python3 scripts/ganjoor.py corpus --poets hafez,saadi,rumi  # a subset — cheaper for a sandbox/CI run
python3 scripts/ganjoor.py corpus --jobs 4                  # control worker count
python3 scripts/ganjoor.py corpus --force                   # reconvert even if md/ exists
```

If a release tarball ever exists (this repo's own, once GO-011 lands, or the
upstream fork's today), extract it **through the same command** rather than
raw `tar` — `md/` is gitignored and does not exist on a fresh clone, and
`tar -C md ...` on a missing directory fails (`tar` does not create `-C`'s
target):

```bash
python3 scripts/ganjoor.py corpus --tar ganjoor-md-v0.1.0.tar.gz
```

(Equivalent to `mkdir -p md && tar -xzf ganjoor-md-v0.1.0.tar.gz -C md` — the
tarball's own top level is `poets/`, `summaries-fa/`, etc., packed with
`tar -C md .`, so it unpacks straight into `md/`.)

> **Artifact/corpus contents:** Persian is complete — full poems, poet bios,
> category indexes, and Persian خلاصه mirrors. `summaries-en` (and therefore
> the `ganjoor-en` collection) stays empty until v0.2 enrichment
> (`src/enrich.py`) has been run; until then only `ganjoor` / `ganjoor-fa`
> searches return results.

### Step 2 — Build the local search index

The index is project-local and isolated (`.qmd/index.yml` is checked in):

```bash
python3 scripts/ganjoor.py index          # BM25 + metadata — fast, no network, no model
python3 scripts/ganjoor.py embed          # vectors for ganjoor-fa AND ganjoor-en (both, by default)
python3 scripts/ganjoor.py embed -c ganjoor-fa   # or scope to one summary collection
```

`ganjoor.py index`/`embed` set `QMD_TRUST_LOCAL_CONFIG=1` for you (the
checked-in `.qmd/index.yml` pins a custom embedding model; QMD gates
non-default model URIs from checked-in configs otherwise). If you call `qmd`
directly instead, export it yourself first.

**`embed` is scoped to `{ganjoor-fa, ganjoor-en}` by design — never
`ganjoor`.** The first `embed` downloads the multilingual Qwen3-Embedding
model (~640 MB) from `huggingface.co`. `index` is fast; `embed` takes minutes
to hours depending on hardware, runs locally, and is resumable.

> **Do not follow QMD's own post-`update` advice literally.** After `qmd
> update`, QMD prints something like `Run 'qmd embed' to update embeddings
> (263603 unique hashes need vectors)`, and `qmd status` reports all 263,603
> docs as needing embedding. That count includes the 135,033-document
> `ganjoor` collection, which this project **deliberately never embeds**
> (SPEC.md §4). Always scope embedding with `-c ganjoor-fa` / `-c ganjoor-en`
> (or just use `python3 scripts/ganjoor.py embed`, which already does this)
> — do not run a bare `qmd embed` with no collection filter.

### Step 3 — Search

```bash
# Exact (BM25) — no model, no network, always available once indexed
python3 scripts/ganjoor.py search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor -n 3

# Pure-Python fallback — no qmd, no Node, no model, at all
python3 scripts/ganjoor.py search "همای رحمت" --offline

# Semantic (needs embeddings + a reachable huggingface.co at embed time)
python3 scripts/ganjoor.py query "poems about the pain of separation at night" -c ganjoor-en
python3 scripts/ganjoor.py query "شعرهایی درباره غم و گذر عمر" -c ganjoor-fa
```

`--offline` cannot run `query` (semantic) at all — it is exact-match only,
over the Markdown files directly, with no `qmd`/Node/model dependency.

### Step 4 — Expose it to agents via MCP

```bash
python3 scripts/ganjoor.py mcp                        # stdio (default — what .mcp.json uses)
python3 scripts/ganjoor.py mcp --http --port 8191      # HTTP, for clients that need it
python3 scripts/ganjoor.py mcp --http --port 8191 --stop  # stop the HTTP daemon
```

`./scripts/mcp-server.sh --daemon` / `./scripts/mcp-server.sh stop` remain
equivalent thin wrappers over the HTTP form. Any MCP-capable agent can query
the corpus. For per-harness setup (Claude Code CLI/Desktop/web, Codex,
Hermes, generic MCP clients) and a capability matrix, see
**[docs/HARNESSES.md](docs/HARNESSES.md)**.

**Protocol notes (verified against qmd 2.8.3):**

- Tool surface: **`query`**, **`get`**, **`multi_get`**, **`status`**. (There
  is no `search` tool over MCP — hybrid search lives in `query`.)
- The HTTP transport is **stateless** — `initialize` does not return an
  `mcp-session-id` header. Do not implement session-id capture/echo logic
  against this version; send each request independently. The stdio
  transport needs no session handling at all and is the default.
- The `get` tool's document parameter is **`file`** (a `qmd://`-relative path
  or `#docid`), **not** `docid` — passing `docid` produces an
  input-validation error.
- The `query` tool defaults `rerank` to `true`, which triggers a reranker
  model download on first use. In offline/CPU-only/sandboxed environments
  this makes **every** `query` call fail or hang, including plain `lex`
  (BM25) searches — always pass `"rerank": false` explicitly unless you have
  confirmed the reranker model is already cached locally.

**`query` tool** — typed searches (each item is `{type: "lex"|"vec"|"hyde", query}`),
`collections` is a plural array, plus `limit`, `minScore`, `candidateLimit`,
`intent`, `rerank`:

```json
// Persian exact line (lex) — works everywhere, no model needed
{"searches": [{"type": "lex", "query": "یوسف گم گشته بازآید به کنعان، غم مخور"}],
 "collections": ["ganjoor"], "limit": 5, "rerank": false}

// English semantic (vec) — needs a reachable embedding model
{"searches": [{"type": "vec", "query": "poems about the pain of separation at night"}],
 "collections": ["ganjoor-en"], "limit": 5, "rerank": false}

// Persian semantic (vec)
{"searches": [{"type": "vec", "query": "شعرهایی درباره غم و گذر عمر"}],
 "collections": ["ganjoor-fa"], "limit": 5, "rerank": false}
```

**`get` tool** — fetch a document by `file` (a docid like `#e339c3` or a
`qmd://` path like `qmd://ganjoor/hafez/ghazal/sh255.md`); content comes back
as a `resource` item with `text/markdown`. Follow the summary's `poem:`
pointer to the full poem and answer from it — never from snippets alone.

### English enrichment — pluggable LLM (optional, for English semantic search)

The English summaries that power `ganjoor-en` semantic search are generated by
`src/enrich.py` against any OpenAI-compatible endpoint:

| Env var | Default | Meaning |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | Provider base URL |
| `OPENAI_API_KEY` | — (required) | Provider key |
| `ENRICH_MODEL` | `deepseek-v4-flash` | Model id |

```bash
# DeepSeek (cheap, tested)
OPENAI_API_KEY=sk-... python3 src/enrich.py --md md --workers 8

# OpenAI
OPENAI_BASE_URL=https://api.openai.com/v1 OPENAI_API_KEY=sk-... ENRICH_MODEL=gpt-4o-mini python3 src/enrich.py --md md

# Any local OpenAI-compatible server (LM Studio, Ollama, vLLM, llama.cpp)
OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=local ENRICH_MODEL=your-model python3 src/enrich.py --md md
```

The pipeline is resumable and idempotent: already-enriched poems are skipped
(frontmatter `summary_model`), so re-runs are cheap. Without `OPENAI_API_KEY`,
the corpus still builds and indexes fine — Persian search works fully; only
English semantic retrieval is absent.

## 4. Environment capabilities — reason about this before running anything

Not every environment has the same capabilities. Two independent axes:

| Axis | Needs | Unavailable when |
|---|---|---|
| Lexical (BM25) search | `qmd` on PATH + built index, or nothing at all (`ganjoor.py search --offline`) | Never — always available once the corpus/index exists |
| Semantic (vector) search | Network access to `huggingface.co` to download the embedding/reranker model (~640 MB, once per machine) | Sandboxed/cloud harness environments (Claude Code web/mobile, Codex cloud) block this host — a **permanent architectural constraint**, not a bug |

In a sandboxed cloud environment: `embed`, `query` with `vec`/`hyde` search
types, and MCP `query` calls with default `rerank: true` will fail or hang.
Use `search` (BM25), `search --offline`, and pass `"rerank": false` on MCP
`query` calls. `ganjoor-en` is empty regardless of environment until v0.2
enrichment has been run somewhere with an LLM API key — a data gap, not a
capability gap. Full detail: `SPEC.md` §7, `docs/HARNESSES.md`. One-command
check for the current environment: `python3 scripts/ganjoor.py doctor`.

## 5. The retrieval workflow (do this, not snippet-only answers)

```
1. query "<search>" -c ganjoor-en (or ganjoor-fa / ganjoor for exact)  → hit: #abc123 or a file path
2. get that document (MCP: {"file": "#abc123"}; CLI: qmd get "#abc123" --full-path)
3. Read the summary file's frontmatter: poem: <relative path>  (skip if the hit is already a full poem, i.e. from `ganjoor`)
4. Read the full Persian poem at that path
5. Answer using the Persian text + metadata (poet, metre, url), citing paths
```

Never answer from snippets alone. Fetch the document, then answer.

## 6. Query patterns that work

```bash
# English semantic (needs a reachable embedding model)
python3 scripts/ganjoor.py query "poems about impermanence and the fleeting nature of joy" -c ganjoor-en -n 5

# Persian exact line (BM25 — the killer feature for poetry, works everywhere)
python3 scripts/ganjoor.py search "رسید مژده که ایام غم نخواهد ماند" -c ganjoor -n 3

# Persian semantic (needs a reachable embedding model)
python3 scripts/ganjoor.py query "شعرهایی درباره دلتنگی و شب" -c ganjoor-fa -n 5

# Pure-Python offline fallback — exact match only, no model/qmd/Node
python3 scripts/ganjoor.py search "وجود عشق" --offline
```

For the raw `qmd query` structured-query form (writing `intent`/`lex`/`vec`/`hyde`
yourself instead of relying on expansion) and the MCP JSON call shapes, see
**[.claude/skills/persian-poetry/SKILL.md](.claude/skills/persian-poetry/SKILL.md)**
— it is the maintained, tool-tested playbook and takes precedence over
recreating those examples here.

## 7. Repository rules

- **Never modify `poets/`, `index/`, or other upstream JSON** — they track
  upstream ganjoor-data. Rebuild artifacts from them instead.
- **Never commit `md/` or `.qmd/*.sqlite*`** — gitignored build artifacts.
- Don't build the full ~2 GB corpus or run a full `qmd update`/`embed` in a
  disk- or time-constrained sandbox — use `corpus --poets <subset>`.
- Keep machine-specific state (global QMD config, local indexes, API keys) out
  of this repo. Enrichment reads credentials from environment variables only.
- Do not describe graph/ontology capabilities as present — they are the
  stated long-term direction (`SPEC.md` §1, §6; `ROADMAP.md` v0.3+,
  exploratory), not shipped.
- Attribution: see `NOTICE.md`. This project is a fork; upstream has no
  license — classical Persian texts are public domain, Ganjoor's AI summaries
  and compilation are theirs.
- Changing the repo: read [CONTRIBUTING.md](CONTRIBUTING.md) first (branching,
  commit style, what needs a CHANGELOG/ROADMAP update).

## 8. Status

See **[ROADMAP.md](ROADMAP.md)** for the authoritative, ID-tracked task
ladder and **[CHANGELOG.md](CHANGELOG.md)** for what has shipped in each
release — both are kept current there rather than duplicated here. Headline
facts, verified:

- 234 poets / **132,538** poems / 2,261 categories / 0 conversion errors /
  263,603 Markdown files / ~1.4 GB / ~6 min to build on 4 cores. (An older
  commit message claims 132,591 poems; `CHANGELOG.md` flags the discrepancy —
  132,538 is the verified figure, not silently reconciled.)
- Cross-platform entrypoint (`scripts/ganjoor.py`) + Windows shims, CI-tested
  on Linux/macOS/Windows.
- No GitHub Release on this repo yet — build the corpus locally.
- `ganjoor-en` empty until v0.2 enrichment runs.
- No graph/ontology layer yet.
