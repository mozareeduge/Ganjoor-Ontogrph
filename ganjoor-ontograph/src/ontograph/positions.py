"""Amendment 20 §3.1/§3.5/§4.1/§4.9: OccurrencePosition -- a positioned,
attributed record of how one assessing object stands toward "may this
Anchor Hit count as an occurrence of this Object Address?" Positions do
not overwrite each other (census.supersede's cross-assessor guard, §3.3);
a hit accumulates a Position Set, and this module computes what that set
means (Standing) without ever collapsing it into a single verdict.
"""
from __future__ import annotations

import json
import uuid as _uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

STANCES = ("occurs", "does-not-occur", "undecidable", "out-of-scope")

# Amendment 20 §9: the one-time mapping from the old adjudication grammar
# to the new position grammar. Shared by migrate.py (one-time explicit
# migration) and census.py (live read-time bridge for un-migrated
# workspaces) so the two paths can never silently drift apart.
STANCE_OF_DECISION = {"accepted": "occurs", "rejected": "does-not-occur", "ambiguous": "undecidable"}


@dataclass(frozen=True)
class OccurrencePosition:
    """One assessor's position on one Anchor Hit (Amendment 20 §3.1).

    `stance` is the position grammar, not the adjudication grammar: it
    describes what the assessor's access shows, never whether that access
    is "accepted." `weight`, when set, is the assessor's OWN self-reported
    confidence -- never a probability of truth, never a resolution
    tiebreaker (see §4.9; its only consumers are triage ordering and an
    optional policy inclusion floor)."""

    id: str
    anchor_hit_id: str
    object_address_id: str
    assessor_object_id: str  # REQUIRED, no default (Amendment 20 §3.1)
    stance: str
    weight: float | None = None
    rationale: str = ""
    apparatus: str = ""
    conditions: dict = None  # type: ignore[assignment]
    created_at: str = ""
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if not self.assessor_object_id:
            raise ValueError(
                "OccurrencePosition.assessor_object_id is required -- "
                "refusing to guess who is positioning (Amendment 20 §3.1/§8.3)"
            )
        if self.stance not in STANCES:
            raise ValueError(f"invalid stance: {self.stance!r} (must be one of {STANCES})")
        if self.weight is not None and not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"weight must be in [0,1] or None, got {self.weight!r}")
        if self.conditions is None:
            object.__setattr__(self, "conditions", {})
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc).isoformat())


def new_position_id() -> str:
    return "op1-" + _uuid.uuid4().hex


def _ledger_path(ws: Path) -> Path:
    return ws / "corpus" / "occurrence-positions.jsonl"


def append_position(ws: Path, position: OccurrencePosition) -> None:
    path = _ledger_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(position), ensure_ascii=False) + "\n")


def read_positions(ws: Path) -> list[OccurrencePosition]:
    path = _ledger_path(ws)
    if not path.exists():
        return []
    out: list[OccurrencePosition] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(OccurrencePosition(**json.loads(line)))
    return out


def position_for(
    ws: Path,
    anchor_hit_id: str,
    object_address_id: str,
    assessor_object_id: str,
    stance: str,
    weight: float | None = None,
    rationale: str = "",
    apparatus: str = "",
    conditions: dict | None = None,
) -> OccurrencePosition:
    """Construct and append a NEW position, automatically superseding this
    assessor's own prior position on this (hit, object) if one exists.
    Refuses (via OccurrencePosition/census-level guards) to touch another
    assessor's position -- there is nothing to touch: this function only
    ever looks up positions BY `assessor_object_id`."""
    existing = read_positions(ws)
    active = active_positions(existing, anchor_hit_id, object_address_id)
    predecessor = active.get(assessor_object_id)
    position = OccurrencePosition(
        id=new_position_id(),
        anchor_hit_id=anchor_hit_id,
        object_address_id=object_address_id,
        assessor_object_id=assessor_object_id,
        stance=stance,
        weight=weight,
        rationale=rationale,
        apparatus=apparatus,
        conditions=conditions or {},
        supersedes=predecessor.id if predecessor else None,
    )
    append_position(ws, position)
    return position


def active_positions(
    positions: list[OccurrencePosition], anchor_hit_id: str, object_address_id: str,
) -> dict[str, OccurrencePosition]:
    """One active position per assessor per hit (census.py §3.3 corollary):
    the latest position in each assessor's own supersession chain, for
    this (hit, object) pair. A position that has been superseded by a
    LATER position from the SAME assessor is not active; a position from
    a DIFFERENT assessor can never supersede it, so every assessor who has
    ever positioned this hit has exactly one entry here."""
    relevant = [
        p for p in positions
        if p.anchor_hit_id == anchor_hit_id and p.object_address_id == object_address_id
    ]
    by_assessor: dict[str, list[OccurrencePosition]] = {}
    for p in relevant:
        by_assessor.setdefault(p.assessor_object_id, []).append(p)
    active: dict[str, OccurrencePosition] = {}
    for assessor_id, chain in by_assessor.items():
        superseded_ids = {p.supersedes for p in chain if p.supersedes}
        live = [p for p in chain if p.id not in superseded_ids]
        # exactly one row should be live per assessor; if the ledger is
        # malformed (e.g. hand-edited), take the most recently written one
        # rather than silently picking an arbitrary one
        live.sort(key=lambda p: p.created_at)
        active[assessor_id] = live[-1] if live else chain[-1]
    return active


