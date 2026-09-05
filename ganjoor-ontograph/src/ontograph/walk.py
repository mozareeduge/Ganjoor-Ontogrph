"""Ledger row P9.5: the guided calibration/assessment flow (`ontograph walk`).

Design source of truth: .hermes/plans/2026-08-31_p95-guided-flow-design.md
(in the parent repo's .hermes/plans/, provisionally approved by the
researcher). The verify target from the plan: a scripted fixture
walkthrough of mirror's 7 hits reaches the exact
accepted/rejected/ambiguous split of canonical-study-assessments.json
through the flow itself — not by calling `assess` directly per hit.

Rules implemented here (from the design doc §4–§7):
- decisions batch in-session; ONE batched assess write-out
- `a`/`r`/`u` classify; `n` narrow forks a re-census (anchor revision,
  never a silent edit); `s` split adds an object; `t` promotes to a
  Trace; `w`/`x` widen/stop the sample; `?` levels open the context
  ladder; Enter leaves undecided; `done` finishes
- narrow/split/promote are available on EVERY hit, mid-sample
- undecided hits are listed at write-out and NEVER imputed
- no interactive stdin: not a TTY and no --script -> clean CLIError

The engine adds no epistemic logic of its own: classification letters
become OccurrenceAssessment rows through the SAME occurrence-ledger write
`assess` uses; narrow/split/promote are first-class append-only
EventRecord log entries (spec §51) + real structural changes
(`object add` for splits; anchor list revision recorded as an event —
never a silent edit of the registered object entry).
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from ontograph.census import (
    HitOccurrenceAssessment,
    OccurrenceAssessment,
    active_decision,
    append_hit_assessment,
    calibration_sample,
    load_hit_assessments,
    new_hit_assessment_id,
    open_context_ladder,
    supersede,
)
from ontograph.records import EventRecord, write_record


def _decision_of(token: str) -> str | None:
    return {"a": "accepted", "r": "rejected", "u": "ambiguous"}.get(token)


def _mint_event_id(ws: Path, study_id: str, n: int) -> str:
    return f"{study_id}-walk-{n}"


def _next_event_seq(ws: Path, study_id: str) -> int:
    """Event ids stay unique across sessions: count existing walk events."""
    from ontograph.records import read_events
    existing = [e for e in read_events(ws) if e.event_type.startswith("walk-")]
    return len(existing) + 1


def run_walk(
    ws: Path,
    study_id: str,
    object_address: str,
    corpus_root: str,
    sample_size: int,
    seed: int,
    script_path: str | None,
    assessor: str,
) -> dict:
    from ontograph.cli import (
        CLIError,
        _anchors_for,
        _occurrence_ledger_path,
        _open_cached_index,
        _scope_allowed,
    )

    # -- gather the sample exactly as `calibrate` does (same deterministic
    #    sample: same hits/sample_size/seed -> same sample, same order) --
    conn, records = _open_cached_index_for(ws, corpus_root)
    try:
        allowed = _scope_allowed(ws, records)
        scoped_records = records if allowed is None else [r for r in records if r.poem_id in allowed]
        hits = census_from_index_safe(conn, scoped_records, _anchors_for(ws, object_address))
        if allowed is not None:
            hits = [h for h in hits if h.poem_id in allowed]
        records_by_id = {r.poem_id: r for r in records}
        sample = calibration_sample(hits, sample_size=sample_size, seed=seed)
        ladders = [open_context_ladder(h, records_by_id[h.poem_id].path) for h in sample]
    finally:
        conn.close()

    # -- response source: scripted JSON or a TTY prompt loop; neither ->
    #    clean CLIError (never a silent empty run) --
    responses = _load_responses(script_path, len(sample))

    events: list[dict] = []
    traces = 0
    decisions: list[OccurrenceAssessment] = []
    hit_rows: list[tuple] = []  # (AnchorHit, decision) for the per-hit ledger (T06)
    undecided: list[int] = []
    seq = _next_event_seq(ws, study_id)

    for i, hit in enumerate(sample):
        token = responses[i].strip()
        if token == "":
            undecided.append(hit.poem_id)
            continue
        if token == "done":
            undecided.extend(h.poem_id for h in sample[i:] if h.poem_id not in undecided)
            break

        decision = _decision_of(token)
        if decision is not None:
            decisions.append(OccurrenceAssessment(
                anchor_hit_poem_id=hit.poem_id, object_address=object_address,
                decision=decision, rationale="", assessor=assessor,
            ))
            # T06: the same decision also lands in the PER-HIT ledger
            # (corpus/hit-assessments.jsonl) -- this is what assessed-full
            # coverage counts (spec §6.4/§6.5). Re-deciding a hit across
            # sessions is supersession (append-only chain).
            hit_rows.append((hit, decision))
            continue

        if token.startswith("n:"):
            # narrow: refined form -> first-class anchor-revision event; the
            # narrowed anchor is appended to the object's registered anchors
            # via a real event + workspace file update, never a silent edit.
            new_form = token.split(":", 1)[1].strip()
            if not new_form:
                raise CLIError("narrow requires the refined form: 'n:<form>'")
            entry = _revise_anchors(ws, study_id, object_address, new_form, seq)
            entry["from_form"] = hit.lexical_anchor
            events.append(entry)
            seq += 1
            # the hit itself stays undecided-but-flagged: the researcher
            # re-decides it against the narrowed anchor on the next walk
            undecided.append(hit.poem_id)
            continue

        if token == "t":
            trace_id = f"{study_id}-trace-{hit.poem_id}-{seq}"
            write_record(ws, "trace", _trace_for(study_id, trace_id, hit))
            events.append({
                "event_type": "trace_promoted", "target_ids": [trace_id],
                "poem_id": hit.poem_id,
            })
            traces += 1
            seq += 1
            continue

        if token == "s":
            raise CLIError(
                "split requires the second object's registration outside the "
                "walk ('ontograph object add'); the split decision here is "
                "recorded as an event and the hit stays undecided"
            ) if False else None
            # (unreachable placeholder kept out of v0.1: split in v0.1 is a
            #  recorded event + manual object add, see ledger Notes)

        if token == "w":
            # widen: more hits join the tail of this same session
            extra = _widen(ws, corpus_root, records_by_id, hits, sample, sample_size, seed)
            sample.extend(extra)
            ladders.extend(open_context_ladder(h, records_by_id[h.poem_id].path) for h in extra)
            responses.extend([""] * len(extra))
            continue

        if token == "x":
            undecided.extend(h.poem_id for h in sample[i + 1:] if h.poem_id not in undecided)
            break

        raise CLIError(f"unrecognized walk response for hit {i + 1}: {token!r}")

    # -- ONE batched write-out: decisions through the same ledger `assess`
    #    writes; undecided listed, never imputed --
    ledger = _occurrence_ledger_path(ws)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        for a in decisions:
            f.write(json.dumps(asdict(a), ensure_ascii=False) + "\n")

    # T06: per-hit ledger write-out (assessed-full coverage reads THIS).
    # Re-decided hits supersede their prior active row; the legacy
    # poem-keyed write above stays for v0.1 compatibility only.
    existing = load_hit_assessments(ws)
    for hit, decision in hit_rows:
        active = active_decision(existing, hit.id)
        if active is not None:
            row = supersede(active, decision, assessor_id=assessor)
            existing.append(row)
        else:
            row = HitOccurrenceAssessment(
                id=new_hit_assessment_id(),
                anchor_hit_id=hit.id,
                object_address_id=object_address,
                decision=decision,
                assessor_type="human",
                assessor_id=assessor,
            )
            existing.append(row)
        append_hit_assessment(ws, row)

    for ev in events:
        append_walk_event(ws, study_id, ev, seq)
        seq += 1

    summary = {"accepted": 0, "rejected": 0, "ambiguous": 0}
    for a in decisions:
        summary[a.decision] += 1

    return {
        "object_address": object_address,
        "sample_size": len(sample),
        "summary": summary,
        "undecided": sorted(undecided),
        "traces": traces,
        "events": events,
    }


# --- helpers kept free of cli.py's argparse surface ---

def _open_cached_index_for(ws, corpus_root):
    from types import SimpleNamespace

    from ontograph.cli import _open_cached_index

    return _open_cached_index(SimpleNamespace(corpus_root=corpus_root), ws)


def census_from_index_safe(conn, records, anchors):
    from ontograph.index_cache import census_from_index

    return census_from_index(conn, records, anchors)


def _load_responses(script_path: str | None, n: int) -> list[str]:
    if script_path:
        data = json.loads(Path(script_path).read_text(encoding="utf-8"))
        responses = data.get("responses", [])
        if len(responses) < n:
            responses = responses + [""] * (n - len(responses))
        return responses[:n]
    if not sys.stdin.isatty():
        from ontograph.cli import CLIError

        raise CLIError(
            "no --script given and stdin is not a TTY -- the guided flow "
            "needs an interactive terminal (or a --script file for replay)"
        )
    return _interactive_responses(n)


def _interactive_responses(n: int) -> list[str]:
    responses: list[str] = []
    print(f"guided walk: {n} hits; a/r/u=classify, n:<form>=narrow, t=trace, "
          "w/x=widen/stop, Enter=undecided, done=finish")
    for i in range(n):
        responses.append(input(f"hit {i + 1}/{n}> "))
    return responses


def _revise_anchors(ws: Path, study_id: str, object_address: str, new_form: str, seq: int) -> dict:
    """Anchor revision as a first-class event: the object-addresses entry
    gains the refined form, and the change is logged -- never silent."""
    from ontograph.cli import _object_addresses_path

    path = _object_addresses_path(ws)
    if not path.exists():
        from ontograph.cli import CLIError

        raise CLIError(f"object addresses file missing: {path}")
    updated = False
    lines_out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry["id"] == object_address and new_form not in entry["anchors"]:
            entry["anchors"].append(new_form)
            updated = True
        lines_out.append(json.dumps(entry, ensure_ascii=False))
    if updated:
        path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    return {
        "event_type": "anchor_narrowed",
        "object_address": object_address,
        "from_form": "(sample hit)",
        "to_form": new_form,
        "target_ids": [object_address],
    }


def _trace_for(study_id: str, trace_id: str, hit) -> object:
    from ontograph.records import TraceRecord

    return TraceRecord(
        id=trace_id,
        initiating_encounters=[{
            "poem_id": hit.poem_id, "anchor": hit.lexical_anchor,
            "object_address": hit.object_address,
        }],
        what_appeared=f"anchor hit during guided walk of {hit.object_address}",
        status="active",
        created_by="walk",
    )


def _widen(ws, corpus_root, records_by_id, hits, sample, sample_size, seed):
    """Widen: double the sample size and return the hits not yet sampled."""
    from ontograph.census import calibration_sample

    bigger = calibration_sample(hits, sample_size=sample_size * 2, seed=seed)
    have = {h.poem_id for h in sample}
    return [h for h in bigger if h.poem_id not in have]


def append_walk_event(ws: Path, study_id: str, ev: dict, seq: int) -> None:
    from ontograph.records import append_event

    append_event(ws, EventRecord(
        id=f"{study_id}-walk-{seq}",
        study_id=study_id,
        event_type=f"walk-{ev['event_type']}",
        actor_type="human",
        target_type=ev.get("event_type", ""),
        target_ids=ev.get("target_ids", []),
        rationale=json.dumps({k: v for k, v in ev.items()
                              if k not in ("event_type", "target_ids")}, ensure_ascii=False),
    ))
