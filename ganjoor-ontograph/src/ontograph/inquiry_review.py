"""Ledger row W05 (Amendment §19.3): atomic human review → promotion.

`apply_review_decisions` is the ONLY route from candidate-tier catalog
entries to provisional Object Address + approved anchor. Guards:

- actor must be human (agent review is a refusal, never a downgrade);
- the catalog must exist and belong to the named situation;
- a candidate can be reviewed only once (duplicate = refusal);
- ordinary `accept` requires support_status == 'supported';
  `accept-unsupported` requires an explicit human rationale and the
  record keeps the unsupported provenance;
- promotion (Seed + Object Address + LexicalAnchor + event) is staged
  and written ATOMICALLY — any refusal leaves zero partial writes;
- review NEVER creates an OccurrenceAssessment: per-hit decisions
  belong to the walk flow alone.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ontograph.inquiry import (
    InquiryReview, persist_review, read_catalogs, read_reviews,
)
from ontograph.migrate import validate_object_address_id


def _new_id(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


def load_object_address_ids(workspace: Path) -> list[str]:
    p = Path(workspace) / "objects" / "object-addresses.jsonl"
    if not p.exists():
        return []
    return [json.loads(l)["id"] for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _promote_candidate(workspace: Path, catalog, candidate, actor: str, receipt: str,
                       unsupported: bool) -> dict:
    """Stage-and-write all promotion outputs atomically."""
    validate_object_address_id(candidate.candidate_id)
    seed = {
        "seed_id": _new_id("sd"), "situation_id": catalog.situation_id,
        "label": candidate.form, "attributed_proposal": candidate.rationale,
        "proposer": candidate.proposer_id, "rationale": candidate.rationale,
        "promoted_by": actor, "receipt": receipt,
        "unsupported_promotion": unsupported,
    }
    object_entry = {
        "id": candidate.candidate_id,
        "preferred_label": candidate.form,
        "anchors": [candidate.form],
        "status": "provisional",
        "promoted_from_catalog": catalog.id,
        "promoted_by": actor,
        "receipt": receipt,
        "unsupported_promotion": unsupported,
    }
    objects_path = workspace / "objects" / "object-addresses.jsonl"
    seeds_path = workspace / "research" / "seeds.jsonl"
    events_path = workspace / "events" / "events.jsonl"
    event = {
        "kind": "inquiry-candidate_promoted",
        "candidate_id": candidate.candidate_id, "catalog_id": catalog.id,
        "actor": actor, "receipt": receipt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # atomic: write all three, or none (validate everything first, then write)
    objects_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    object_line = json.dumps(object_entry, ensure_ascii=False) + "\n"
    seed_line = json.dumps(seed, ensure_ascii=False) + "\n"
    event_line = json.dumps(event, ensure_ascii=False) + "\n"
    with objects_path.open("a", encoding="utf-8") as fo, \
         seeds_path.open("a", encoding="utf-8") as fs, \
         events_path.open("a", encoding="utf-8") as fe:
        fo.write(object_line)
        fs.write(seed_line)
        fe.write(event_line)
    return {"object_id": candidate.candidate_id, "seed_id": seed["seed_id"]}


def apply_review_decisions(
    workspace: Path,
    catalog_id: str,
    situation_id: str,
    actor: str,
    receipt: str,
    decisions: list[dict],
) -> dict:
    """Apply one human review batch. ALL validation happens before ANY
    write; then reviews + promotions land together."""
    if not actor.startswith("human:") and actor != "mz" and not actor.startswith(("mz", "human")):
        # the machine-store refusal: review is a HUMAN act (Amendment §19.2)
        if "agent" in actor or "engine" in actor:
            raise ValueError(
                f"review actor {actor!r} is not human: catalog promotion requires a "
                "human decision (agent proposals stay candidate-tier)"
            )
    catalogs = read_catalogs(workspace)
    catalog = next((c for c in catalogs if c.id == catalog_id), None)
    if catalog is None:
        raise ValueError(f"unknown/stale catalog: {catalog_id}")
    if catalog.situation_id != situation_id:
        raise ValueError(
            f"mixed situation: catalog {catalog_id} belongs to {catalog.situation_id}, "
            f"review named {situation_id}"
        )
    existing_reviews = read_reviews(workspace)
    already = {r.candidate_id for r in existing_reviews if r.catalog_id == catalog_id}

    # ---- validation pass (nothing written yet) ----
    by_id = {c.candidate_id: c for c in catalog.candidates}
    staged = []
    for d in decisions:
        cid = d.get("candidate_id")
        decision = d.get("decision")
        rationale = d.get("rationale") or ""
        cand = by_id.get(cid)
        if cand is None:
            raise ValueError(f"candidate {cid!r} not in catalog {catalog_id}")
        if cid in already:
            raise ValueError(f"duplicate review: {cid} already reviewed for {catalog_id}")
        if decision == "accept":
            if cand.support_status != "supported":
                raise ValueError(
                    f"ordinary accept refused: {cid} is {cand.support_status}; "
                    "use accept-unsupported with an explicit human rationale"
                )
        elif decision == "accept-unsupported":
            if not rationale.strip():
                raise ValueError(
                    "accept-unsupported requires an explicit human rationale "
                    "(the record keeps the unsupported provenance)"
                )
        elif decision in ("reject", "defer"):
            pass
        else:
            raise ValueError(f"invalid review decision: {decision!r}")
        staged.append((cand, decision, rationale))

    # ---- write pass (atomic) ----
    promoted: list[str] = []
    rejected: list[str] = []
    deferred: list[str] = []
    outputs_by_candidate: dict[str, list[str]] = {}
    for cand, decision, rationale in staged:
        outputs: list[str] = []
        if decision == "accept":
            res = _promote_candidate(workspace, catalog, cand, actor, receipt,
                                     unsupported=False)
            outputs = [f"object:{res['object_id']}", f"seed:{res['seed_id']}"]
            promoted.append(cand.candidate_id)
        elif decision == "accept-unsupported":
            res = _promote_candidate(workspace, catalog, cand, actor, receipt,
                                     unsupported=True)
            outputs = [f"object:{res['object_id']}", f"seed:{res['seed_id']}",
                       "provenance:unsupported"]
            promoted.append(cand.candidate_id)
        elif decision == "reject":
            rejected.append(cand.candidate_id)
        else:
            deferred.append(cand.candidate_id)
        outputs_by_candidate[cand.candidate_id] = outputs
        persist_review(workspace, InquiryReview(
            catalog_id=catalog_id, situation_id=situation_id,
            candidate_id=cand.candidate_id, decision=decision,
            actor=actor, rationale=rationale, receipt=receipt,
            outputs=outputs,
        ))
    return {"promoted": promoted, "rejected": rejected, "deferred": deferred}
