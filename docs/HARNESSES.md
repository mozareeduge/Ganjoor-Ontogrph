# Running this repo's MCP server across agent harnesses

This repo ships a `persian-poetry` MCP server backed by the project-local QMD
index (`.qmd/index.yml`). It works with any standard MCP client. This page
covers per-harness setup, gotchas, and a capability matrix so you know what
to expect before you start.

All configs below assume you are in the repo root, `md/` has been built (or
unpacked from a release), and `qmd update` has already indexed it (see
`AGENTS.md` for corpus/index setup — do **not** rebuild either from scratch,
they are large).

---

## Claude Code (CLI, macOS/Linux)

The repo's checked-in **`.mcp.json`** is auto-detected by Claude Code when you
open the project:

```json
{
  "mcpServers": {
    "persian-poetry": {
      "command": "qmd",
      "args": ["mcp"],
      "env": { "QMD_TRUST_LOCAL_CONFIG": "1" }
    }
  }
}
```

On first launch Claude Code will prompt to approve this project-scoped
server — approve it once and it's remembered for the project.

**Manual alternative** (adds the same server via the CLI instead of relying
on `.mcp.json` discovery):

```bash
claude mcp add persian-poetry -e QMD_TRUST_LOCAL_CONFIG=1 -- qmd mcp
```

## Claude Code Desktop on Windows

Same `.mcp.json` shape, but with a critical gotcha: **an npm-global install of
`qmd` on Windows is a `qmd.cmd` shim**, not an executable directly runnable as
`"command": "qmd"` in some launch contexts. If the bare form fails to start,
route it through `cmd /c` explicitly:

```json
{
  "mcpServers": {
    "persian-poetry": {
      "command": "cmd",
      "args": ["/c", "qmd", "mcp"],
      "env": { "QMD_TRUST_LOCAL_CONFIG": "1" }
    }
  }
}
```

