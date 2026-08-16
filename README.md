# persian-poetry-ai-agent-plugin

**Agent-ready Persian poetry for QMD** — the complete [Ganjoor](https://ganjoor.net/)
corpus (234 poets, ~132,500 poems) converted into a searchable, multilingual,
agent-friendly Markdown database.

Forked from [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
with an added pipeline: **JSON → Markdown → QMD index** (English semantic +
Persian semantic + Persian exact-line search, all local).

## Why

Classical Persian poetry is hard to search semantically. The Ganjoor data ships
as raw JSON with Persian summaries. This project:

1. Converts every poem to a clean, self-describing Markdown file
   (YAML frontmatter + Persian couplets + Persian summary)
2. Enriches each poem with an **English semantic summary** + topic keywords
   (OpenAI-compatible API, e.g. DeepSeek) — so retrieval works in English
   while the poetry stays Persian
3. Ships a **project-local QMD index** (`.qmd/index.yml`) with a multilingual
   embedder (Qwen3-Embedding-0.6B) — English *and* Persian semantic search
4. Is fully isolated: the index never touches your machine's global QMD state

## Quickstart

```bash
npm install -g @tobilu/qmd

# Full pipeline: convert → enrich (English summaries) → index
OPENAI_API_KEY=sk-... ./scripts/build.sh
# No API key? Conversion + indexing still work — only English semantic search is skipped.

# Search
qmd query "poems about the pain of separation at night" -c ganjoor-en
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
```

**Pluggable LLM.** Enrichment is provider-agnostic: `OPENAI_BASE_URL`,
`OPENAI_API_KEY`, and `ENRICH_MODEL` (default `deepseek-v4-flash`) work with
any OpenAI-compatible endpoint — DeepSeek, OpenAI, or a local server
(LM Studio / Ollama / vLLM). See [AGENTS.md](AGENTS.md) for the full table.

## Architecture

```
ganjoor-data JSON (poets/, index/)          ← upstream, read-only
        │  src/ganjoor2md.py (converter)
        ▼
md/poets/<slug>/…            → collection "ganjoor"     → Persian exact search (BM25, no vectors)
md/summaries-fa/<slug>/…     → collection "ganjoor-fa"  → Persian semantic search (خلاصه only)
md/summaries-en/<slug>/…     → collection "ganjoor-en"  → English semantic + BM25
        │  .qmd/index.yml (checked-in, project-local)
        ▼
qmd query/search (isolated, multilingual Qwen3-Embedding)
```

The three-collection split is deliberate: embeddings run **only on summaries**
(one language each), the full poems stay in a vector-free lexical collection
for exact-line search, and every summary file carries a `poem:` pointer back
to the real Persian poem.

## Status

- ✅ Data verified (234 poets, ~132,538 poems, 2.3 GB)
- ✅ QMD integration proven end-to-end (live test corpus, both languages)
- 🚧 Converter + enrichment (in progress)
- ⏳ Full corpus build, Release pipeline, GitHub publish

## Attribution & licensing

See [NOTICE.md](NOTICE.md). Classical Persian poetry is public domain; the
Ganjoor compilation and its AI summaries belong to the Ganjoor project.
Our code is MIT; our generated English summaries are MIT. Upstream
(ganjoor-data) declares no license — respect the source.
