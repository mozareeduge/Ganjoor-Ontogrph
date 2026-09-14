"""Amendment 20 §3.2: AssessorObject -- assessor identities as first-class,
registered records, not an enum value stamped on an assessment row.

This is the structural form of the researcher's own framing: "humans are
also objects horizontally working in this complex object." A human, an
LLM triage pass, a deterministic rule, a retrieval score, a prior study --
each gets an AssessorObject with its own id, apparatus, and declared
independence_class. Nothing in this module ranks them; `assessor_type` is
descriptive only (§3.2), and no function here may be used to grant one
type precedence over another (Amendment 20 §3.4).
"""
from __future__ import annotations

import json
import uuid as _uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Descriptive only -- open vocabulary, never a ranked enum (Amendment 20 §3.2).
# This tuple exists for documentation/CLI --help text, not for validation:
# a study may declare any assessor_type string it needs.
KNOWN_ASSESSOR_TYPES = (
    "human", "agent", "rule", "retrieval-score", "corpus-metadata",
    "prior-study", "editorial-apparatus",
)


@dataclass(frozen=True)
class AssessorObject:
    """A registered assessor identity (Amendment 20 §3.2).

    `independence_class` is the guard against the obvious cheat ("add a
    second assessor to buy a higher permission tier"): two assessors
    sharing a class do not corroborate each other in `resolution.py`'s
    Standing computation. It is declared, not verified -- consistent with
    the project's existing attestation-based trust model (spec: a human
    receipt is a string, not a cryptographic proof)."""

    id: str
    label: str
    assessor_type: str  # descriptive; see KNOWN_ASSESSOR_TYPES, not enforced
    apparatus: str  # REQUIRED: what produced this assessor's positions
    independence_class: str
    conditions_of_validity: str = ""
    registered_by: str = ""
    registered_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("AssessorObject.id is required")
        if not self.assessor_type:
            raise ValueError("AssessorObject.assessor_type is required")
        if not self.apparatus:
            raise ValueError(
                f"AssessorObject {self.id!r}: apparatus is required -- "
                "human: who + what context ladder levels are opened; "
                "agent: model id + prompt version + harness; "
                "rule: rule id + version + implementation reference "
                "(Amendment 20 §3.2)"
            )
        if not self.independence_class:
            raise ValueError(
                f"AssessorObject {self.id!r}: independence_class is required "
                "-- declare it even when it is unique to this assessor "
                "(Amendment 20 §3.2)"
            )


def new_assessor_id(label_hint: str = "") -> str:
    """`as-` + uuid4 hex, optionally prefixed by a slugified hint for
    readability (e.g. `as-mz-a1b2c3...`). The hint is cosmetic only --
    identity is the full id, never the hint alone."""
    slug = "".join(c.lower() if c.isalnum() else "-" for c in label_hint).strip("-")
    slug = "-".join(p for p in slug.split("-") if p)[:24]
    suffix = _uuid.uuid4().hex[:16]
    return f"as-{slug}-{suffix}" if slug else f"as-{suffix}"


def _registry_path(ws: Path) -> Path:
    return ws / "objects" / "assessor-objects.jsonl"


def register_assessor(ws: Path, assessor: AssessorObject) -> AssessorObject:
    """Append `assessor` to the registry. Registration is append-only like
    every other Ontograph ledger; re-registering the same id is refused
    (use a new id for a materially different apparatus -- e.g. a new
    model/prompt version is a NEW assessor, not an edit of the old one,
    so its positions stay attributable to the exact apparatus that made
    them)."""
    existing = {a.id for a in read_assessors(ws)}
    if assessor.id in existing:
        raise ValueError(
            f"assessor {assessor.id!r} is already registered -- a materially "
            "different apparatus (model/prompt/rule version) needs a new id, "
            "not a re-registration of this one"
        )
    if not assessor.registered_at:
        assessor = _with_timestamp(assessor)
    path = _registry_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(assessor), ensure_ascii=False) + "\n")
    return assessor


def _with_timestamp(assessor: AssessorObject) -> AssessorObject:
    from dataclasses import replace

    return replace(assessor, registered_at=datetime.now(timezone.utc).isoformat())


def read_assessors(ws: Path) -> list[AssessorObject]:
    path = _registry_path(ws)
    if not path.exists():
        return []
    out: list[AssessorObject] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(AssessorObject(**json.loads(line)))
    return out


def resolve_assessor(ws: Path, assessor_id: str) -> AssessorObject:
    """Look up a registered assessor by id. Raises with a clear message
    (never returns None / silently guesses) when the id is unknown --
    an unregistered assessor cannot position anything (Amendment 20 §3.2
    is what makes positions attributable to a real, inspectable apparatus
    at all)."""
    for a in read_assessors(ws):
        if a.id == assessor_id:
            return a
    raise ValueError(
        f"assessor {assessor_id!r} is not registered in this study -- "
        "run 'ontograph assessor add' first, or check for a typo"
    )


def independence_classes_of(ws: Path, assessor_ids: list[str]) -> set[str]:
    """The set of distinct `independence_class` values among `assessor_ids`.
    Used by `resolution.standing_of()` to distinguish `concordant` (>=2
    classes agreeing) from `corroborated-weak` (agreeing, but sharing a
    class -- e.g. a rule authored by the same agent whose output it rules
    over shares that agent's class, per Amendment 20 §3.2)."""
    registry = {a.id: a for a in read_assessors(ws)}
    classes: set[str] = set()
    for aid in assessor_ids:
        assessor = registry.get(aid)
        if assessor is None:
            raise ValueError(f"assessor {aid!r} is not registered in this study")
        classes.add(assessor.independence_class)
    return classes