If you need an absolute path to the shim instead of relying on `PATH`, quote
it as a JSON string with **escaped backslashes** (a single `\` in a Windows
path must be written as `\\` inside JSON):

```json
{
  "mcpServers": {
    "persian-poetry": {
      "command": "cmd",
      "args": ["/c", "C:\\Users\\you\\AppData\\Roaming\\npm\\qmd.cmd", "mcp"],
      "env": { "QMD_TRUST_LOCAL_CONFIG": "1" }
    }
  }
}
```

## Claude Code web / mobile (cloud sandbox)

Cloud sandboxes running Claude Code have **no network access to
huggingface.co**, so `qmd embed`, `qmd query`, and `qmd vsearch` (anything
needing an embedding or reranker model) cannot run. Semantic search is not
available there — plan for lexical-only:

```bash
# BM25 lexical search — no model, no network
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor -n 5

# Pure-Python fallback, no qmd/Node/model dependency at all
python3 scripts/ganjoor.py search "همای رحمت" --offline
```

Also avoid asking a cloud container to build or convert the full ~2 GB corpus.
If you only need a few poets for a session, build a subset instead of the
full `md/`:

```bash
python3 scripts/ganjoor.py corpus --poets hafez,saadi,rumi
```

MCP still works in these sandboxes over stdio (`qmd mcp` uses no network by
itself) — only the model-backed search *types* (`vec`/`hyde`) and reranking
are unavailable. Always pass `"rerank": false` on `query` calls here (see
Troubleshooting below).

## Codex (CLI / IDE)

Codex reads `AGENTS.md` natively — no extra pointer file needed. Add the MCP
server to `~/.codex/config.toml`:

```toml
[mcp_servers.persian_poetry]
command = "qmd"
args = ["mcp"]
env = { "QMD_TRUST_LOCAL_CONFIG" = "1" }
```

(Use the `cmd /c qmd mcp` form from the Windows section above if you're
running Codex on Windows with an npm-global `qmd`.)

## Codex cloud

Same sandbox constraints as Claude Code web/mobile: no network access to
huggingface.co, so semantic search (`vec`/`hyde`, embedding, reranking) is
unavailable. Use `qmd search` (BM25) or `python3 scripts/ganjoor.py search
--offline`, and build a `--poets` subset rather than the full corpus if disk
or time is tight.

## Hermes / any generic MCP client

Both transports work; pick based on what your client supports.

**stdio** (recommended — default, no port to manage):

```bash
QMD_TRUST_LOCAL_CONFIG=1 qmd mcp
```

Point your client's stdio MCP config at that command with that environment
variable set — same shape as the Claude Code `.mcp.json` above.

**HTTP** (for clients that only speak HTTP, or when you want the server
reachable from another process/host):

```bash
QMD_TRUST_LOCAL_CONFIG=1 qmd mcp --http --port 8191
# or, to background it:
QMD_TRUST_LOCAL_CONFIG=1 qmd mcp --http --port 8191 --daemon
```

Endpoint: `http://localhost:8191/mcp`.

> **Note:** qmd 2.8.3's HTTP transport is **stateless** — `initialize` does
> not return an `mcp-session-id` (or any session) header. Do not implement
> session-header capture/echo logic against this version; just send each
> request independently.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "tool not found" / MCP server won't start | `qmd` not on `PATH`, or (Windows) it's a `.cmd` shim the launcher can't exec directly | Confirm `qmd --version` works in the same shell the harness uses; on Windows route through `cmd /c qmd mcp` (see above) |
| `query`/`vsearch`/`embed` hangs or fails with a connection/403 error | Environment has no network access to `huggingface.co` (cloud sandboxes, offline machines) | Use `qmd search` (BM25) or `python3 scripts/ganjoor.py search --offline`; on any MCP `query` call pass `"rerank": false` (the default is `true`, which tries to download a reranker model) |
| "config not trusted" / QMD refuses to start with the checked-in `.qmd/index.yml` | `QMD_TRUST_LOCAL_CONFIG` unset — checked-in configs that pin custom models require explicit trust | Set `QMD_TRUST_LOCAL_CONFIG=1` in the server's `env` (as in every config above), or run `qmd trust` once interactively |
| A thematic/conceptual query returns nothing from `ganjoor` | `ganjoor` is BM25-only by design (never embedded) — it does literal/lexical matching only, not meaning-based matching | That's expected: query `ganjoor` for exact lines/keywords; use `ganjoor-fa`/`ganjoor-en` (semantic, embedded) for themes — which in turn need network access to huggingface.co (see above) |

## Capability matrix

| Harness / environment | Exact search (BM25) | Persian semantic | English semantic | MCP |
|---|---|---|---|---|
| Claude Code CLI (macOS/Linux, local, online) | Yes | Yes (if embedded) | Yes (once v0.2 ships, if embedded) | Yes (stdio) |
| Claude Code Desktop (Windows, local, online) | Yes | Yes (if embedded) | Yes (once v0.2 ships, if embedded) | Yes (stdio via `cmd /c`) |
| Claude Code web / mobile (cloud sandbox) | Yes | No (no huggingface.co access) | No | Yes (stdio; `query` limited to `lex`, `rerank: false`) |
| Codex CLI / IDE (local, online) | Yes | Yes (if embedded) | Yes (once v0.2 ships, if embedded) | Yes (stdio) |
| Codex cloud | Yes | No | No | Yes (stdio; `lex`-only, `rerank: false`) |
| Hermes / generic MCP client (local, online) | Yes | Yes (if embedded) | Yes (once v0.2 ships, if embedded) | Yes (stdio or HTTP) |
| Any environment before `qmd embed` has run | Yes | No | No | Yes (`lex` only) |

"If embedded" = `qmd embed -c ganjoor-fa` / `-c ganjoor-en` has been run on
that machine and huggingface.co was reachable when it ran. `ganjoor-en` is
empty until the v0.2 enrichment ships regardless of embedding status.
