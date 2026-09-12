# CONTRIBUTING

How a human **or an agent** (Claude Code, Codex, Hermes, any model) changes
this repository safely. Read [docs/HANDOFF.md](docs/HANDOFF.md) first if you
are starting a session cold.

## Branching

Observed convention on this project: agent sessions work on branches named
`claude/<two-word-codename>` (e.g. `claude/quirky-meitner-x9xmhx`) or
similarly harness-generated names — do not rename these mid-session. For
manually created branches, use `<type>/<short-topic>` (e.g.
`fix/web-demo-parsing`, `docs/handoff-kit`), matching the commit type
prefixes below.

Never push directly to `main` for anything beyond trivial doc fixes the
owner has explicitly asked for inline — open a branch, let CI run, then the
owner merges.

## Commit messages

This repository's actual history (`git log --oneline`) uses a consistent
`type: summary` prefix, occasionally `type(scope): summary`:

```
feat: agent-ready Markdown + QMD search layer for the Ganjoor corpus
fix: web-demo parsing — line-based hit parsing + collection→dir map
docs: explicit installation playbook (AGENTS.md) + README quickstart aligned with Release-artifact distribution
docs(fa): humanized Persian README — natural tech voice, English terms for MD/index/embed/MCP
ci: release workflow — build MD corpus → GitHub Release artifact
data: export 234 poets / 132591 poems — 2026-08-16
```

Follow this pattern:

- Lowercase type prefix: `feat`, `fix`, `docs`, `ci`, `data`, or another type
  if none of these fit (do not invent a type when an existing one applies).
- One line, present tense, states what changed and often *why* or *what for*
  after an em dash — not a changelog restatement of the diff.
- Optional scope in parens (`docs(fa):`) when a change is language- or
  area-specific.
- No footer boilerplate is used in this repo's own history beyond what a
  specific harness's system prompt requires you to append (attribution
  lines, if your environment mandates them) — do not add ticket numbers or
  co-author trailers unless asked.

## What must be updated alongside a change

| You changed... | Also update |
|---|---|
| Any code/data behavior | [CHANGELOG.md](CHANGELOG.md) `[Unreleased]`, grouped Added/Changed/Fixed |
| A task's status (started, blocked, finished) | [ROADMAP.md](ROADMAP.md) — flip the status, don't leave it stale |
| A design/architecture choice (why X over Y) | [docs/DECISIONS.md](docs/DECISIONS.md) — new numbered ADR entry |
| The normalization map, search-text pipeline, or Markdown output format | SPEC.md §5 invariants — these are breaking changes (see CHANGELOG versioning policy); flag loudly, do not slip in quietly |
| A new supported harness or environment quirk | [docs/HARNESSES.md](docs/HARNESSES.md) (owned by other workstreams — coordinate rather than edit directly if you are in the governance workstream) |

If you're not sure whether a change is decision-worthy: if a future agent
could plausibly ask "why is it done this way instead of the obvious other
way," it belongs in DECISIONS.md.

## What must never be committed

- `md/` — the generated Markdown corpus (gitignored; ~1.4 GB, 263K files;
  distributed as a Release artifact, not committed).
- `.qmd/index.sqlite`, `.qmd/*.sqlite*`, `.qmd/.cache/` — the local search
  index; machine-specific, rebuilt with `qmd update` + `qmd embed`.
- API keys, tokens, or credentials of any kind. `src/enrich.py` reads
  `OPENAI_API_KEY` (and friends) from the environment only — never hardcode
  a key in a script, config, or example.
- Machine-specific paths or state (a specific laptop's absolute paths, a
  specific global QMD config).
- `__pycache__/`, `*.pyc`, OS junk (`.DS_Store`).

Before committing, run `git status` and look for anything under `md/`,
`.qmd/`, or a stray key before staging — `.gitignore` covers the known
cases but a `git add -A` habit can still surprise you with something new.

## Verification before proposing a change

Cheap checks — run these every time, they take seconds:

```bash
python -m py_compile src/ganjoor2md.py src/enrich.py scripts/ganjoor.py
python3 scripts/ganjoor.py doctor
```

If you touched the converter, enrichment, or search-text pipeline, prove it
on a **small subset** — never rebuild the full corpus to test a change:

```bash
python3 scripts/ganjoor.py corpus --poets varragh,vasif --force
python3 scripts/ganjoor.py index
python3 scripts/ganjoor.py search "<a known phrase from that poet>" --offline
```

This mirrors what `.github/workflows/ci.yml` runs on every push (a
2-poet/5-poem subset, on ubuntu/macos/windows runners) — if it doesn't pass
locally on a subset, it won't pass in CI on the full matrix either.

If you touched the normalization map or output format specifically: SPEC.md
§5 says this forces a full rebuild + re-embed. State that explicitly in your
PR/commit description so the owner knows to schedule it — do not run the
full ~6-minute/1.4 GB build yourself unless asked; it is expensive and the
owner may prefer to run it once on their own machine after reviewing the
change.

## Local-laptop ↔ cloud-repo sync flow

The owner develops across a local laptop repo synced with this cloud repo,
switching agentic harnesses and models mid-project. This makes ordinary git
discipline more important, not less:

- **Fetch and rebase before pushing**, always: `git fetch origin && git
  rebase origin/<branch>` (or merge, if the harness's workflow prefers that)
  before pushing your own commits. A session that skips this can silently
  overwrite work the owner did locally between sessions.
- **Never force-push a shared branch** (`main`, or any branch another
  session/the laptop might also be working on). Force-pushing rewrites
  history other checkouts still hold — the laptop's next `git pull` either
  conflicts messily or, worse, silently diverges. If a rebase produces
  conflicts, resolve them in the rebase; if you truly believe history needs
  rewriting, stop and ask the owner rather than deciding unilaterally.
- **Small, frequent commits** beat one large one — easier for the next
  session (possibly a different model, different harness) to see exactly
  what changed and why via `git log`.
- If you are an agent picking up mid-project, assume the working tree may
  already have uncommitted changes from a previous session (this workstream
  itself started with several modified/untracked files already in the
  tree) — `git status` before doing anything destructive, and never `git
  checkout --`/`git reset --hard`/`git clean -f` without first confirming
  nothing valuable would be lost (stash if unsure).

## Scope discipline for multi-agent cycles

This project is sometimes worked by several agents in parallel on the same
branch, each assigned a disjoint file set (see this document's own origin:
a "workstream" covering only the governance/hand-off files). If you were
given an explicit file list, **stay inside it** — touching a file another
workstream owns, even to fix something you noticed, creates merge conflicts
and duplicated/contradictory edits. Flag it instead (a DECISIONS entry, a
ROADMAP row, or a note back to whoever coordinates the cycle).
