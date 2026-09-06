"""W07A: governed operation context -- pure situation selection.

Wiring into verbs/status is W07B (next row); this module is ONLY the
schema-side helpers and the deterministic, side-effect-free selector so
the preflight can be unit-tested without touching any command.

Amendment §19.2 selection rule (deterministic, never recency):
- exactly one ACTIVE situation -> inherit it;
- zero active -> refuse, the message names `inquire` as the remedy;
- several active -> refuse without an explicit --situation ID;
- explicit ID must name an EXISTING, ACTIVE situation (a superseded ID
  is refused even explicitly while an active situation exists).
"""
from __future__ import annotations

from pathlib import Path

from ontograph.records_v2 import read_situations


class SituationResolutionError(Exception):
    """Preflight refusal: no/ambiguous/unknown situation for a governed
    operation. Raised BEFORE any computation or write."""


def select_situation(workspace: Path, situation_id: str | None) -> str:
    """Return the situation ID a governed command must run under.

    Pure read over the situation ledger; raises SituationResolutionError
    on every ambiguous/unsupported input (never silently picks).
    """
    situations = read_situations(workspace)
    active = [s for s in situations if s.status != "superseded"]

    if situation_id is None:
        if len(active) == 1:
            return active[0].id
        if not active:
            raise SituationResolutionError(
                "no active ResearchSituation in this workspace -- "
                "run 'ontograph inquire' first (governed operations "
                "require a situation; legacy-unframed rows cannot "
                "support higher records)"
            )
        raise SituationResolutionError(
            f"{len(active)} active situations found "
            f"({', '.join(sorted(s.id for s in active))}) -- pass "
            f"--situation <id> explicitly; selection is never by recency"
        )

    named = next((s for s in situations if s.id == situation_id), None)
    if named is None:
        raise SituationResolutionError(
            f"situation not found: {situation_id!r}"
        )
    if named.status == "superseded":
        raise SituationResolutionError(
            f"situation {situation_id!r} is superseded -- superseded "
            f"situations cannot frame new operations"
        )
    return named.id
