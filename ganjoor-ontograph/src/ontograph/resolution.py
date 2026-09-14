"""Amendment 20 §4.3/§4.9: ResolutionPolicy -- how a Position Set composes
into one figure, always an explicit, versioned, disclosed declaration.
`resolve()` never has a built-in fallback order over assessor types
(Amendment 20 §3.4); the engine refuses to compose when no policy is
declared (§4.3) rather than silently choosing one.
"""
from __future__ import annotations

import json
import uuid as _uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("none", "concordance", "named-assessor", "weighted")
CONTESTED_HANDLINGS = ("excluded-and-reported", "counted-as-undecidable")


@dataclass(frozen=True)
class ResolutionPolicy:
    """Amendment 20 §4.3. `object_address_id` may be a real object address
    or the literal `"*"` for a study default. `contestation_threshold`
    and `min_weight_for_inclusion` were added in Amendment v1.1.0 to close
    the two gaps found in review -- see their docstrings below."""

    id: str
    object_address_id: str
    kind: str
    assessor_object_id: str | None = None  # required when kind == named-assessor
    weights: dict | None = None  # required when kind == weighted: {assessor_object_id: float}
    contested_handling: str = "excluded-and-reported"
    contestation_threshold: float | None = None
    """Share of eligible hits that may be `contested` before Amendment 20
    §4.7's Claim Permission ceiling drops to "describe locally" regardless
    of coverage. None == 0.0 (zero tolerance). This is the field §4.7's
    "study-declared threshold" names."""
    min_weight_for_inclusion: float | None = None
    """A non-human position whose self-reported `weight` falls below this
    value is excluded from THIS policy's resolution and does not count
    toward coverage under this policy. A human position is never excluded
    this way, regardless of its weight. None == no floor."""
    justification: str = ""
    declared_by: str = ""
    declared_at: str = ""
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"invalid ResolutionPolicy.kind: {self.kind!r} (must be one of {KINDS})")
        if self.kind == "named-assessor" and not self.assessor_object_id:
            raise ValueError("kind='named-assessor' requires assessor_object_id")
        if self.kind == "weighted":
            if not self.weights:
                raise ValueError("kind='weighted' requires weights")
            if not self.justification:
                raise ValueError(
                    "kind='weighted' requires justification -- averaging positions "
                    "needs a stated reason (Amendment 20 §4.3; §26 warns against "
                    "averaging disagreement into synthetic truth without one)"
                )
        if self.contested_handling not in CONTESTED_HANDLINGS:
            raise ValueError(f"invalid contested_handling: {self.contested_handling!r}")
        for name, value in (
            ("contestation_threshold", self.contestation_threshold),
            ("min_weight_for_inclusion", self.min_weight_for_inclusion),
        ):
            if value is not None and not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0,1] or None, got {value!r}")


def new_policy_id() -> str:
    return "rp1-" + _uuid.uuid4().hex


def _ledger_path(ws: Path) -> Path:
    return ws / "research" / "resolution-policies.jsonl"


def declare_policy(ws: Path, policy: ResolutionPolicy) -> ResolutionPolicy:
    """Append `policy`. Policies are versioned and append-only, like every
    other Ontograph ledger -- redeclaring for the same object_address_id
    supersedes the prior policy for FUTURE reads (active_policy_for), but
    the prior declaration stays in the ledger as history."""
    if not policy.declared_at:
        from dataclasses import replace

        policy = replace(policy, declared_at=datetime.now(timezone.utc).isoformat())
    path = _ledger_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(policy), ensure_ascii=False) + "\n")
    return policy


def read_policies(ws: Path) -> list[ResolutionPolicy]:
    path = _ledger_path(ws)
    if not path.exists():
        return []
    out: list[ResolutionPolicy] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(ResolutionPolicy(**json.loads(line)))
    return out


def active_policy_for(ws: Path, object_address_id: str) -> ResolutionPolicy | None:
    """The most recently declared policy naming this exact object, else
    the most recent study-default (`"*"`) policy, else None -- None means
    "nothing declared," which callers (census.py, F06) must treat as a
    refusal to compute any aggregate, never as an implicit named-assessor
    fallback (Amendment 20 §3.4/§4.3)."""
    policies = read_policies(ws)
    specific = [p for p in policies if p.object_address_id == object_address_id]
    if specific:
        return specific[-1]
    default = [p for p in policies if p.object_address_id == "*"]
    return default[-1] if default else None


