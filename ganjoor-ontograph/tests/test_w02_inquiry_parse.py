"""Ledger row W02 (Amendment §19.3): lossless hunch + attributed
proposal parser — PURE functions, no index access, no CLI writes.

Discriminating targets:

1. An English-only hunch preserves the verbatim text byte-for-byte and
   yields language_observations=['english'] and the `needs-vocabulary`
   signal when no Persian forms are supplied — never fabricated forms.
2. An attributed Persian proposal (YAML/JSON dict) parses into an
   InquiryCandidate with proposer + rationale carried losslessly.
3. Missing proposer/rationale, unknown kinds, and purported
   engine-generated contrast candidates are REFUSED (the engine never
   generates semantic contrasts — Amendment §19.3).
4. Normalization is display-only: whitespace collapsing for display,
   verbatim preserved.
"""
from __future__ import annotations

import pytest

from ontograph.inquiry import InquiryCandidate
from ontograph.inquiry_parse import (
    parse_hunch,
    parse_proposal,
)


def test_english_hunch_preserved_verbatim_needs_vocabulary() -> None:
    raw = "I keep noticing Rostam winning by cunning,  not force."
    out = parse_hunch(raw)
    assert out["verbatim_hunch"] == raw
    assert out["normalized_display_hunch"] == "I keep noticing Rostam winning by cunning, not force."
    assert out["language_observations"] == ["english"]
    assert out["needs_vocabulary"] is True
    assert out["persian_forms"] == [], "never fabricate Persian forms"


def test_hunch_with_supplied_persian_forms() -> None:
    out = parse_hunch("نبرد رستم", persian_forms=["کمند", "چاره باید نه زور"])
    assert out["needs_vocabulary"] is False
    assert out["persian_forms"] == ["کمند", "چاره باید نه زور"]
    assert out["verbatim_hunch"] == "نبرد رستم"


def test_attributed_proposal_parses() -> None:
    prop = {
        "kind": "lexical-anchor", "form": "کمند",
        "proposer": "mz", "proposer_type": "human",
        "rationale": "signature rope trick",
    }
    cand = parse_proposal(prop)
    assert isinstance(cand, InquiryCandidate)
    assert cand.form == "کمند"
    assert cand.proposer_id == "mz"
    assert cand.support_status == "unsupported"  # proposal, not yet verified


def test_unattributed_proposal_refused() -> None:
    with pytest.raises(ValueError, match="proposer"):
        parse_proposal({"kind": "lexical-anchor", "form": "کمند", "rationale": "r"})
    with pytest.raises(ValueError, match="rationale"):
        parse_proposal({"kind": "lexical-anchor", "form": "کمند", "proposer": "mz"})


def test_unknown_kind_refused() -> None:
    with pytest.raises(ValueError, match="kind"):
        parse_proposal({"kind": "strategy-label", "form": "x",
                        "proposer": "mz", "rationale": "r"})


def test_engine_generated_contrast_refused() -> None:
    with pytest.raises(ValueError, match="engine"):
        parse_proposal({
            "kind": "authored-contrast", "form": "زور",
            "proposer": "engine", "proposer_type": "engine",
            "rationale": "the engine detected this contrast",
        })


def test_empty_hunch_refused() -> None:
    with pytest.raises(ValueError):
        parse_hunch("   ")
