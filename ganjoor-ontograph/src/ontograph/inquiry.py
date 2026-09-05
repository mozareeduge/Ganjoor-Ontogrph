"""Ledger row W01 (Amendment §19.3): InquiryCatalog + InquiryReview —
isolated append-only candidate stores.

The catalog is a proposal envelope; candidates are candidate-tier by
construction. Validation closes the bypasses named in the amendment:
- kinds restricted to the five declared values;
- support_status restricted to supported|unsupported|not-applicable
  (an agent can never write 'assumed' or 'verified-by-fluency');
- supported requires at least one CandidateEvidenceRef (located verse);
- every candidate names its proposer (type + id) and rationale;
- reviews are human-actor records with a receipt; the decision space is
  exactly accept | accept-unsupported | reject | defer | revise | split.

`records_v2_guard.generic_record_add_allowed` is the machine-store
refusal list the generic record route consults (W06 wires the CLI).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

CATALOGS_REL = "research/inquiry-catalogs.jsonl"
REVIEWS_REL = "research/inquiry-reviews.jsonl"

CANDIDATE_KINDS = ("seed-object", "lexical-anchor", "authored-contrast",
                   "non-object-note", "lexical-neighbor")
SUPPORT_STATUSES = ("supported", "unsupported", "not-applicable")
REVIEW_DECISIONS = ("accept", "accept-unsupported", "reject", "defer", "revise", "split")

# stores the generic record route may never write (machine-managed)
MACHINE_MANAGED_STORES = frozenset({
    "inquiry-catalogs", "inquiry-reviews", "occurrence-assessments",
    "operations", "mappings", "relation-objects", "claims",
    "research-situations", "seeds", "descriptive-catalogs",
})


def generic_record_add_allowed(store_type: str) -> bool:
    return store_type not in MACHINE_MANAGED_STORES


def _new_id(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


@dataclass(frozen=True)
class CandidateEvidenceRef:
    path: str
    poem_id: int
    verse_order: int
    couplet_index: int | None
    match_span: list[int]
    corpus_snapshot_id: str


@dataclass(frozen=True)
class InquiryCandidate:
    candidate_id: str
    kind: str
    form: str
    proposer_type: str
    proposer_id: str
    rationale: str
    support_status: str
    hit_count: int = 0
    poem_count: int = 0
    poet_count: int = 0
    evidence: list[CandidateEvidenceRef] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind not in CANDIDATE_KINDS:
            raise ValueError(f"invalid candidate kind: {self.kind!r}")
        if self.support_status not in SUPPORT_STATUSES:
            raise ValueError(f"invalid support_status: {self.support_status!r}")
        if not self.proposer_type or not self.proposer_id or not self.rationale:
            raise ValueError("attribution required: proposer type/id + rationale")
        if self.support_status == "supported":
            if self.hit_count <= 0 or not self.evidence:
                raise ValueError(
                    "supported candidates need positive counts and at least one "
                    "located evidence reference (never assert support without a pointer)"
                )
        if self.support_status != "not-applicable" and not self.form:
            raise ValueError("lexical candidates carry a form")


@dataclass(frozen=True)
class InquiryCatalog:
    study_id: str
    situation_id: str
    corpus_snapshot_id: str
    field_id: str
    scope_spec: dict
    parameters: dict
    limitations: list[str]
    candidates: list[InquiryCandidate]
    supersedes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", _new_id("ic"))
        if not self.study_id or not self.situation_id:
            raise ValueError("catalog requires study_id + situation_id")


@dataclass(frozen=True)
class InquiryReview:
    catalog_id: str
    situation_id: str
    candidate_id: str
    decision: str
    actor: str
    rationale: str
    receipt: str
    predecessor: str | None = None
    outputs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.decision not in REVIEW_DECISIONS:
            raise ValueError(f"invalid review decision: {self.decision!r}")
        if not self.actor or not self.rationale or not self.receipt:
            raise ValueError("review requires human actor, rationale, and receipt")


def _persist(path: Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def persist_catalog(workspace: Path, catalog: InquiryCatalog) -> Path:
    p = Path(workspace) / CATALOGS_REL
    _persist(p, catalog)
    return p


def read_catalogs(workspace: Path) -> list[InquiryCatalog]:
    p = Path(workspace) / CATALOGS_REL
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        d["candidates"] = [
            InquiryCandidate(**{**c, "evidence": [CandidateEvidenceRef(**e) for e in c["evidence"]]})
            for c in d["candidates"]
        ]
        out.append(InquiryCatalog(**d))
    return out


def persist_review(workspace: Path, review: InquiryReview) -> Path:
    p = Path(workspace) / REVIEWS_REL
    _persist(p, review)
    return p


def read_reviews(workspace: Path) -> list[InquiryReview]:
    p = Path(workspace) / REVIEWS_REL
    if not p.exists():
        return []
    return [
        InquiryReview(**json.loads(l))
        for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