def _eligible_positions(ws, position_set: dict, policy: ResolutionPolicy) -> dict:
    """Apply §4.3's `min_weight_for_inclusion` floor: drop non-human
    positions below the floor. A human position is never excluded this
    way regardless of weight (Amendment v1.1.0 §4.3)."""
    if policy.min_weight_for_inclusion is None:
        return position_set
    from ontograph.assessors import resolve_assessor

    kept = {}
    for assessor_id, position in position_set.items():
        assessor = resolve_assessor(ws, assessor_id)
        if assessor.assessor_type == "human":
            kept[assessor_id] = position
            continue
        if position.weight is not None and position.weight < policy.min_weight_for_inclusion:
            continue
        kept[assessor_id] = position
    return kept


def resolve(ws: Path, position_set: dict, policy: ResolutionPolicy) -> str | None:
    """Compose one hit's Position Set into a single stance under `policy`,
    or None when this policy has nothing to say about this hit (excluded,
    unpositioned under this policy, or a weighted tie). None is a
    legitimate result, never an error -- callers treat it as "this hit is
    not counted," not as a crash.

    No branch here compares assessor_type to grant precedence (Amendment
    20 §3.4) -- only `policy.kind`, which the researcher declared, decides
    how positions compose."""
    position_set = _eligible_positions(ws, position_set, policy)
    if not position_set:
        return None

    if policy.kind == "none":
        return None

    if policy.kind == "named-assessor":
        position = position_set.get(policy.assessor_object_id)
        return position.stance if position else None

    if policy.kind == "concordance":
        stances = {p.stance for p in position_set.values()}
        if len(stances) == 1:
            return next(iter(stances))
        # contested under this policy
        return "undecidable" if policy.contested_handling == "counted-as-undecidable" else None

    if policy.kind == "weighted":
        totals: dict[str, float] = {}
        for assessor_id, position in position_set.items():
            w = policy.weights.get(assessor_id)
            if w is None:
                continue
            totals[position.stance] = totals.get(position.stance, 0.0) + w
        if not totals:
            return None
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return None  # tie: no legitimate winner, never guessed
        return ranked[0][0]

    raise AssertionError(f"unreachable: unknown policy kind {policy.kind!r}")  # __post_init__ guards this


def policy_ablation(
    ws: Path,
    hit_ids: list[str],
    object_address_id: str,
    declared: ResolutionPolicy,
    alternatives: list[ResolutionPolicy],
    positions: list | None = None,
) -> dict:
    """Amendment 20 §2.3: every aggregate result also reports the same
    figure under >=1 alternative declared policy. Reports a simple
    occurs-count per policy over `hit_ids`; callers with a richer figure
    (e.g. a percentage, a stratified breakdown) recompute analogously --
    this function establishes the CONTRACT (>=2 policies always present),
    not the only possible shape of the figure itself."""
    from ontograph.positions import active_positions, read_positions

    positions = read_positions(ws) if positions is None else positions

    def occurs_count(policy: ResolutionPolicy) -> int:
        count = 0
        for hit_id in hit_ids:
            active = active_positions(positions, hit_id, object_address_id)
            if resolve(ws, active, policy) == "occurs":
                count += 1
        return count

    result = {"declared": {"policy_id": declared.id, "kind": declared.kind, "occurs": occurs_count(declared)}}
    result["alternatives"] = [
        {"policy_id": p.id, "kind": p.kind, "occurs": occurs_count(p)}
        for p in alternatives
    ]
    return result


def contested_share(ws: Path, hit_ids: list[str], object_address_id: str, positions: list | None = None) -> float:
    """Share of `hit_ids` whose Standing is `contested`, computed from the
    raw Position Set -- policy-independent, matching Standing's own
    "never persisted, always recomputed" rule (Amendment 20 §3.5). This is
    what Amendment 20 §4.7's Claim Permission ceiling compares against a
    policy's `contestation_threshold`."""
    from ontograph.positions import standing_distribution

    if not hit_ids:
        return 0.0
    dist = standing_distribution(ws, hit_ids, object_address_id, positions=positions)
    return dist["contested"] / len(hit_ids)
