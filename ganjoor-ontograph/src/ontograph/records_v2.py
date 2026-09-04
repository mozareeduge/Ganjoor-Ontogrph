"""U03 (Amendment §19.8, narrowed): validated ResearchSituation + Seed
record schemas with append-only persistence.

These are the governance preflight records: a situation captures the
verbatim hunch BEFORE any analysis; seeds are attributed candidate-tier
proposals. Everything here is deliberately inert — no census, no
anchors, no CLI. W02–W03 build `inquire` on top.

Validation refuses invalid records BEFORE any write (no partial lines).
Statuses: situational | superseded. 'assessed' is structurally
impossible — these records are candidate-tier by construction (Amendment
§19.1: agent authorship stays visible).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path

SITUATIONS_REL = "research/research-situations.jsonl"
SEEDS_REL = "research/seeds.jsonl"

_SITUATION_STATUSES = ("situational", "superseded")


def _new_id(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


@dataclass(frozen=True)
class ResearchSituation:
    study_id: str
    verbatim_hunch: str
    normalized_display_hunch: str
    language_observations: list[str] = field(default_factory=list)
    premature_decisions: list[str] = field(default_factory=list)
    status: str = "situational"
    actor: str = ""
    supersedes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", _new_id("rs"))
        if not self.study_id or not self.actor:
            raise ValueError("ResearchSituation requires study_id and actor")
        if not self.verbatim_hunch.strip():
            raise ValueError("verbatim_hunch must not be empty (the hunch IS the record)")
        if self.status not in _SITUATION_STATUSES:
            raise ValueError(
                f"invalid status {self.status!r}; situations are candidate-tier: "
                f"{_SITUATION_STATUSES} only ('assessed' is structurally impossible)"
            )
        if self.status == "superseded" and not self.supersedes:
            raise ValueError("a superseded situation must name its predecessor")


@dataclass(frozen=True)
class Seed:
    seed_id: str
    situation_id: str
    label: str
    attributed_proposal: str
    proposer: str
    rationale: str

    def __post_init__(self) -> None:
        if not all([self.seed_id, self.situation_id, self.label,
                    self.attributed_proposal, self.proposer, self.rationale]):
            raise ValueError(
                "Seed requires every field — attribution (proposer + rationale) "
                "is what makes it candidate-tier rather than anonymous"
            )


def _persist(path: Path, record: dataclass) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def persist_situation(workspace: Path, situation: ResearchSituation) -> Path:
    p = Path(workspace) / SITUATIONS_REL
    _persist(p, situation)
    return p


def read_situations(workspace: Path) -> list[ResearchSituation]:
    p = Path(workspace) / SITUATIONS_REL
    if not p.exists():
        return []
    return [
        ResearchSituation(**json.loads(l))
        for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
    ]


def persist_seed(workspace: Path, seed: Seed) -> Path:
    p = Path(workspace) / SEEDS_REL
    _persist(p, seed)
    return p


def read_seeds(workspace: Path) -> list[Seed]:
    p = Path(workspace) / SEEDS_REL
    if not p.exists():
        return []
    return [
        Seed(**json.loads(l))
        for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
