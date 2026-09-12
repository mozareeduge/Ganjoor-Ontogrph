# SPEC — Ganjoor-Ontograph

Durable specification of what this system **is**. Not a build log, not a
roadmap — see [ROADMAP.md](ROADMAP.md) for status and
[docs/DECISIONS.md](docs/DECISIONS.md) for *why* it is built this way. A
fresh agent with no prior chat history should be able to act correctly on
this repository from this file alone (plus [AGENTS.md](AGENTS.md) /
[CLAUDE.md](CLAUDE.md) for operational commands).

> Repo URL note: the canonical project name is **Ganjoor-Ontograph**, but the
> repository is currently hosted at `github.com/mozareeduge/Ganjoor-Ontogrph`
> (missing the second "a"). A rename is planned (tracked as `GO-010` in
> ROADMAP.md) but has not happened. Use "Ganjoor-Ontograph" in prose; use the
> `Ganjoor-Ontogrph` spelling in every URL/clone command until the rename
> lands.

## 1. Purpose

Two layers, deliberately kept distinct:

- **What exists today**: a conversion + indexing + retrieval pipeline that
  turns the Ganjoor Persian classical poetry corpus into an agent-ready
  Markdown database, searchable locally (BM25 always, vector search when a
  model is available), and exposed to AI agents over MCP.
- **What this project is *for***: a *research machine* for opening new
  perspectives on the Persian classical literary archive — cross-poet
  thematic exploration, structural/relational analysis across 132K+ poems,
  eventually an explicit ontology/graph layer over poets, poems, forms,
  metres, and themes (the "ontograph" in the name). This is the owner's
  stated long-term ambition. **It is not built yet.** Do not describe graph
  or ontology capabilities as present; see §6 Non-goals and ROADMAP.md v0.3+.

## 2. Provenance

```
ganjoor/ganjoor-data  →  erfanbashar1/persian-poetry-ai-agent-plugin  →  Ganjoor-Ontograph (this repo)
(upstream JSON corpus)   (JSON→Markdown conversion, enrichment,          (governance/hand-off layer,
                          three-collection QMD search, MCP server)        cross-harness support, this
                                                                           SPEC/ROADMAP/DECISIONS kit)
```

Full attribution and licensing detail: [NOTICE.md](NOTICE.md). Do not break
this chain — credit stays intact when this project is renamed, forked, or
redistributed.

## 3. Data model

### 3.1 Source of truth (read-only)

`poets/`, `index/`, `manifest.json`, `metres.json`, `languages.json`,
`API.md` are the upstream Ganjoor JSON export. **Never edit them.** They are
the sole input to `src/ganjoor2md.py`. If something about the generated
corpus is wrong, fix the converter and regenerate — do not hand-patch
generated Markdown or upstream JSON.

### 3.2 Generated Markdown corpus (`md/`, gitignored, built or downloaded)

Four document kinds, one Markdown file each:

| Kind | Path shape | Produced by |
|---|---|---|
| Poet bio | `md/poets/<slug>/<slug>.md` | poet's `poet.json` |
| Category index | `md/poets/<slug>/<catpath>/_cat.md` | `_cat.json` |
| Poem | `md/poets/<slug>/<catpath>/<poemslug>.md` | poem JSON (any non-poet/`_cat` file) |
| Persian summary mirror | `md/summaries-fa/<slug>/<catpath>/<poemslug>.md` | poem's `PoemSummary`, quality-gated |
| English summary | `md/summaries-en/<slug>/<catpath>/<poemslug>.md` | `src/enrich.py` output (v0.2, currently empty) |

**Every file** has YAML frontmatter, then a body. Frontmatter fields on a
poem file (see `src/ganjoor2md.py::render_poem`):

```
id, cat_id, title, full_title, poet, poet_slug, category_path, format,
metre, metre_id, rhyme, language, source, couplets, url,
topics_en, summary_model, summary_date
```

A summary file's frontmatter carries the same identity fields plus the
field that makes the whole architecture navigable:

```
poem: <path to the full poem file, relative to the summary file>
```

**Every summary file points back to its poem.** This pointer is the bridge
between "found by theme" (summary collections) and "read the real text"
(poem collection). Never answer from a summary snippet alone — always follow
`poem:` and read the full poem.

**Poem body structure** (in this order, sections present only when the
corresponding data exists):

1. **Vocalized couplets** — the canonical text, rendered verse-by-verse from
   `Verses` (or `PlainText` fallback for prose entries with no verses).
2. **`## متن ساده`** — the same text unvocalized and character-normalized
   (see §4 normalization map). This is what matches how people actually type
   Persian search queries; it exists purely for lexical matching.
3. **`## خلاصه`** — Ganjoor's Persian AI summary, present only if it passes
   the quality gate (see §4). The «هوش مصنوعی:» prefix is stripped.
4. **`## Summary (EN)`** — English semantic summary + `topics_en`, present
   only for enriched poems (v0.2, `src/enrich.py`). Empty in v0.1.

### 3.3 Poem summary mirror files (`md/summaries-fa/**`, `md/summaries-en/**`)

Standalone Markdown files — not a section of the poem file — one per poem
that has a summary. This physical separation (not just a heading) is what
lets QMD index each language's summaries as its own collection and embed
only that collection. See §4.

## 4. Architecture: three collections, embed-summaries-only

`.qmd/index.yml` defines three collections:

| Collection | Source path | Vectors? | Purpose |
|---|---|---|---|
| `ganjoor` | `md/poets/**` | **No — BM25 only, by design** | Persian exact-line search over full poems, bios, category indexes |
| `ganjoor-fa` | `md/summaries-fa/**` | Yes | Persian semantic search over خلاصه summaries |
| `ganjoor-en` | `md/summaries-en/**` | Yes | English semantic search over English summaries (empty until v0.2 enrichment runs) |

