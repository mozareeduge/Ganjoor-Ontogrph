# DECISIONS — architecture decision log

Lightweight ADR log. Each entry: number, date, status, context, decision,
consequences. Backfilled from the codebase and commit history for decisions
already embedded in the system; add new entries going forward rather than
editing old ones (append a note under a later ADR if a decision is revisited
— see the "Superseded" convention below).

Status values: `accepted`, `superseded by ADR-NNN`.

See [SPEC.md](../SPEC.md) for the resulting architecture as it stands,
[ROADMAP.md](../ROADMAP.md) for what's still open.

---

## ADR-001 — Three QMD collections, embed summaries only, never poems

- **Date**: 2026-08-16 (first implemented in `feat: agent-ready Markdown +
  QMD search layer for the Ganjoor corpus`)
- **Status**: accepted
- **Context**: The corpus has two very different kinds of text per poem —
  long, formulaic, vocalized classical verse (~132K poems), and short, dense
  AI-generated summaries in Persian (and, later, English). A single
  collection embedding everything would be simplest to set up.
- **Decision**: Split into three collections. `ganjoor` (full poems, bios,
  category indexes) is **BM25-only, never embedded**. `ganjoor-fa` and
  `ganjoor-en` (one summary file per poem, physically separate from the poem
  file) are embedded. Every summary file's frontmatter carries a `poem:`
  pointer back to the full poem.
- **Consequences**: Semantic search finds poems *by theme via their
  summary*, then the pointer resolves to the real text — retrieval never
  substitutes for reading the poem. Embedding cost is bounded to ~130K short
  summaries per language rather than ~130K long poems. Exact-line/quote
  search (arguably the most valuable mode for poetry — people search by a
  half-remembered line) stays cheap, exact, and model-free. Cost: nobody can
  ask "give me poems whose full text is semantically similar to X" directly
  — only via the summary proxy. Never run `qmd embed -c ganjoor`; if that
  temptation arises, the real gap is summary quality/coverage, not poem
  embedding.

## ADR-002 — Dual representation per poem: vocalized text + normalized «متن ساده»

- **Date**: 2026-08-16
- **Status**: accepted
- **Context**: Ganjoor's canonical poem text is fully vocalized (diacritics,
  precise Arabic-vs-Farsi letterforms). Real-world Persian search queries
  are typed unvocalized, often with inconsistent letterforms (ي vs ی, ك vs
  ک) and ZWNJ usage. Indexing only the vocalized text would silently miss
  the way people actually search.
- **Decision**: Keep the vocalized couplets as the canonical, displayed
  text. Additionally render a `## متن ساده` section — the same text passed
  through `normalize_search_text` (strip diacritics/tatweel, map
  Arabic-style letters to Farsi equivalents, collapse ZWNJ and exotic
  spaces to plain spaces) — purely for matching.
- **Consequences**: BM25 search on `ganjoor` matches how people type, not
  just the "correct" vocalized spelling. The mapping is now an invariant
  (SPEC.md §5, ADR-008): changing it changes what every existing index
  matches, requiring a full rebuild + re-embed.

## ADR-003 — Quality gate drops junk Persian summaries

- **Date**: 2026-08-16
- **Status**: accepted
- **Context**: Ganjoor's `PoemSummary` field is an AI-generated summary
  prefixed with «هوش مصنوعی:». Not every poem has a usable one — some are
  empty, truncated, or too short to carry real thematic content, which
  would pollute the `ganjoor-fa` collection with near-empty embedded
  documents.
- **Decision**: `clean_ai_summary` strips the AI prefix and whitespace, then
  drops the summary entirely (`SUMMARY_MIN_CHARS = 100`) if what remains is
  under 100 characters. No `## خلاصه` section and no `md/summaries-fa/...`
  file are generated for that poem.
- **Consequences**: `ganjoor-fa` is smaller than the full poem count (fewer
  than 132,538 documents) but higher signal — every embedded Persian summary
  is a real summary. A poem missing a خلاصه section is missing it because it
  failed the gate, not a bug. The 100-char threshold is a judgment call, not
  derived from data analysis; revisiting it is a valid future ADR but
  requires a rebuild.

## ADR-004 — Project-local, isolated QMD index instead of the machine-global one

- **Date**: 2026-08-16
- **Status**: accepted
- **Context**: QMD normally maintains one global index per machine/profile.
  This project needs a specific, pinned embedding model (multilingual
  Qwen3-Embedding) and a specific three-collection layout that would
  conflict with, or be overwritten by, whatever else uses QMD on the same
  machine.
- **Decision**: Check in `.qmd/index.yml` (collection paths, patterns,
  context strings, pinned model URIs) at the repo root. The index database
  itself (`.qmd/index.sqlite*`) is gitignored and built locally per machine.
  `QMD_TRUST_LOCAL_CONFIG=1` is required to opt into a checked-in config
  that pins non-default models — this is QMD's own safety gate, not this
  project's.
