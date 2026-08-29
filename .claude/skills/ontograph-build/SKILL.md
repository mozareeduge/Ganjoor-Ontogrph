---
name: ontograph-build
description: Drives one bounded iteration of implementing the Ganjoor Ontograph engine/CLI/skill from the implementation ledger. Use when asked to build, continue building, or finish the Ganjoor Ontograph project, or when invoked via /loop for that purpose. Not for using the finished apparatus to research something — that's persian-poetry-ontograph.
version: 0.1.0
author: Mohammad Zare
license: MIT
metadata:
  hermes:
    tags: [persian, poetry, ontograph, build, implementation]
    related_skills: [persian-poetry-ontograph]
---

# ontograph-build

You have no memory of any prior session. Everything you need is in this
file and in the four files it points to. Read them in this order before
doing anything else:

1. `ganjoor-ontograph/Ganjoor_Ontograph_Research_Apparatus_Project_Spec_v2.3.0.md` — the spec. Authoritative for *what* to build and *why*.
2. `ganjoor-ontograph/USER_JOURNEY.md` — the concrete UX target. If an implementation choice would make one of its example outputs impossible to produce, the choice is wrong, not the document.
3. `ganjoor-ontograph/implementation/BUILD_PLAN.md` — phases, rationale, engineering defaults, definition of done.
4. `ganjoor-ontograph/implementation/IMPLEMENTATION_LEDGER.md` — the exact task list. This is the only file you edit for task-tracking purposes; do not invent a second progress-tracking mechanism.

## What one iteration does

1. Open `IMPLEMENTATION_LEDGER.md`. Find the **first** row, top to bottom
   across all phases, with `Status: todo`. Rows are already in dependency
   order — do not skip ahead to an easier-looking later row, and do not
   start a row whose `Depends-on`/Notes reference an earlier row that
   isn't `done` yet.
2. If no `todo` row exists anywhere above Phase 8:
   - Re-run every Verify command in Phase 7 once, fresh (don't trust old
     output). If all pass: this is **v0.1 complete**. Write a short
     completion note at the top of `IMPLEMENTATION_LEDGER.md` (date, what
     passed), commit and push it, and — **if you are running under
     `/loop`, call `ScheduleWakeup` with `stop: true` instead of scheduling
     another wakeup.** Do not keep looping once the ledger is clean; that
     wastes the user's time and money for no further progress. Report
     completion to the user in your final message.
   - If something that was `done` now fails re-verification: treat it as
     a new blocker — flip its Status to `blocked`, add a Notes entry
     explaining what broke, and stop this iteration there (this is more
     important than starting new work; a regression in a "done" row means
     something upstream changed and needs attention before anything else
     is trustworthy).
3. Otherwise, take that one row:
   - Mark it `in-progress` in the ledger (small commit, or fold into the
     same commit as the work — your choice, but the ledger update and the
     code must land together).
   - Implement exactly what the row describes, using the spec section(s)
     it cites as the authority for behavior. If the row and the spec seem
     to disagree, the spec wins — flag the discrepancy in Notes rather
     than silently picking one.
   - Run the row's Verify command yourself. Do not mark `done` on the
     strength of "this should work."
   - If Verify passes: flip Status to `done`, commit (small, scoped commit
     message referencing the row ID, e.g. "P1.5: exact AnchorHit census"),
     push, and **stop this iteration** — one row per turn, even if the next
     row looks trivial. This keeps every iteration reviewable in the PR
     diff and keeps context bounded.
   - If Verify fails after a reasonable attempt: mark the row `blocked`
     with a specific, actionable Notes entry (what you tried, what failed,
     what would unblock it — not just "doesn't work"). Do not leave a
     `todo` row half-implemented in an uncommitted or broken state; either
     finish it to `done` or roll back to a clean `blocked` state before
     stopping the iteration.
4. Never mark a row `done` by weakening its Verify command, deleting a
   failing assertion, or narrowing what it tests until it happens to pass.
   That is the same failure mode the spec itself guards against in
   Appendix A (a passing check that quietly stopped checking the thing it
   was supposed to check is worse than a visible `blocked`).

## Engineering constraints that apply to every row

- Follow `BUILD_PLAN.md`'s "Provisional engineering defaults" section
  exactly (Python, pytest, SQLite, JSONL/YAML, the fixture corpus) — don't
  introduce a different stack mid-build.
- Use `ganjoor-ontograph/fixtures/mini-ganjoor/` for every automated test.
  Never clone or depend on the real multi-GB corpora inside an automated
  loop iteration — that's Phase 8, explicitly manual, explicitly out of
  this skill's scope.
- If a row's Verify needs a fixture case that doesn't exist yet (e.g. a
  birth/death-year field the fixture poets don't have), add the minimal
  fixture data needed and note it in the ledger row rather than skipping
  the row or weakening the test.
- Keep `references/` and `templates/` in
  `.claude/skills/persian-poetry-ontograph/` in sync if a row changes a
  record shape they describe — that skill is the eventual researcher-facing
  interface to what you're building here.
- Per repo convention (see `../../ganjoor-ontograph/EVALUATION.md` and the
  spec's own Appendix A discipline): never silently narrow scope, never
  claim a gate passed without having actually run it this iteration, never
  invent a methodological shortcut not in the spec.

## Stopping conditions (read this before your first iteration)

- **Normal stop:** one ledger row done, committed, pushed → end the turn.
- **Completion stop:** no `todo` rows left, Phase 7 gates re-verified green
  → mark complete, and if under `/loop`, call `ScheduleWakeup` with
  `stop: true`.
- **Blocked stop:** a row can't pass Verify after a real attempt → mark
  `blocked` with specifics, commit, end the turn. A blocked row does not
  halt the whole loop — the *next* iteration should look for a different
  `todo` row that doesn't depend on the blocked one, or, if everything
  remaining depends on it, report that clearly rather than silently idling.