**Rule: embeddings run only on summary collections. Never embed `ganjoor`.**
Rationale (see `docs/DECISIONS.md` ADR-001):

- Full poems are long, formulaic across a poet's corpus, and vocalized text
  embeds poorly with a general multilingual model — semantic search on full
  poems returns noise.
- Summaries are short, dense, thematic — exactly the shape that embeds well.
- Every embedded document carries a `poem:` pointer, so semantic search on a
  summary is retrieval *for* the poem, not a replacement for reading it.
- This also bounds embedding cost: ~130K summaries per language instead of
  ~130K long poems, and poems are searched by exact text instead (cheap,
  exact, no model needed).

Do not run `qmd embed -c ganjoor`. If you find yourself wanting semantic
search over full poem text, that is a sign to improve summaries, not to
embed poems.

## 5. Invariants — never change silently

These four things, if changed, invalidate correctness assumptions baked into
already-built corpora/indexes on other machines (the owner's laptop, CI,
past Release artifacts). A change to any of them is a **breaking change**
(see CHANGELOG.md versioning policy) requiring: a DECISIONS entry explaining
why, a full corpus rebuild, and a full re-embed.

1. **The Persian normalization map** (`CHAR_MAP`, `DIACRITICS_RE`, `SPACE_RE`
   in `src/ganjoor2md.py::normalize_search_text`) — maps Arabic-style
   letters to Farsi equivalents (ي/ى→ی, ك→ک, ة/ھ→ه), strips diacritics and
   tatweel, collapses ZWNJ and exotic spaces. This is what the `## متن ساده`
   section contains and what every BM25 query is implicitly matched against.
   Precomposed hamza letters (آ أ إ ؤ ئ) are deliberately **not** remapped —
   see the code comment for why. Do not "fix" or extend this map without a
   DECISIONS entry; every existing `md/` tree and index was built against the
   current mapping.
2. **The search-text pipeline** — the fact that `متن ساده` is derived from
   the *same* rendered body as the vocalized text, via one deterministic
   function, with no additional cleanup steps. Adding a step changes what
   matches.
3. **The Markdown output format** — the frontmatter field set/order, the
   heading names (`## متن ساده`, `## خلاصه`, `## Summary (EN)`, `## آثار
   (Works)`, `## زیرشاخه‌ها`, `## شعرها`), and the summary-file `poem:`
   pointer convention. Downstream tooling (QMD collection contexts, the MCP
   skill playbook, `scripts/ganjoor.py --offline` search) parses this
   structure directly.
4. **Upstream JSON is read-only**: `poets/`, `index/`, `manifest.json`,
   `metres.json`, `languages.json`, `API.md`. These track upstream
   `ganjoor-data`; regenerate `md/` from them, never hand-edit them or the
   generated output.

Any other implementation detail (converter internals, MCP transport choice,
enrichment provider) can change freely with an ordinary CHANGELOG entry.

## 6. Non-goals (today)

Explicitly **not** part of the current system — do not assume these exist
or attempt to wire them in as if they were minor additions:

- No graph database, no ontology schema, no entity/relation extraction over
  poems. "Ontograph" is a name for a direction, not a shipped feature.
- No editing/annotation layer for poems or summaries beyond the enrichment
  pipeline's own frontmatter fields.
- No web application, hosted service, or multi-user access control. This is
  a local-first, single-user (per machine) tool.
- No modification of upstream Ganjoor content — corrections, alternate
  readings, or scholarly annotations are out of scope for this repo's
  pipeline.
- No commitment to any particular graph technology, embedding model, or LLM
  provider beyond what is already pluggable (`src/enrich.py` is
  OpenAI-API-compatible and provider-agnostic by design).

## 7. Environment capability model

Not every environment this project runs in has the same capabilities. Two
independent axes determine what works:

| Axis | Needs | Unavailable when |
|---|---|---|
| **Lexical (BM25) search** | `qmd` on PATH + built index, or nothing at all (`scripts/ganjoor.py search --offline`) | Never — always available once the corpus/index exists |
| **Semantic (vector) search** | Network access to `huggingface.co` to download the embedding/reranker model (~640 MB, once per machine) | Cloud/sandboxed harness environments (Claude Code web/mobile, Codex cloud) block this host — this is a **permanent architectural constraint**, not a bug to fix |

Consequences an agent must reason about:

- In a sandboxed cloud environment, `qmd embed`, `qmd query` with `vec`/`hyde`
  search types, and MCP `query` calls with default `rerank: true` will fail
  or hang. Use `qmd search` (BM25), `python3 scripts/ganjoor.py search
  --offline`, and pass `"rerank": false` on MCP `query` calls.
- `ganjoor-en` is empty regardless of environment until v0.2 enrichment has
  been run somewhere with the corpus and an LLM API key — this is a data gap,
  not a capability gap.
- Full detail and a per-harness capability matrix: [docs/HARNESSES.md](docs/HARNESSES.md).
- One-command capability check for the *current* environment:
  `python3 scripts/ganjoor.py doctor`.

## 8. Cross-references

- [ROADMAP.md](ROADMAP.md) — task ladder, status, milestones.
- [CHANGELOG.md](CHANGELOG.md) — what shipped, when, versioning policy.
- [docs/DECISIONS.md](docs/DECISIONS.md) — why the architecture is this shape.
- [docs/HANDOFF.md](docs/HANDOFF.md) — start-here protocol for a new agent/session.
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to change this repo safely.
- [NOTICE.md](NOTICE.md) — licensing and provenance.
- [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) — operational command playbook.
- [docs/HARNESSES.md](docs/HARNESSES.md) — per-harness MCP setup and capability matrix.
