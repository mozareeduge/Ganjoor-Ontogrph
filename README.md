# persian-poetry-ai-agent-plugin

**English** | [**فارسی**](README.fa.md)

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
   (YAML frontmatter + vocalized couplets + «متن ساده» plain text + Persian خلاصه)
2. Enriches each poem with an **English semantic summary** + topic keywords
   (any OpenAI-compatible API — pluggable) — so retrieval works in English
   while the poetry stays Persian
3. Ships a **project-local QMD index** (`.qmd/index.yml`) with a multilingual
   embedder (Qwen3-Embedding-0.6B) — English *and* Persian semantic search
4. Is fully isolated: the index never touches your machine's global QMD state

## Quickstart

The corpus ships as a GitHub **Release artifact** (Markdown only — you build
the local vector index yourself, per machine).

```bash
# Prerequisites: Python 3.10+ and QMD 2.5+
npm install -g @tobilu/qmd

# 1. Get the code
git clone https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin.git
cd persian-poetry-ai-agent-plugin

# 2. Get the Markdown corpus — from the latest Release, or make with make
#    (download ganjoor-md-v*.tar.gz from the Releases page, then:)
tar -xzf ganjoor-md-v0.1.0.tar.gz -C md
#    or build from the checked-in data:  python3 src/ganjoor2md.py --input . --output md

# 3. Build the local search index (isolated, project-local)
export QMD_TRUST_LOCAL_CONFIG=1
qmd update
qmd embed -c ganjoor-fa      # Persian semantic (summary-only, by design)
qmd embed -c ganjoor-en      # English semantic (needs summaries; v0.2+)

# 4. Search — Persian exact, Persian semantic, English semantic
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
qmd query "شعرهایی درباره غم و گذر عمر" -c ganjoor-fa
qmd query "poems about the pain of separation at night" -c ganjoor-en

# 5. Expose it to agents via MCP
./scripts/mcp-server.sh --daemon   # http://localhost:8191/mcp
```

**Prefer `make`?** The [Makefile](Makefile) wraps the same steps transparently:
`make setup`, `make corpus`, `make index`, `make embed`, `make all`, `make search`,
`make mcp`.

Full step-by-step instructions, the pluggable LLM table, and the agent playbook
live in [AGENTS.md](AGENTS.md). Agents that know the `persian-poetry` MCP can
load the [persian-poetry-mcp skill](skills/persian-poetry-mcp/SKILL.md) for the
query playbook.

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
- ✅ Full corpus converted (0 errors) + Persian semantic/ exact search live
- ✅ **v0.1.0 released** — corpus artifact `ganjoor-md-v0.1.0.tar.gz`
  (Persian-complete: poems + bios + categories + خلاصه mirrors)
- ✅ MCP server, skill, and web demo shipped
- ⏳ English semantic summaries: crawling (free, ~2 weeks) → **v0.2.0** adds
  `summaries-en` to the release artifact
- ⏳ Endorsed by Ganjoor's founder — a non-technical presentation is on the way

## Attribution & licensing

See [NOTICE.md](NOTICE.md). Classical Persian poetry is public domain; the
Ganjoor compilation and its AI summaries belong to the Ganjoor project. Our
code is MIT; our generated English summaries are MIT. Upstream
(ganjoor-data) declares no license — respect the source, and thank
[Ganjoor](https://ganjoor.net) for the treasure.
