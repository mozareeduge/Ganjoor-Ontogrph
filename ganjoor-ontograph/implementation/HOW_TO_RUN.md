# How to actually run the build

This package is meant to be executed from a **fresh Claude Code context** —
not the session that wrote it. That's deliberate: implementation is many
small, verifiable steps across (probably) dozens of iterations, and a long
planning conversation is the wrong thing to keep replaying underneath all
of them. Everything a fresh context needs is in this directory tree; it
does not need this conversation's history.

## One-time setup

1. Open Claude Code in a checkout of `mozareeduge/Ganjoor-Ontogrph`, on
   branch `ontograph/v0.1-build` (or wherever this package has landed since
   — check `git log --oneline -- ganjoor-ontograph` if unsure).
2. Confirm the skill is discovered: `.claude/skills/ontograph-build/SKILL.md`
   should show up when you list available skills.

## Starting the build loop

In the fresh session:

```text
/loop /ontograph-build
```

No interval — this lets the model self-pace between iterations (each
iteration is one ledger row; there's no reason to wait a fixed number of
minutes between them, only to avoid polling faster than there's new state
to act on). The loop will:

- read the ledger, implement the next `todo` row, verify it, commit, push,
  and end that turn;
- keep re-invoking itself until `IMPLEMENTATION_LEDGER.md` reports v0.1
  complete (Phase 7's gates re-verified green), at which point the skill
  itself calls the loop's `stop: true` — you don't need to watch for this
  and stop it manually, though you're always free to interrupt and resume
  later (the ledger is the durable state; a fresh `/loop /ontograph-build`
  in a new session picks up exactly where the last one left off).

## Watching progress without babysitting it

Every completed row is a pushed commit against `ontograph/v0.1-build` in
`mozareeduge/Ganjoor-Ontogrph`. Watching that branch's/PR's commit list is
the fastest way to see progress — no need to read every intermediate
session's transcript. `IMPLEMENTATION_LEDGER.md`'s Status column at any
point in time is the authoritative "what's done, what's next, what's
stuck" answer.

## If a row gets stuck

The skill marks a stuck row `blocked` with a specific note rather than
looping forever on it or silently skipping it. If you see a `blocked` row:
read its Notes entry, decide the actual fix or scope change, update the
row yourself (or tell a fresh session what to change), and resume the loop
the same way. A `blocked` row is a normal, expected outcome of real
implementation work — it is not a failure of this package.

## Once Phase 0–7 are done

Phase 8 (real-corpus integration) is intentionally **not** part of the
automated loop, even though this repository is a fork that already vendors
the real `ganjoor-data` corpus at its root (`poets/`, `index/`,
`manifest.json` — no separate clone needed here, unlike when this package
lived elsewhere). It's still excluded from the unattended loop because
pointing the engine at ~132,000 real poems and running the spec's own
worked example (§45) is exploratory, human-in-the-loop work, not another
bounded ledger row. Run it yourself, or explicitly kick off one more
session scoped only to Phase 8's two rows, once you're ready.