def standing_of(
    ws: Path, active: dict[str, OccurrencePosition],
) -> str:
    """Amendment 20 §3.5. Computed on read, never persisted as a fact
    about the hit -- only inside an OperationRecord, correctly scoped to
    that operation's conditions."""
    from ontograph.assessors import independence_classes_of

    if not active:
        return "unpositioned"
    if len(active) == 1:
        return "single-position"
    stances = {p.stance for p in active.values()}
    if len(stances) > 1:
        return "contested"
    classes = independence_classes_of(ws, list(active.keys()))
    return "concordant" if len(classes) >= 2 else "corroborated-weak"


def position_coverage(
    ws: Path,
    eligible_hit_ids: list[str],
    object_address_id: str,
    positions: list[OccurrencePosition] | None = None,
) -> dict:
    """Amendment 20 §4.1: the composition block every object-incidence
    result carries. `by_assessor` counts POSITIONED hits per assessor
    (not raw position rows -- an assessor who repositioned a hit counts
    it once)."""
    positions = read_positions(ws) if positions is None else positions
    by_assessor: dict[str, int] = {}
    positioned_hits = 0
    for hit_id in eligible_hit_ids:
        active = active_positions(positions, hit_id, object_address_id)
        if active:
            positioned_hits += 1
        for assessor_id in active:
            by_assessor[assessor_id] = by_assessor.get(assessor_id, 0) + 1
    return {
        "eligible_hits": len(eligible_hit_ids),
        "positioned_hits": positioned_hits,
        "unpositioned_hits": len(eligible_hit_ids) - positioned_hits,
        "by_assessor": by_assessor,
    }


def standing_distribution(
    ws: Path, eligible_hit_ids: list[str], object_address_id: str,
    positions: list[OccurrencePosition] | None = None,
) -> dict:
    """Amendment 20 §4.1's `standing` block: counts of each Standing value
    across the eligible hit set."""
    positions = read_positions(ws) if positions is None else positions
    counts = {"unpositioned": 0, "single_position": 0, "concordant": 0,
              "corroborated_weak": 0, "contested": 0}
    key_of = {
        "unpositioned": "unpositioned", "single-position": "single_position",
        "concordant": "concordant", "corroborated-weak": "corroborated_weak",
        "contested": "contested",
    }
    for hit_id in eligible_hit_ids:
        active = active_positions(positions, hit_id, object_address_id)
        standing = standing_of(ws, active)
        counts[key_of[standing]] += 1
    return counts


def contested_trace_candidates(
    ws: Path, eligible_hit_ids: list[str], object_address_id: str,
    positions: list[OccurrencePosition] | None = None,
) -> list[dict]:
    """Amendment 20 §2.4: every `contested` hit automatically mints a
    Trace candidate carrying the hit, every position with its apparatus
    and conditions, and (by anchor_hit_id, resolvable by the caller via
    `source show`) a source return. This function does not write the
    Trace record itself -- callers decide whether/how to persist it
    (e.g. cli.py's census/walk paths call records.write_record)."""
    positions = read_positions(ws) if positions is None else positions
    candidates: list[dict] = []
    for hit_id in eligible_hit_ids:
        active = active_positions(positions, hit_id, object_address_id)
        if standing_of(ws, active) != "contested":
            continue
        candidates.append({
            "anchor_hit_id": hit_id,
            "object_address_id": object_address_id,
            "positions": [asdict(p) for p in active.values()],
        })
    return candidates


def queue_by_weight(
    positions: list[OccurrencePosition],
    hit_ids: list[str],
    object_address_id: str,
    order: str = "uncertain-first",
) -> list[str]:
    """Amendment 20 §4.9: order an unpositioned-by-a-human queue by the
    highest-confidence NON-HUMAN position's self-reported `weight`.
    `weight` is never a resolution input (see OccurrencePosition docstring)
    -- this is its only ordering-of-attention role. Hits with no weighted
    non-human position sort last regardless of `order`, since there is
    nothing to prioritize by."""
    if order not in ("confident-first", "uncertain-first"):
        raise ValueError(f"invalid order: {order!r} (confident-first|uncertain-first)")

    def best_weight(hit_id: str) -> float | None:
        active = active_positions(positions, hit_id, object_address_id)
        weights = [p.weight for p in active.values() if p.weight is not None]
        return max(weights) if weights else None

    weighted = [(hid, best_weight(hid)) for hid in hit_ids]
    with_weight = [(hid, w) for hid, w in weighted if w is not None]
    without_weight = [hid for hid, w in weighted if w is None]
    reverse = order == "confident-first"
    with_weight.sort(key=lambda t: t[1], reverse=reverse)
    return [hid for hid, _ in with_weight] + without_weight
