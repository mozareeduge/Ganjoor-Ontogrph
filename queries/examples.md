# Example QMD queries — persian-poetry-ai-agent-plugin

All examples assume the project-local index is set up and collections are
embedded (see AGENTS.md). Run them from the repo root.

## English semantic — the primary mode (collection: `ganjoor-en`)

```bash
qmd query "poems about the pain of separation from the beloved at night" -c ganjoor-en -n 5
qmd query "poems about impermanence and seizing the moment" -c ganjoor-en -n 5
qmd query "poems praising wine and the tavern elder" -c ganjoor-en -n 5
qmd query "stories about Rustam and his son Sohrab" -c ganjoor-en -n 5
```

## English lexical (BM25) (collection: `ganjoor-en`)

```bash
qmd search "wine cupbearer tavern" -c ganjoor-en -n 5
qmd search "separation grief night" -c ganjoor-en -n 5
```

## Persian exact line (BM25) (collection: `ganjoor`)

```bash
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor -n 3
qmd search "رسید مژده که ایام غم نخواهد ماند" -c ganjoor -n 3
```

## Persian semantic (multilingual embedder, summary-only) (collection: `ganjoor-fa`)

```bash
qmd query "شعرهایی درباره دلتنگی و شب" -c ganjoor-fa -n 5
qmd query "شعرهایی درباره غم و گذر عمر" -c ganjoor-fa -n 5
qmd query "رباعی‌های خیام درباره مرگ و شراب" -c ganjoor-fa -n 5
```

## Structured query — author intent/lex/vec yourself

```bash
qmd query $'intent: Find ghazals about the pain of separation at night, not poems about wine parties.\nlex: separation night grief beloved parting\nvec: poems about the anguish of being apart from the beloved in the dark of night\nhyde: A Hafez ghazal describing the torment of separation and longing at night.' -c ganjoor-en -n 5
```

## The agent hand-off flow

```bash
# 1. Find the summary doc
qmd query "poems about impermanence and grief" -c ganjoor-en -n 3
# 2. Resolve the hit to a real file path
qmd get "#<docid>" --full-path
# 3. Read the summary file's frontmatter → poem: <relative path>
# 4. Read the full Persian poem at that path and answer from it
```
