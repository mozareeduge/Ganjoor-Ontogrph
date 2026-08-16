#!/bin/bash
# build.sh — full persian-poetry-ai-agent-plugin pipeline: JSON → Markdown → (enrichment) → QMD index.
#
# Portable: no machine-specific paths, no hardcoded credentials. Enrichment is
# pluggable — any OpenAI-compatible endpoint. If OPENAI_API_KEY is unset, the
# pipeline still converts + indexes (Persian search works without enrichment;
# English semantic search needs it).
#
# Env vars:
#   INPUT             path to ganjoor-data clone (default: repo root)
#   OUTPUT            markdown output root (default: md)
#   JOBS              converter worker processes (default: CPU count)
#   OPENAI_BASE_URL   OpenAI-compatible base URL (default: https://api.deepseek.com/v1)
#   OPENAI_API_KEY    required for enrichment
#   ENRICH_MODEL      model id (default: deepseek-v4-flash)
#   ENRICH_WORKERS    concurrent LLM calls (default: 8)
#
# Usage:
#   ./scripts/build.sh                          # convert + index (no enrichment)
#   OPENAI_API_KEY=sk-... ./scripts/build.sh    # convert + enrich + index
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INPUT="${INPUT:-$REPO_ROOT}"
OUTPUT="${OUTPUT:-md}"
JOBS="${JOBS:-$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)}"

echo "== Stage 1: convert JSON → Markdown =="
python3 src/ganjoor2md.py --input "$INPUT" --output "$OUTPUT" --jobs "$JOBS"

echo
echo "== Stage 2: enrichment (English semantic summaries) =="
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  python3 src/enrich.py --md "$OUTPUT" --workers "${ENRICH_WORKERS:-8}"
else
  echo "OPENAI_API_KEY not set — skipping enrichment."
  echo "Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / ENRICH_MODEL) to enable English semantic search."
fi

echo
echo "== Stage 3: project-local QMD index =="
export QMD_TRUST_LOCAL_CONFIG=1
qmd update
qmd embed

echo
echo "Done. Try:"
echo "  qmd query 'poems about the pain of separation at night' -c ganjoor-en"
echo "  qmd search 'که عشق آسان نمود اول ولی افتاد مشکل ها' -c ganjoor"
