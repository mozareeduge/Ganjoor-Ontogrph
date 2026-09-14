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

RESEARCH_LEDGERS = (
    "research-situations.jsonl",
    "inquiry-catalogs.jsonl",
    "inquiry-reviews.jsonl",
)


class SituationResolutionError(Exception):
    """Preflight refusal: no/ambiguous/unknown situation for a governed
    operation. Raised BEFORE any computation or write."""


def is_governed_workspace(ws: Path) -> bool:
    """W07B shared preflight gate: a workspace with ANY research history
    (situations, catalogs, or reviews) is governed -- analytical commands
    must run under an active situation. The W06 rule (catalogs only) is
    subsumed: catalogs never exist without a situation behind them."""
    research = Path(ws) / "research"
    return any((research / f).exists() for f in RESEARCH_LEDGERS)


def select_governed_situation(ws: Path, explicit_id: str | None) -> str | None:
    """Return the situation a command must run under: None for an
    ungoverned workspace (legacy route stays legal), otherwise the
    deterministic select_situation outcome (refusals included)."""
    if not is_governed_workspace(ws):
        return None
    return select_situation(ws, explicit_id)


def governed_operation_eligible(ws: Path, operation_ids: list[str]) -> tuple[bool, str]:
    """Higher-record eligibility (design §8): every cited OperationRecord
    must EXIST and be `governed`. Missing references (orphans) and
    legacy-unframed records are refused with the reason -- evidence is
    never auto-filled, never retro-linked."""
    from ontograph.operations import GOVERNED, read_operation_records

    records = {r["id"]: r for r in read_operation_records(ws)}
    for op_id in operation_ids:
        record = records.get(op_id)
        if record is None:
            return False, (
                f"operation record not found: {op_id!r} -- orphan references "
                f"cannot support a higher record"
            )
        if record.get("inquiry_status") != GOVERNED:
            return False, (
                f"operation {op_id!r} is legacy-unframed -- it cannot support "
                f"a higher record; remedy is a governed rerun under an active "
                f"situation, never retro-linking history"
            )
    return True, ""


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
