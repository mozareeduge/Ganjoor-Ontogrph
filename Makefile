# persian-poetry-ai-agent-plugin — easy targets for reproducible use.
# Transparent: every target just calls the same documented steps (see AGENTS.md).
# Thin wrappers around scripts/ganjoor.py, the single cross-platform entrypoint.

SHELL := /bin/bash
export QMD_TRUST_LOCAL_CONFIG := 1

.PHONY: help setup corpus index embed all search mcp demo clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install QMD (Node prerequisite) and check Python
	@python3 scripts/ganjoor.py setup

corpus: ## Build md/ from the checked-in data (or set CORPUS_TAR to unpack a release)
	@python3 scripts/ganjoor.py corpus $(if $(CORPUS_TAR),--tar "$(CORPUS_TAR)")
	@echo "corpus ready: md/"

index: ## Index the Markdown corpus (fast; BM25 + metadata)
	python3 scripts/ganjoor.py index

embed: ## Generate vectors for semantic search (summary collections only; first run downloads the Qwen3 model)
	python3 scripts/ganjoor.py embed

all: corpus index embed ## Corpus + index + embed (the full local setup)

search: ## Try a sample Persian exact-line search
	python3 scripts/ganjoor.py search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor -n 3

mcp: ## Start the MCP server (agents can then query the corpus)
	./scripts/mcp-server.sh --daemon

demo: ## Start the simple web search page
	python3 scripts/ganjoor.py demo

clean: ## Remove generated artifacts (md/ and the local index)
	rm -rf md .qmd/index.sqlite
