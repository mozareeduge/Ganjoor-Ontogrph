"""Amendment 20 §4.7: Claim Permission as a machine-enforced ceiling keyed
to DISCLOSED COMPOSITION AND CONTESTATION, never to assessor type or
authorship. A lone human and a lone rule get exactly the same ceiling;
what buys argumentative permission is independent corroboration plus low
contestation, not who spoke. Computed from an OperationRecord's stored
`result` (built by census's flat-assessment branch, F07/F08/F09) and
enforced at `cli._record_add()` (F10).
"""
from __future__ import annotations

PERMISSION_LEVELS = (
    "preserve only",
    "describe locally",
    "describe distribution under declared conditions",
    "argue cautiously",
    "argue",
)


class ClaimPermissionError(ValueError):
    """A Finding/Claim declares a permission level its cited operation's
    result does not support. Named distinctly from the builtin
    `PermissionError` (the Amendment's own prose names it `PermissionError`,
    which would shadow the builtin -- a small, deliberate naming deviation,
    not a behavior change)."""

    def __init__(self, declared: str, ceiling: str, reason: str) -> None:
        self.declared = declared
        self.ceiling = ceiling
        super().__init__(
            f"declared claim_permission {declared!r} exceeds the ceiling "
            f"{ceiling!r} for this operation (Amendment 20 §4.7): {reason}"
        )


def _level_index(level: str) -> int:
    try:
        return PERMISSION_LEVELS.index(level)
    except ValueError:
        raise ValueError(f"unknown claim_permission level: {level!r} (must be one of {PERMISSION_LEVELS}, or 'blocked')")


def exceeds_ceiling(declared: str, ceiling: str) -> bool:
    """True when `declared` reaches further than `ceiling` permits.
    `declared == "blocked"` never exceeds anything -- refusing to claim at
    all is always within any ceiling."""
    if declared == "blocked":
        return False
    return _level_index(declared) > _level_index(ceiling)


def _one_level_below(ceiling: str) -> str:
    idx = _level_index(ceiling)
    return PERMISSION_LEVELS[max(0, idx - 1)]


def ceiling_for(ws, operation_record: dict) -> str:
    """Amendment 20 §4.7's full table. `operation_record` is a stored
    OperationRecord dict (as `operations.read_operation_records()` returns
    it) -- its `result` key carries whatever `_census`'s flat-assessment
    branch (F07/F08/F09) computed, including `positioning`/`standing`/
    `resolution_policy`.

    SCOPING NOTE: `estimated` mode is not yet wired to any CLI verb
    (tracked separately, Plans.md's deferred-work list) -- its branch
    below is a placeholder for when it is, not independently verified
    here."""
    result = operation_record.get("result", {}) or {}
    mode = result.get("mode") or (operation_record.get("parameters") or {}).get("mode", "anchor")

    if mode == "anchor":
        return "preserve only"
    if mode == "inventory":
        return "describe locally"
    if mode == "estimated":
        return "describe distribution under declared conditions"
    if mode not in ("positioned-full", "positioned-concordant"):
        raise ValueError(f"ceiling_for: unrecognized/unsupported mode {mode!r}")

    positioning = result.get("positioning") or {}
    standing = result.get("standing") or {}
    policy = result.get("resolution_policy")

    if positioning.get("unpositioned_hits", 1) != 0:
        return "describe locally"  # positioning coverage < 100%

    eligible = positioning.get("eligible_hits", 0) or 0
    contested = standing.get("contested", 0) or 0
    contested_share = (contested / eligible) if eligible else 0.0
    # Amendment v1.1.0 §4.3: an undeclared contestation_threshold is None,
    # read as 0.0 (zero tolerance). The persisted result does not carry
    # the full policy object today (only id/kind), so any contestation at
    # all is treated as exceeding an unknown/default threshold here --
    # conservative, matching the "None == 0.0" convention exactly rather
    # than assuming a threshold that was never disclosed in the result.
    if contested_share > 0.0:
        return "describe locally"

    by_assessor = positioning.get("by_assessor") or {}
    assessor_ids = list(by_assessor)

    if policy is not None and policy.get("kind") == "weighted":
        base = _base_ceiling(ws, mode, assessor_ids)
        return _one_level_below(base)

    return _base_ceiling(ws, mode, assessor_ids)


def _base_ceiling(ws, mode: str, assessor_ids: list[str]) -> str:
    if mode == "positioned-concordant":
        # reachable only when every eligible hit is already `concordant`
        # (enforced by census.enforce_mode_requirements before this
        # result could ever exist) -- independent corroboration across
        # the whole eligible set, the table's top tier.
        return "argue"

    # positioned-full
    if len(assessor_ids) <= 1:
        return "describe distribution under declared conditions"

    from ontograph.assessors import independence_classes_of

    classes = independence_classes_of(ws, assessor_ids)
    if len(classes) >= 2:
        return "argue cautiously"
    # >=2 assessor ids but sharing one independence class: real
    # corroboration was never actually achieved (Amendment 20 §3.2's
    # anti-gaming guard) -- no better than a single voice.
    return "describe distribution under declared conditions"
