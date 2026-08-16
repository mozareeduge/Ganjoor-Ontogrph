# AGENTS.md — Playbook for AI agents working with this repository

This repository turns the Ganjoor Persian poetry corpus (ganjoor.net) into an
**agent-ready, QMD-searchable markdown database**. It is a fork of
[ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data) with an added
conversion + enrichment + search layer.

Everything an agent needs to know lives in this file. Read it before doing
anything.

---

## 1. What this repo contains

| Path | What it is |
|---|---|
| `poets/`, `index/`, `manifest.json`, `metres.json`, `languages.json`, `API.md` | Upstream Ganjoor JSON data (poets, categories, poems) — do not edit |
| `src/` | The converter + enrichment scripts (JSON → Markdown) |
| `scripts/` | Shell wrappers: fetch → convert → enrich → ingest |
| `md/` | **Generated** — the QMD-ready Markdown corpus (gitignored) |
| `.qmd/index.yml` | **Checked-in project-local QMD config** — this repo's own isolated search index |
| `queries/` | Example QMD queries (English + Persian) |

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
  - `ganjoor-fa` → `md/summaries-fa/**` — Persian خلاصه summaries, one per poem.
    Embedded. Use for Persian semantic search on summaries.
  - Every summary file's frontmatter has a `poem:` pointer to the full Persian
    poem — the bridge from any summary hit back to the real text.
- **The search index is project-local** (`.qmd/index.yml` + `.qmd/index.sqlite`).
  It never touches the machine's global QMD index or any other profile's index.

## 3. Quickstart for an agent

Requires [QMD](https://github.com/tobi/qmd) (`npm install -g @tobilu/qmd`).

```bash
# 0. Build the Markdown corpus + index (convert; enrichment optional — see below)
./scripts/build.sh

# 1. Index + embed (project-local — safe, isolated) — build.sh does this too
export QMD_TRUST_LOCAL_CONFIG=1   # allow the checked-in config + custom models (CI/agent mode)
qmd update                        # index files into .qmd/index.sqlite
qmd embed                         # generate vector embeddings (Qwen3-Embedding, multilingual)

# 2. Search
qmd query "poems about the pain of separation from the beloved at night" -c ganjoor-en
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
```

### Enrichment — pluggable LLM (any OpenAI-compatible provider)

`src/enrich.py` generates the English semantic summaries that power English
retrieval. It talks to any OpenAI-compatible `/chat/completions` endpoint:

| Env var | Default | Meaning |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | Provider base URL |
| `OPENAI_API_KEY` | — (required) | Provider key |
| `ENRICH_MODEL` | `deepseek-v4-flash` | Model id |

Examples:

```bash
# DeepSeek (cheap, tested)
OPENAI_API_KEY=sk-... ./scripts/build.sh

# OpenAI
OPENAI_BASE_URL=https://api.openai.com/v1 OPENAI_API_KEY=sk-... ENRICH_MODEL=gpt-4o-mini ./scripts/build.sh

# Any local OpenAI-compatible server (LM Studio, Ollama, vLLM, llama.cpp)
OPENAI_BASE_URL=http://localhost:1234/v1 OPENAI_API_KEY=local ENRICH_MODEL=your-model ./scripts/build.sh
```

The pipeline is resumable and idempotent: already-enriched poems are skipped
(frontmatter `summary_model`), so re-runs are cheap. Without `OPENAI_API_KEY`,
the corpus builds and indexes fine — Persian search works fully; only English
semantic retrieval is absent.

Notes:
- `QMD_TRUST_LOCAL_CONFIG=1` is required for unattended runs because the
  checked-in `.qmd/index.yml` pins custom models (Qwen3-Embedding) — by design,
  QMD gates non-default model URIs from checked-in configs.
- The embedding model is multilingual (Qwen3-Embedding-0.6B): **English and
  Persian semantic search both work**.
- On this Mac, use the working QMD binary:
  `/Users/erfanbashar/.hermes/node/bin/qmd` (the one on PATH may have an ABI mismatch).

## 4. The retrieval workflow (do this, not snippet-only answers)

```
1. qmd query "<english semantic>" -c ganjoor-en          → hit: #abc123
2. qmd get "#abc123" --full-path                          → path to a summary file
3. Read the summary file's frontmatter: poem: <relative path>
4. Read the full Persian poem at that path
5. Answer using the Persian text + metadata (poet, metre, url), citing paths
```

Never answer from snippets alone. Fetch the document, then answer.

## 5. Query patterns that work

```bash
# English semantic (the primary mode)
qmd query "poems about impermanence and the fleeting nature of joy" -c ganjoor-en -n 5

# English lexical
qmd search "wine cupbearer tavern-elder" -c ganjoor-en -n 5

# Persian exact line (BM25 — the killer feature for poetry)
qmd search "رسید مژده که ایام غم نخواهد ماند" -c ganjoor -n 3

# Persian semantic (multilingual embedder)
qmd query "شعرهایی درباره دلتنگی و شب" -c ganjoor -n 5

# Structured query — write intent/lex/vec yourself, don't rely on expansion
qmd query $'intent: Find ghazals about the pain of separation at night, not poems about wine parties.\nlex: separation night grief beloved parting\nvec: poems about the anguish of being apart from the beloved in the dark of night\nhyde: A Hafez ghazal describing the torment of separation and longing at night.' -c ganjoor-en
```

## 6. Repository rules

- **Never modify `poets/`, `index/`, or other upstream JSON** — they track
  upstream ganjoor-data. Rebuild artifacts from them instead.
- **Never commit `md/` or `.qmd/*.sqlite*`** — gitignored build artifacts.
- The Markdown corpus is distributed as a GitHub Release artifact (see
  `scripts/` and the release workflow) so agents download it instead of
  converting 132K files themselves.
- Keep machine-specific state (global QMD config, local indexes, API keys) out
  of this repo. Enrichment reads credentials from environment variables only.
- Attribution: see `NOTICE.md`. This project is a fork; upstream has no
  license — classical Persian texts are public domain, Ganjoor's AI summaries
  and compilation are theirs.

## 7. Status

- [x] Data verified (234 poets / ~132.5K poems, 2.3 GB)
- [x] QMD integration proven (two-collection architecture, multilingual embedder)
- [x] Converter `src/ganjoor2md.py` (JSON → MD) — Hafez pilot verified
- [x] Enrichment `src/enrich.py` (English summaries via OpenAI-compatible API) — Hafez pilot verified
- [ ] Full corpus build + Release pipeline (in progress)
