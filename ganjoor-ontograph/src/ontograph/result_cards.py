"""Ledger row U05: result cards (Gate E "result card" contract).

A result card is the human-facing summary attached to a persisted
analytical result. It carries, per execution spec Gate E:
- a one-sentence reading of the result (numbers in context);
- the denominator (never a bare numerator);
- the source (operation record id + poem provenance);
- the LEGAL next choices (§19.9 decision table -- never an automatic
  argument, never assessed-full while hits are incomplete);
- construction detail (mode, parameters as run).

The card is assembled from the computed result DICT only. It performs no
corpus computation itself (§3: a renderer never computes research
results), and it is derived data -- the OperationRecord on disk stays the
source of truth.
"""
from __future__ import annotations


def _choices(op_type: str, result: dict) -> list[str]:
    """Legal next actions per the §19.9 table (order = priority)."""
    mode = result.get("mode", "")
    choices: list[str] = []
    op_id = result.get("operation_record_id")
    if op_id:
        choices.append(
            f"source show <study> --operation {op_id} (return the result to its passages)"
        )
    if mode == "anchor":
        # hits exist but review state is unknown/lexical: the legal routes
        # are walk, rule, or estimate -- NEVER assessed-full as a suggestion
        choices.append("walk <study> --object <addr> (review hits per-hit)")
        choices.append("declare an assessed-rule or estimated route (V203/V204)")
    else:
        # assessed-full: the governed next steps are Finding/Trace retention
        choices.append(
            "record add <study> --type finding (retain a Finding citing this operation)"
        )
        choices.append("record add <study> --type trace (retain a Trace)")
    choices.append("release <study> --version X.Y.Z (when the study is releaseable)")
    return choices


def build_result_card(operation_type: str, result: dict) -> dict:
    """Assemble the card from the computed result dict (pure)."""
    op_id = result.get("operation_record_id")
    mode = result.get("mode", "anchor")
    object_address = result.get("object_address", "")

    if mode == "anchor":
        hit_count = result.get("hit_count", 0)
        denominator = result.get("poem_count", 0)
        numerator = hit_count
        sentence = (
            f"lexical anchor hits for {object_address!r}: {hit_count} hits "
            f"in {denominator} poems (anchor-level count; not an assessed prevalence)"
        )
    else:
        numerator = result.get("numerator", 0)
        denominator = result.get("denominator", 0)
        ambiguous = result.get("ambiguous_only_count", 0)
        sentence = (
            f"assessed prevalence for {object_address!r}: {numerator}/{denominator} "
            f"poems accepted ({mode}; {ambiguous} ambiguous-only poems remain "
            f"visible in the denominator)"
        )

    return {
        "operation_type": operation_type,
        "sentence": sentence,
        "numerator": numerator,
        "denominator": denominator,
        "source": {
            "operation_record_id": op_id,
            "poems": result.get("accepted_poems")
            or result.get("poems")
            or [],
        },
        "choices": _choices(operation_type, result),
        "construction": {
            "mode": mode,
            "object_address": object_address,
            "ambiguous_only_count": result.get("ambiguous_only_count", 0),
        },
    }
