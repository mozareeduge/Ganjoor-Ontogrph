---
name: persian-poetry-mcp
description: Use when querying the persian-poetry MCP server (ganjoor corpus, 132K poems) — correct tool calls, collections, query types, and the summary→poem pointer flow.
version: 1.0.0
author: Erfan Bashar
license: MIT
metadata:
  hermes:
    tags: [persian, poetry, mcp, qmd, ganjoor, search]
    related_skills: [qmd]
---

# persian-poetry MCP — query the Ganjoor corpus

The `persian-poetry` MCP server exposes the full Ganjoor Persian poetry corpus
(234 poets, ~132,500 poems) through a local QMD index. This skill is the
battle-tested playbook for getting the best results.

## When to use

- A user asks for a poem, a line, or poems by theme (Persian or English)
- You need to quote, find, or verify Persian poetry
- You want to answer "who said X?" or "find a poem about Y"

## The tool surface (there is NO `search` tool)

| Tool | Purpose |
|---|---|
| `query` | Hybrid search — typed searches (`lex`/`vec`/`hyde`) |
| `get` | Fetch a full document by docid (`#abc123`) or `qmd://` path |
| `multi_get` | Fetch multiple documents by glob |
| `status` | Index overview (collections, doc counts) |

## Collections (which to query)

| Collection | Contents | Use for |
|---|---|---|
| `ganjoor` | Full Persian poems (BM25-only) | **Exact-line search** — a line you remember |
| `ganjoor-fa` | Persian خلاصه summaries (embedded) | **Persian semantic** — theme questions in Persian |
| `ganjoor-en` | English summaries (embedded) | **English semantic** — theme questions in English |

Rule of thumb: **exact remembered line → `ganjoor`; theme in Persian → `ganjoor-fa`;
theme in English → `ganjoor-en`.**

## The `query` tool — typed searches

`searches` is an array of `{type, query}` where type is:

- **`lex`** — BM25 keywords. Supports `"quoted phrases"` and `-negation`.
  Best for exact lines and known vocabulary.
- **`vec`** — semantic question ("poems about the pain of separation at night").
- **`hyde`** — a hypothetical answer passage (50-100 words) — advanced.

Always pass `collections` (plural array) and `limit`.

### Examples

```json
{"searches": [{"type": "lex", "query": "یوسف گم گشته بازآید به کنعان، غم مخور"}],
 "collections": ["ganjoor"], "limit": 5}

{"searches": [{"type": "vec", "query": "شعرهایی درباره غم و اندوه و فراق"}],
 "collections": ["ganjoor-fa"], "limit": 5}

{"searches": [{"type": "vec", "query": "poems about living sincerely for God, not for show"}],
 "collections": ["ganjoor-en"], "limit": 5}
```

## The pointer flow — ALWAYS serve the real poem

Search hits are **summary cards**, not the poem. A hit's frontmatter carries a
`poem:` pointer (relative path) to the full Persian poem in `md/poets/`.

1. `query` → note the docid (`#abc123`) or `qmd://` path
2. `get` with that docid/path → the card (for `ganjoor-en`/`ganjoor-fa` hits)
3. Follow the `poem:` pointer → the full poem file (vocalized text, خلاصه,
   English summary, metre, rhyme, url)
4. Answer from the **full poem**, never from a snippet alone

For `ganjoor` hits the hit IS the full poem — no pointer needed.

## Pitfalls (learned the hard way)

- **No `search` tool** — hybrid search lives in `query`.
- **`searches` items are objects** `{type, query}` — not strings.
- **`collections` is plural** — singular `collection` is silently ignored.
- **Session protocol** — the server speaks MCP 2025-11-25: capture the
  `mcp-session-id` response header from `initialize`, send it back as
  `Mcp-Session-Id` on every later request, then send `notifications/initialized`.
- **Exact lines**: the corpus is vocalized (diacritics) — search the plain
  form; the «متن ساده» section handles it. Quoting poems (tafsirs, ghazals
  quoting other poets) can outrank the original — check the poet field.
- **Epic poems** (Shahnameh, Masnavi) live in large section files — a famous
  line may rank below a quoting poem; the original is still in the corpus.

## Verification

- `status` responds with collection counts
- A `lex` query for a known Hafez line returns `hafez/ghazal/sh255.md` in the top results
- A `vec` query in Persian returns on-theme poems with scores ≥ 85%
