#!/bin/bash
# mcp-server.sh — expose the project's QMD index as an MCP server (agent-ready).
#
# Runs the project-local QMD index (see .qmd/index.yml) over MCP's stateless
# HTTP transport. Any MCP client (Hermes, Claude, other agents) can query the
# corpus with tools instead of shell commands.
#
# Port: 8191 by default — isolated from Doc's QMD daemons (8181/8182).
# The server reads the index read-only; the enrichment crawl can keep running.
#
# Usage:
#   ./scripts/mcp-server.sh           # start in foreground
#   ./scripts/mcp-server.sh --daemon  # start as background daemon
#   ./scripts/mcp-server.sh stop      # stop the daemon
#
# Thin wrapper: delegates to `python3 scripts/ganjoor.py mcp` (the single
# cross-platform entrypoint); this script only keeps its own env var and
# argument interface stable for existing users/docs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${QMD_MCP_PORT:-8191}"

cd "$REPO_ROOT"

case "${1:-}" in
  stop)
    python3 scripts/ganjoor.py mcp --http --port "$PORT" --stop
    ;;
  --daemon)
    python3 scripts/ganjoor.py mcp --http --port "$PORT" --daemon
    echo "QMD MCP server (ganjoor) listening on http://localhost:${PORT} (index: ${REPO_ROOT}/.qmd)"
    ;;
  *)
    exec python3 scripts/ganjoor.py mcp --http --port "$PORT"
    ;;
esac
