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

The corpus ships as a GitHub **Release artifact** (Markdown only — you build
the local vector index yourself, per machine).

```bash
npm install -g @tobilu/qmd

# 1. Get the code
git clone https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin.git
cd persian-poetry-ai-agent-plugin

# 2. Get the Markdown corpus (from Releases), or build it: python3 src/ganjoor2md.py --input . --output md
tar -xzf ganjoor-md-v0.1.0.tar.gz -C md

# 3. Build the local search index (isolated, project-local)
export QMD_TRUST_LOCAL_CONFIG=1
qmd update && qmd embed

# 4. Search — English semantic, Persian semantic, Persian exact
qmd query "poems about the pain of separation at night" -c ganjoor-en
qmd query "شعرهایی درباره غم و گذر عمر" -c ganjoor-fa
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor

# 5. Expose it to agents via MCP
./scripts/mcp-server.sh --daemon   # http://localhost:8191/mcp
```

Full step-by-step instructions, the pluggable LLM table, and the agent playbook
live in [AGENTS.md](AGENTS.md).

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
