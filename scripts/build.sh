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
#
# Thin wrapper: the corpus/index/embed stages delegate to scripts/ganjoor.py
# (the single cross-platform entrypoint); this script only keeps the
# documented env-var interface stable for existing users/docs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INPUT="${INPUT:-$REPO_ROOT}"
OUTPUT="${OUTPUT:-md}"
JOBS="${JOBS:-}"

echo "== Stage 1: convert JSON → Markdown =="
if [[ "$INPUT" == "$REPO_ROOT" && "$OUTPUT" == "md" ]]; then
  # Default paths: delegate to ganjoor.py (it picks the CPU count itself
  # when JOBS is unset — no more hardcoded/macOS-only job counts).
  if [[ -n "$JOBS" ]]; then
    python3 scripts/ganjoor.py corpus --jobs "$JOBS"
  else
    python3 scripts/ganjoor.py corpus
  fi
else
  # Custom INPUT/OUTPUT: ganjoor.py's `corpus` command always reads/writes
  # the repo's own tree, so fall back to the converter directly for this
  # legacy case rather than dropping INPUT/OUTPUT support.
  python3 src/ganjoor2md.py --input "$INPUT" --output "$OUTPUT" \
    --jobs "${JOBS:-$(python3 -c 'import os; print(os.cpu_count() or 4)')}"
fi

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
python3 scripts/ganjoor.py index
# Embed ONLY the summary collections. The `ganjoor` collection (full poems) is
# intentionally BM25-only — embedding it wastes hours for nothing.
python3 scripts/ganjoor.py embed

echo
echo "Done. Try:"
echo "  python3 scripts/ganjoor.py query 'poems about the pain of separation at night' -c ganjoor-en"
echo "  python3 scripts/ganjoor.py search 'که عشق آسان نمود اول ولی افتاد مشکل ها' -c ganjoor"
