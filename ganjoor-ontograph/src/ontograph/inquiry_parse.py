"""Ledger row W02 (Amendment §19.3): lossless hunch + attributed
proposal parsing — pure functions.

Rules implemented:
- `parse_hunch`: verbatim text is preserved byte-for-byte; display
  normalization is whitespace-collapsing ONLY; language observation is
  script-based (Arabic-script presence -> persian/mixed, else english);
  an English hunch without supplied Persian forms yields
  needs-vocabulary — the runtime never translates or fabricates forms.
- `parse_proposal`: validates one attributed candidate proposal dict
  into an InquiryCandidate with support_status='unsupported' (a
  proposal is unverified by definition — W04's verifier upgrades it).
  Engine-generated semantic contrasts are refused: proposals come from
  the researcher or are attributed to an agent actor, never to "the
  engine decided" (Amendment §19.3).
"""
from __future__ import annotations

import re

from ontograph.inquiry import InquiryCandidate

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def parse_hunch(raw: str, persian_forms: list[str] | None = None) -> dict:
    verbatim = raw
    if not verbatim.strip():
        raise ValueError("hunch must not be empty")
    display = " ".join(verbatim.split())
    has_arabic = bool(_ARABIC_RE.search(verbatim))
    language = "persian" if has_arabic else "english"
    forms = list(persian_forms or [])
    return {
        "verbatim_hunch": verbatim,
        "normalized_display_hunch": display,
        "language_observations": [language],
        "needs_vocabulary": language == "english" and not forms,
        "persian_forms": forms,
    }


def parse_proposal(prop: dict) -> InquiryCandidate:
    kind = prop.get("kind")
    proposer = str(prop.get("proposer") or "")
    proposer_type = str(prop.get("proposer_type") or ("human" if proposer else ""))
    rationale = str(prop.get("rationale") or "")
    if not proposer:
        raise ValueError("proposal requires an attributed proposer (never anonymous)")
    if not rationale:
        raise ValueError("proposal requires a rationale (attribution without reason is not governance)")
    if proposer_type == "engine":
        raise ValueError(
            "the engine never generates semantic contrasts or strategy labels; "
            "proposals must be human- or agent-attributed (Amendment §19.3)"
        )
    form = str(prop.get("form") or "")
    cand = InquiryCandidate(
        candidate_id=str(prop.get("candidate_id") or f"cand-{abs(hash((kind, form, proposer))) % 10**12:012d}"),
        kind=kind or "",
        form=form,
        proposer_type=proposer_type,
        proposer_id=proposer,
        rationale=rationale,
        support_status="unsupported",
    )
    return cand