- **Consequences**: Any clone gets the exact same collection layout and
  embedding model, regardless of what else that machine's QMD is doing
  elsewhere. Downside: every environment variable and command in every doc
  must remember to set `QMD_TRUST_LOCAL_CONFIG=1`, or QMD refuses to start —
  this is documented repeatedly (AGENTS.md, CLAUDE.md, docs/HARNESSES.md)
  because it's the single most common setup failure.

## ADR-005 — Distribute the Markdown corpus as a Release artifact, not committed `md/`

- **Date**: 2026-08-16 (`ci: release workflow — build MD corpus → GitHub
  Release artifact`)
- **Status**: accepted
- **Context**: The generated corpus is ~1.4 GB across 263,603 files.
  Committing it would make every clone slow, bloat the repo permanently
  (git never shrinks), and couple every doc change to a multi-GB diff.
- **Decision**: `md/` is gitignored. A CI release workflow builds it from
  the checked-in upstream JSON and uploads a tarball (`ganjoor-md-v*.tar.gz`)
  as a GitHub Release asset. Consumers either download that artifact or run
  `src/ganjoor2md.py` themselves (~6 min on 4 cores).
- **Consequences**: Clones stay small and fast. The tradeoff is a
  dependency on GitHub Releases actually existing for a given repo — see
  ROADMAP.md GO-011: this repo (`mozareeduge/Ganjoor-Ontogrph`) does not yet
  have its own Release, only the upstream fork does, so the
  download-artifact path in README currently only works against the
  upstream fork's Releases page, not this one.

## ADR-006 — stdio as the default MCP transport

- **Date**: 2026-08-16/17, reaffirmed this cycle when writing
  `docs/HARNESSES.md`
- **Status**: accepted
- **Context**: `qmd mcp` supports stdio and `qmd mcp --http --port 8191`.
  Different harnesses have different defaults and constraints; a choice had
  to be made for what this repo documents and configures (`.mcp.json`) by
  default.
- **Decision**: stdio is the default and recommended transport. No port to
  manage, no session-header handling to get wrong (qmd 2.8.3's HTTP
  transport is stateless — no `mcp-session-id` at all, which differs from
  qmd 2.5.3's session-based HTTP documented earlier in project history — a
  version-sensitive detail worth re-checking if `qmd` is upgraded). HTTP
  remains available and documented for clients that only speak HTTP or need
  a server reachable from another process/host.
- **Consequences**: `.mcp.json`, Claude Code config, Codex `config.toml`
  examples all default to stdio. Anyone reaching for HTTP should re-verify
  the session-header behavior against the `qmd` version actually installed
  — it has changed across versions already.

## ADR-007 — No-dependency offline search path for restricted/cloud harnesses

- **Date**: this cycle (`scripts/ganjoor.py`)
- **Status**: accepted
- **Context**: Cloud-sandboxed agent harnesses (Claude Code web/mobile,
  Codex cloud) block network access to `huggingface.co`, so `qmd embed`,
  semantic `qmd query`, and MCP `query` with default `rerank: true` cannot
  function there — and in some such environments even installing `qmd`
  itself (an npm package needing Node) may be inconvenient or unavailable.
  Without a fallback, those environments could do nothing at all with the
  corpus.
- **Decision**: `scripts/ganjoor.py search --offline` implements a
  pure-Python, stdlib-only search directly over the Markdown files — no
  `qmd`, no Node, no model download, no network. It is necessarily cruder
  than QMD's BM25 (no proper index, simpler scoring) but always works.
- **Consequences**: Every environment, no matter how restricted, has *some*
  working search path. This is documented as a first-class capability (not
  a last-resort hack) in SPEC.md §7 and `docs/HARNESSES.md`'s capability
  matrix. Agents should reach for it proactively in sandboxed environments
  rather than repeatedly hitting the huggingface.co wall first.

## ADR-008 — Freeze the Persian normalization map

- **Date**: encoded as a code comment 2026-08-16, formalized as a governance
  rule this cycle
- **Status**: accepted
- **Context**: `normalize_search_text`'s `CHAR_MAP` (ي/ى→ی, ك→ک, ة/ھ→ه) and
  the diacritics/space-collapsing regexes define what `## متن ساده` contains
  for every one of 132,538 poems, and thus what every BM25 query is matched
  against. A well-intentioned "fix" (e.g. also remapping precomposed hamza
  letters آ/أ/إ/ؤ/ئ) would look like an improvement in isolation but change
  matching behavior for the entire corpus. The code comment already
  explains why hamza letters are deliberately *not* remapped (SQLite's
  `unicode61` tokenizer decomposes them symmetrically for both doc and
  query already, so remapping would only break correct spellings like
  «آسان»، «رئیس»).
- **Decision**: Treat `CHAR_MAP`, `DIACRITICS_RE`, and `SPACE_RE` as frozen
  unless a new ADR explicitly revisits them, documents the new rationale,
  and triggers a full rebuild + re-embed. This is now stated explicitly in
  SPEC.md §5 as an invariant, not left implicit in a code comment.
- **Consequences**: Anyone (human or agent) wanting to "improve" Persian
  normalization must write an ADR and accept the rebuild cost before
  touching this code, not slip a change in alongside an unrelated fix.
