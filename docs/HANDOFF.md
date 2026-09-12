# HANDOFF — start here

The protocol for any agent or model (Claude Code, Codex, Hermes, or anything
else, running any model) picking up this repository, whether cold or
mid-task. This document assumes nothing about which harness or model is
reading it. Model-agnostic by design — do not add vendor-specific
instructions here; harness specifics live in
[docs/HARNESSES.md](HARNESSES.md).

## 1. Read order

1. **This file** — protocol and orientation.
2. **[SPEC.md](../SPEC.md)** — what the system is, the invariants you must
   not break.
3. **[ROADMAP.md](../ROADMAP.md)** — what's done, in-progress, blocked,
   planned.
4. **[CHANGELOG.md](../CHANGELOG.md)** `[Unreleased]` section — what has
   happened since the last release that ROADMAP.md's `done` markers alone
   won't tell you (exact scope of recent changes).
5. **AGENTS.md** (and `CLAUDE.md` if you are Claude Code — it's a fast-path
   pointer to AGENTS.md) — the operational command playbook: exact commands
   for setup, corpus build, indexing, embedding, search, MCP.
6. **[docs/HARNESSES.md](HARNESSES.md)** — per-harness MCP setup and a
   capability matrix, if your task involves MCP or you're unsure what your
   environment can do.

Do not skip straight to writing code from a task description alone — the
invariants in SPEC.md §5 and the "expensive operations" list below exist
specifically because skipping this reading has real cost (hours of rebuild
time, or a silently invalidated corpus).

## 2. Establish current state in one pass

```bash
python3 scripts/ganjoor.py doctor      # capability report: qmd on PATH?
                                        # huggingface.co reachable? corpus
                                        # built? index built?
git log --oneline -20                  # what actually landed recently
git status                             # what's uncommitted right now —
                                        # do not assume a clean tree
```

Cross-check `git status` output against the "YOUR FILES" boundaries of any
active workstream (if this is a multi-agent cycle) before touching anything
you didn't expect to see modified — a previous session's in-flight work may
still be sitting uncommitted.

## 3. Hard invariants — do not break these

Full detail: SPEC.md §5. Summary:

- **Never** silently change the Persian normalization map
  (`CHAR_MAP`/`DIACRITICS_RE`/`SPACE_RE` in `src/ganjoor2md.py`) or the
  search-text pipeline that derives `## متن ساده`. It invalidates every
  existing corpus and index. If a real reason exists to change it, write a
  `docs/DECISIONS.md` entry first and flag the rebuild cost explicitly.
- **Never** hand-edit the Markdown output format (frontmatter fields,
  section headings, the `poem:` pointer convention) without updating both
  the converter and every doc that describes it.
- **Never** edit upstream JSON (`poets/`, `index/`, `manifest.json`,
  `metres.json`, `languages.json`, `API.md`) — regenerate `md/` from it
  instead.
- **Never** run `qmd embed -c ganjoor` — that collection is BM25-only by
  design (ADR-001).
- **Never** commit `md/` or `.qmd/*.sqlite*` — see CONTRIBUTING.md.

## 4. Expensive operations — do not run casually

| Operation | Cost | When it's actually needed |
|---|---|---|
| Full corpus conversion (`python3 scripts/ganjoor.py corpus`, all poets) | ~6 min on 4 cores, ~1.4 GB, 263,603 files | Only after a converter change that must be validated at full scale, or to produce a Release artifact. Test converter changes on a `--poets` subset first. |
| Full `qmd update` (index build) over the full corpus | Fast relative to conversion, but still touches all 263K files | After a full corpus rebuild, or a `.qmd/index.yml` change. |
| `qmd embed` over `ganjoor-fa`/`ganjoor-en` | Minutes to hours depending on hardware; **first run downloads a ~640 MB model from huggingface.co** | Only when semantic search over summaries is actually needed and huggingface.co is reachable (see §5). Resumable — don't restart from scratch if it was interrupted. |
| English enrichment (`src/enrich.py` over the full corpus) | Costs real LLM API spend across ~132K poems (provider-dependent); idempotent/resumable via `summary_model` frontmatter | Only when explicitly asked to populate `ganjoor-en` (ROADMAP.md GO-020) — this has a real dollar cost per run, unlike the local-compute operations above. |

If a task seems to require one of these, check whether a small subset
(`--poets a,b,c`) proves the point first. Reserve the full-scale run for
when the owner actually wants the artifact regenerated.

## 5. Detecting your environment's capabilities

Different sessions of this same project run in very different
environments — a local laptop with full network access, a cloud sandbox
with none. Do not assume; check:

```bash
python3 scripts/ganjoor.py doctor
```

This reports whether `qmd` is on PATH, whether `huggingface.co` is
reachable, and whether the corpus/index already exist locally. Two
independent facts follow from that:

- **No huggingface.co access** (typical of cloud-sandboxed harness
  environments) → semantic search (`vec`/`hyde` query types, `qmd embed`,
  MCP `query` with default `rerank: true`) will fail or hang. Use `qmd
  search` (BM25) or `python3 scripts/ganjoor.py search --offline`, and pass
  `"rerank": false` on any MCP `query` call. This is architectural, not a
  bug to work around by retrying.
- **No `qmd`/Node at all** → `scripts/ganjoor.py search --offline` still
  works; it's stdlib Python over the raw Markdown files.

See SPEC.md §7 and `docs/HARNESSES.md`'s capability matrix for the full
picture, including per-harness specifics (Claude Code CLI vs. web/mobile,
Codex CLI vs. cloud, Hermes/generic MCP).

## 6. Exit protocol — before handing back

A session ends well when the *next* session (possibly a different model, a
different harness, days later) can run §2 above and get an accurate
picture without re-deriving anything you already knew. Before finishing:

1. **CHANGELOG.md** — add or update the `[Unreleased]` entry for what you
   actually did (grouped Added/Changed/Fixed). If you shipped something
   release-worthy, note it, but don't cut a version bump yourself unless
   asked.
2. **ROADMAP.md** — flip the status of any row you affected (`planned` →
   `in-progress` → `done`, or → `blocked` with the blocker named in the
   Dependency column). Add a new row if you did something not yet listed.
3. **docs/DECISIONS.md** — if you made a design choice a future agent could
   reasonably second-guess, add a numbered ADR entry with real rationale.
4. **Leave the working tree in a state `git status` explains** — no
   half-renamed files, no orphaned temp output. If you leave something
   intentionally uncommitted for the owner to review, say so in your final
   message; don't rely on the next session guessing why.
5. **Don't commit or push on the governance/hand-off document set unless
   asked** — these files describe state; let the owner decide when a
   documentation update is "real" enough to commit, same as any other
   change (see CONTRIBUTING.md).

If you were mid-task and genuinely blocked (missing credentials, a decision
only the owner can make, an environment limitation with no workaround),
say so plainly in ROADMAP.md (`blocked`, with the real blocker) and in your
final message — do not paper over it as `done`.
