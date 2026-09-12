---
name: persian-poetry
description: Use when searching, quoting, or answering questions about Persian poetry from the Ganjoor corpus (Hafez, Saadi, Rumi, Ferdowsi, and 230+ other poets) via the persian-poetry MCP server — correct tool calls, collections, query types, and the summary-to-poem pointer flow.
version: 1.1.0
author: Erfan Bashar
license: MIT
metadata:
  hermes:
    tags: [persian, poetry, mcp, qmd, ganjoor, search]
    related_skills: [qmd]
---

# persian-poetry MCP — query the Ganjoor corpus

The `persian-poetry` MCP server exposes the full Ganjoor Persian poetry corpus
(234 poets, ~263K files) through a local QMD index. This skill is the
battle-tested playbook for getting the best results.

## When to use

- A user asks for a poem, a line, or poems by theme (Persian or English)
- You need to quote, find, or verify Persian poetry
- You want to answer "who said X?" or "find a poem about Y"

## The tool surface (there is NO `search` tool over MCP)

| Tool | Purpose |
|---|---|
| `query` | Hybrid search — typed searches (`lex`/`vec`/`hyde`) |
| `get` | Fetch a full document — required parameter is **`file`** (a `qmd://`-relative path or `#docid`), NOT `docid` |
| `multi_get` | Fetch multiple documents by `pattern` (glob) |
| `status` | Index overview (collections, doc counts) |

## Collections (which to query)

| Collection | Contents | Use for |
|---|---|---|
| `ganjoor` | Full Persian poems (BM25-only, never embedded) | **Exact-line search** — a line you remember |
| `ganjoor-fa` | Persian خلاصه summaries (embedded) | **Persian semantic** — theme questions in Persian |
| `ganjoor-en` | English summaries (embedded) | **English semantic** — theme questions in English. **Empty until v0.2** — queries return no results until enrichment ships. |

Rule of thumb: **exact remembered line → `ganjoor`; theme in Persian → `ganjoor-fa`;
theme in English → `ganjoor-en`.**

## Semantic search needs a model download — it often can't run

`vec`/`hyde` search and reranking require QMD to download an embedding/rerank
model from huggingface.co on first use. Many environments (cloud sandboxes,
offline machines) block that host. When it's blocked:

- `type: "lex"` (BM25) still works everywhere — it needs no model.
- **Always pass `"rerank": false`** on `query` calls. The MCP `query` tool
  defaults `rerank` to `true`, which tries to download a reranker model; on a
  blocked or CPU-only machine that call fails or hangs. `"rerank": false`
  skips it and returns the raw hybrid results.
- If `vec`/`hyde` queries return nothing or error, fall back to `lex` queries
  against `ganjoor` (BM25 always works — it's the full-text layer).

## The `query` tool — typed searches

`searches` is an array of `{type, query}` where type is:

- **`lex`** — BM25 keywords. Supports `"quoted phrases"` and `-negation`.
  Best for exact lines and known vocabulary. Needs no model.
- **`vec`** — semantic question ("poems about the pain of separation at night"). Needs an embedding model.
- **`hyde`** — a hypothetical answer passage (50-100 words) — advanced. Needs an embedding model.

Always pass `collections` (plural array), `limit`, and `"rerank": false`.

### Examples

```json
{"searches": [{"type": "lex", "query": "یوسف گم گشته بازآید به کنعان، غم مخور"}],
 "collections": ["ganjoor"], "limit": 5, "rerank": false}

{"searches": [{"type": "vec", "query": "شعرهایی درباره غم و اندوه و فراق"}],
 "collections": ["ganjoor-fa"], "limit": 5, "rerank": false}

{"searches": [{"type": "vec", "query": "poems about living sincerely for God, not for show"}],
 "collections": ["ganjoor-en"], "limit": 5, "rerank": false}
```

## The `get` tool

```json
{"file": "ganjoor/hafez/ghazal/sh255.md"}
```

or with a docid returned by a search hit:

```json
{"file": "#4cf4ad"}
```

`docid` is **not** a valid parameter name for this tool — passing it produces
an input-validation error (`file: Invalid input: expected string, received
undefined`). Always use `file`.

## The pointer flow — ALWAYS serve the real poem

Search hits from `ganjoor-fa`/`ganjoor-en` are **summary cards**, not the poem.
A hit's frontmatter carries a `poem:` pointer (relative path) to the full
Persian poem in `md/poets/`.

1. `query` → note the docid (`#abc123`) or path
2. `get` with `file` set to that docid/path → the card (for `ganjoor-en`/`ganjoor-fa` hits)
3. Follow the `poem:` pointer → the full poem file (vocalized text, خلاصه,
   English summary, metre, rhyme, url)
4. Answer from the **full poem**, never from a snippet alone

For `ganjoor` hits the hit IS the full poem — no pointer needed.

## Pitfalls (learned the hard way)

- **No `search` tool over MCP** — hybrid search lives in `query`. (The CLI has
  a separate `qmd search` command for BM25-only lookups outside MCP.)
- **`searches` items are objects** `{type, query}` — not strings.
- **`collections` is plural** — singular `collection` is silently ignored.
- **`get` takes `file`, not `docid`.**
- **No session header on HTTP** — qmd 2.8.3's MCP HTTP transport is stateless;
  there is no `mcp-session-id` to capture or echo back. The stdio transport
  (`qmd mcp`, no flags) needs no session handling at all and is the default
  for local harness configs.
- **Reranking fails offline** — always pass `"rerank": false` unless you have
  confirmed the reranker model is already downloaded.
- **Exact lines**: the corpus is vocalized (diacritics) — search the plain
  form; the «متن ساده» section handles it. Quoting poems (tafsirs, ghazals
  quoting other poets) can outrank the original — check the poet field.
- **Epic poems** (Shahnameh, Masnavi) live in large section files — a famous
  line may rank below a quoting poem; the original is still in the corpus.

## Verification

- `status` responds with collection counts.
- A `lex` query for a known Hafez line returns `hafez/ghazal/sh255.md` in the top results.
- A `vec` query (when embeddings exist and huggingface.co is reachable) in
  Persian returns on-theme poems with scores ≥ 85%.
