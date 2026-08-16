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
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${QMD_MCP_PORT:-8191}"
export QMD_TRUST_LOCAL_CONFIG=1   # project-local config pins custom models

cd "$REPO_ROOT"

case "${1:-}" in
  stop)
    qmd mcp stop --port "$PORT"
    ;;
  --daemon)
    qmd mcp --http --port "$PORT" --daemon
    echo "QMD MCP server (ganjoor) listening on http://localhost:${PORT} (index: ${REPO_ROOT}/.qmd)"
    ;;
  *)
    exec qmd mcp --http --port "$PORT"
    ;;
esac
