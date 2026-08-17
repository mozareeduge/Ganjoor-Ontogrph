# persian-poetry-ai-agent-plugin — easy targets for reproducible use.
# Transparent: every target just calls the same documented steps (see AGENTS.md).

SHELL := /bin/bash
export QMD_TRUST_LOCAL_CONFIG := 1

.PHONY: help setup corpus index embed all search mcp demo clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install QMD (Node prerequisite) and check Python
	@command -v qmd >/dev/null 2>&1 || npm install -g @tobilu/qmd
	@qmd --version
	@python3 --version

corpus: ## Build md/ from the checked-in data (or set CORPUS_TAR to unpack a release)
	@if [ -n "$(CORPUS_TAR)" ]; then \
		mkdir -p md && tar -xzf "$(CORPUS_TAR)" -C md; \
	else \
		python3 src/ganjoor2md.py --input . --output md --jobs $(shell sysctl -n hw.ncpu 2>/dev/null || echo 4); \
	fi
	@echo "corpus ready: md/"

index: ## Index the Markdown corpus (fast; BM25 + metadata)
	qmd update

embed: ## Generate vectors for semantic search (summary collections only; first run downloads the Qwen3 model)
	qmd embed -c ganjoor-fa
	qmd embed -c ganjoor-en

all: corpus index embed ## Corpus + index + embed (the full local setup)

search: ## Try a sample Persian exact-line search
	qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor -n 3

mcp: ## Start the MCP server (agents can then query the corpus)
	./scripts/mcp-server.sh --daemon

demo: ## Start the simple web search page
	python3 scripts/web-demo.py

clean: ## Remove generated artifacts (md/ and the local index)
	rm -rf md .qmd/index.sqlite
