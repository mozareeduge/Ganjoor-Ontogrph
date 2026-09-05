"""Ledger row T07: the walk STATE MACHINE, separated from terminal I/O.

Execution spec T07/T08 locks + §6.3 walk contract:
- pure functions over (state, responses) -> WalkResult; no stdin/stdout
  here. The CLI (cli.py) owns prompting; this module owns semantics.
- responses are IDENTITY-based (`anchor_hit_id` named per response);
  array order is not identity; unknown/stale IDs fail atomically.
- undecided hits are never imputed; resume selects unassessed hits on
  the same snapshot.
- `hit_context` renders the §6.3 context display contract (hit ID,
  progress, poet/title/poem/category/source, verse, couplet, neighbors,
  actions) -- data assembly only; rendering belongs to the CLI.

The existing `ontograph.walk` (P9.5) keeps working unchanged; it can be
rebuilt on top of this module in T08 without repeating its logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ontograph.anchors import AnchorHit, LexicalAnchor
from ontograph.census import HitOccurrenceAssessment, active_decision


WALK_ACTIONS = ("a", "r", "u", "n", "s", "t", "w", "x", "?")

_ACTION_TO_DECISION = {"a": "accepted", "r": "rejected", "u": "ambiguous"}


@dataclass(frozen=True)
class WalkResponse:
    """One identity-based scripted decision (spec §6.3)."""

    anchor_hit_id: str
    action: str  # accepted | rejected | ambiguous (script form)


@dataclass
class WalkState:
    object_address: str
    sample: list[AnchorHit]
    corpus_snapshot_id: str
    resume_ledger: list[HitOccurrenceAssessment] = field(default_factory=list)
    anchors: list = field(default_factory=list)  # active anchors (T08 narrow/split)
    candidate_pool: list[AnchorHit] = field(default_factory=list)  # T08 widen


@dataclass
class WalkResult:
    accepted: int
    rejected: int
    ambiguous: int
    undecided: list[str]  # hit IDs, in sample order
    ledger_rows: list[HitOccurrenceAssessment] = field(default_factory=list)
    # T08 action outputs (empty for pure a/r/u walks)
    anchors: list = field(default_factory=list)  # active anchor list after the action
    superseded_anchor_forms: list[str] = field(default_factory=list)
    new_objects: list[str] = field(default_factory=list)
    trace: dict | None = None
    events: list[dict] = field(default_factory=list)
    sample: list[AnchorHit] = field(default_factory=list)  # sample after widen
    context_level: int | None = None
    context: dict | None = None


@dataclass
class WalkAction:
    """One interactive walk action (spec §6.3 action grammar, T08)."""

    token: str  # a|r|u|n|s|t|w|x|?1..?4|done
    hit_id: str = ""
    form: str = ""  # n: replacement anchor form
    reason: str = ""  # n/s/t: required rationale
    new_object_id: str = ""  # s: second object address id
    note: str = ""  # t: trace note
    rationale: str = ""  # accepted alias for reason (n/s)

    def __post_init__(self) -> None:
        if not self.reason and self.rationale:
            self.reason = self.rationale


def apply_action(state: WalkState, action: WalkAction) -> WalkResult:
    """Apply ONE non-decision action and return the resulting view. These
    are first-class, append-only events (spec §51) -- never silent edits."""
    hit = next((h for h in state.sample if h.id == action.hit_id), None)
    events: list[dict] = []

    if action.token == "n":
        if not action.form or not action.reason:
            raise ValueError("narrow (n) requires --form and a reason")
        old_forms = [a.form for a in state.anchors if a.status == "approved"]
        new_anchor = LexicalAnchor(
            object_address=state.object_address, form=action.form, match_mode="phrase"
            if " " in action.form else "exact", status="approved",
        )
        events.append({
            "kind": "walk-anchor_narrowed", "reason": action.reason,
            "superseded_forms": old_forms, "new_form": action.form,
        })
        return WalkResult(
            accepted=0, rejected=0, ambiguous=0,
            undecided=[h.id for h in state.sample],
            anchors=[new_anchor], superseded_anchor_forms=old_forms,
            events=events, sample=list(state.sample),
        )

    if action.token == "s":
        from ontograph.migrate import validate_object_address_id

        if not action.new_object_id or not action.reason:
            raise ValueError("split (s) requires a new object id and a rationale")
        validate_object_address_id(action.new_object_id)
        events.append({
            "kind": "walk-object_split", "new_object_id": action.new_object_id,
            "rationale": action.reason, "hit_id": action.hit_id,
        })
        return WalkResult(
            accepted=0, rejected=0, ambiguous=0,
            undecided=[h.id for h in state.sample],  # hit stays undecided
            new_objects=[action.new_object_id], events=events,
            sample=list(state.sample),
        )

    if action.token == "t":
        if not action.note:
            raise ValueError("trace (t) requires a note")
        trace = {
            "anchor_hit_id": action.hit_id,
            "object_address_id": state.object_address,
            "note": action.note,
            "source_return": _source_return(hit) if hit else {},
        }
        events.append({"kind": "walk-trace_promoted", "hit_id": action.hit_id})
        return WalkResult(
            accepted=0, rejected=0, ambiguous=0,
            undecided=[h.id for h in state.sample],
            trace=trace, events=events, sample=list(state.sample),
        )

    if action.token == "w":
        pool = state.candidate_pool or state.sample
        # deterministic enlargement: next unshown hits in pool order
        shown = {h.id for h in state.sample}
        additions = [h for h in pool if h.id not in shown][: max(1, len(pool) // 2)]
        new_sample = list(state.sample) + additions
        return WalkResult(
            accepted=0, rejected=0, ambiguous=0,
            undecided=[h.id for h in new_sample],
            sample=new_sample,
        )

    if action.token.startswith("?"):
        level = int(action.token[1:])
        if level not in (1, 2, 3, 4):
            raise ValueError(f"invalid context level: {level}")
        from ontograph.walk_state import hit_context

        ctx = hit_context(
            hit, sample_size=len(state.sample),
            position=([h.id for h in state.sample].index(action.hit_id) + 1) if hit else 0,
        )
        return WalkResult(
            accepted=0, rejected=0, ambiguous=0,
            undecided=[h.id for h in state.sample],
            context_level=level, context=ctx, sample=list(state.sample),
        )

    raise ValueError(f"unsupported walk action token: {action.token!r}")


def _source_return(hit: AnchorHit) -> dict:
    """Minimal source-return payload for a Trace (poem coordinates; the
    CLI resolves the full passage via `source show`)."""
    return {
        "poem_id": hit.poem_id,
        "verse_order": hit.verse_order,
        "couplet_index": hit.couplet_index,
        "match_span": [hit.token_start, hit.token_end],
        "corpus_snapshot_id": hit.corpus_snapshot_id,
    }


def run_walk(state: WalkState, responses: list[WalkResponse]) -> WalkResult:
    """Apply identity-based responses to the sample. Fails atomically on
    any unknown/stale hit ID (nothing is applied)."""
    sample_ids = {h.id for h in state.sample}
    unknown = [r.anchor_hit_id for r in responses if r.anchor_hit_id not in sample_ids]
    if unknown:
        raise ValueError(
            f"stale/unknown anchor_hit_id(s) in responses: {unknown[:3]}... "
            f"scripts must name hit IDs from corpus snapshot {state.corpus_snapshot_id}"
        )
    # already-assessed hits (resume): active decisions on the same snapshot
    assessed_ids: set[str] = set()
    for h in state.sample:
        active = active_decision(state.resume_ledger, h.id)
        if active is not None and active.assessor_type != "legacy-poem-decision":
            assessed_ids.add(h.id)

    decisions: dict[str, str] = {}
    for r in responses:
        if r.anchor_hit_id in assessed_ids:
            continue
        decisions[r.anchor_hit_id] = r.action

    accepted = sum(1 for d in decisions.values() if d == "accepted")
    rejected = sum(1 for d in decisions.values() if d == "rejected")
    ambiguous = sum(1 for d in decisions.values() if d == "ambiguous")

    ledger_rows = [
        HitOccurrenceAssessment(
            id=f"oa-walk-{i}",
            anchor_hit_id=hid,
            object_address_id=state.object_address,
            decision=decisions[hid],
            assessor_type="human",
        )
        for i, hid in enumerate(decisions)
    ]
    # Resume semantics (T07 lock): already-assessed hits are neither
    # re-asked nor listed as undecided -- resume selects the active
    # UNASSESSED hits on the same snapshot.
    undecided = [
        h.id for h in state.sample
        if h.id not in decisions and h.id not in assessed_ids
    ]
    return WalkResult(
        accepted=accepted, rejected=rejected, ambiguous=ambiguous,
        undecided=undecided, ledger_rows=ledger_rows,
    )


def hit_context(
    hit: AnchorHit,
    sample_size: int,
    position: int,
    poet: str = "",
    title: str = "",
    category: str = "",
    source: str = "",
) -> dict:
    """Assemble the §6.3 context display contract for one hit. Pure data;
    the CLI renders it."""
    return {
        "anchor_hit_id": hit.id,
        "progress": f"{position}/{sample_size}",
        "poet": poet,
        "title": title,
        "poem_id": hit.poem_id,
        "category": category,
        "source": source,
        "verse": hit.original_text,
        "couplet_index": hit.couplet_index,
        "normalized_text": hit.normalized_text,
        "match_span": [hit.token_start, hit.token_end],
        "actions": list(WALK_ACTIONS),
    }


def build_script_template(
    object_address_id: str, corpus_snapshot_id: str, sample: list[AnchorHit]
) -> dict:
    """Identity-based script skeleton (spec §6.3): the researcher (or the
    agent) fills `action` per hit; IDs come from the snapshot, never from
    array position."""
    return {
        "schema_version": "1.0",
        "object_address_id": object_address_id,
        "corpus_snapshot_id": corpus_snapshot_id,
        "responses": [{"anchor_hit_id": h.id, "action": ""} for h in sample],
    }
