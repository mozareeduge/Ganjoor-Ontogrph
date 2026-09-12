# CLAUDE.md

Claude Code's entry point for this repo. Full detail lives in **[AGENTS.md](AGENTS.md)**
— read that before any non-trivial task. This file is just the fast path.

## What this is

The Ganjoor Persian poetry corpus (234 poets, ~263K files), converted to
Markdown and indexed with [QMD](https://github.com/tobi/qmd), exposed to
agents via the `persian-poetry` MCP server (see `.mcp.json`).

## The three collections

| Collection | Contents | Use for |
|---|---|---|
| `ganjoor` | Full Persian poems, bios, category indexes | Exact-line search (BM25 only — never embed this one) |
| `ganjoor-fa` | Persian خلاصه summaries | Persian theme/semantic search |
| `ganjoor-en` | English summaries | English theme/semantic search — **empty until v0.2** |

## Golden rules

- Always set `QMD_TRUST_LOCAL_CONFIG=1` before invoking `qmd` (the checked-in
  `.qmd/index.yml` pins custom models; QMD refuses it otherwise).
- Never run `qmd embed -c ganjoor` — that collection is BM25-only by design.
- Never edit `poets/`, `index/`, or other upstream JSON — regenerate from it.
- `md/` and `.qmd/*.sqlite*` are generated/gitignored — never hand-edit or commit them.
- Semantic search (`vec`/`hyde`, `qmd query`) needs a model download from
  huggingface.co. If that's blocked (cloud sandboxes, offline machines), use
  `qmd search` (BM25) or `python3 scripts/ganjoor.py search --offline` instead,
  and pass `"rerank": false` on any MCP `query` call.

## One-command entrypoint

```bash
python3 scripts/ganjoor.py doctor
```

Prints what's available in the current environment (qmd on PATH, network to
huggingface.co, corpus built, index built) and what to do next.

## Retrieval hand-off flow

1. Search a summary collection (`ganjoor-fa`/`ganjoor-en`) or `ganjoor` directly for exact lines.
2. A summary hit's frontmatter has a `poem:` pointer to the full Persian poem.
3. `get` that poem file.
4. Answer from the **full poem text**, never from a search snippet alone.

See **[docs/HARNESSES.md](docs/HARNESSES.md)** for MCP setup across other
agent harnesses (Codex, Hermes, generic MCP clients), and
**[.claude/skills/persian-poetry/SKILL.md](.claude/skills/persian-poetry/SKILL.md)**
for the detailed MCP tool-call playbook.
