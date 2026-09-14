"""W08 (Amendment §19.5): the walk evidence tray.

The tray is a SEPARATE display of reviewed candidates and lexical cues
actually located in the current verse/couplet. It is NOT the machine's
"candidate labels": it never recommends a/r/u, never carries assessments,
and every cue keeps its identity (candidate ID) and its source pointer
(poem/verse coordinates + repository-relative path) so the researcher can
resolve it through `source show`.

Purity: build_evidence_tray is a pure function over (hit, catalogs,
reviews, situation_id). It reads nothing from disk and writes nothing.
"""
from __future__ import annotations

from ontograph.anchors import AnchorHit


def _form_in_verse(form: str, hit: AnchorHit) -> bool:
    """Lexical containment check: the candidate's form must actually occur
    in the hit's verse text (normalized whitespace comparison; the verse is
    already normalized upstream by the census matcher)."""
    if not form:
        return False
    verse = " ".join(hit.normalized_text.split())
    needle = " ".join(form.split())
    return needle in verse


def _located_ref(candidates_by_id: dict, candidate) -> dict | None:
    """The candidate's evidence ref for THIS poem, when one exists."""
    for ref in candidate.evidence:
        if ref.poem_id == _current_poem_id:
            return {
                "path": ref.path,
                "poem_id": ref.poem_id,
                "verse_order": ref.verse_order,
                "couplet_index": ref.couplet_index,
                "match_span": list(ref.match_span),
                "corpus_snapshot_id": ref.corpus_snapshot_id,
            }
    # no evidence in this poem: fall back to a pointer built from the hit
    # itself ONLY if the form is actually present in this verse
    return None


# poem id of the hit currently being rendered (set by build_evidence_tray
# before evidence resolution; single-threaded CLI rendering)
_current_poem_id: int | None = None


def build_evidence_tray(
    hit: AnchorHit,
    catalogs: list,
    reviews: list | None = None,
    situation_id: str | None = None,
) -> dict:
    """Assemble the §19.5 evidence tray for one hit. Cues are the
    situation's live candidates whose form is actually located in the hit's
    verse; each carries ID, raw lexical status, human review decision (if
    any), reason shown, and source pointer. No action advice, ever."""
    global _current_poem_id
    _current_poem_id = hit.poem_id
    try:
        reviews = reviews or []
        live_ids = {c.id for c in catalogs if c.supersedes is None}
        superseded_ids = {c.supersedes for c in catalogs if c.supersedes}
        review_by_candidate = {r.candidate_id: r for r in reviews}

        cues: list[dict] = []
        seen_candidates: set[str] = set()
        for catalog in catalogs:
            if catalog.id in superseded_ids or catalog.supersedes is not None:
                continue  # superseded catalogs contribute nothing
            if situation_id and catalog.situation_id != situation_id:
                continue
            for candidate in catalog.candidates:
                if candidate.candidate_id in seen_candidates:
                    continue
                if not _form_in_verse(candidate.form, hit):
                    continue
                seen_candidates.add(candidate.candidate_id)
                review = review_by_candidate.get(candidate.candidate_id)
                evidence = (
                    {
                        "path": ref.path,
                        "poem_id": ref.poem_id,
                        "verse_order": ref.verse_order,
                        "couplet_index": ref.couplet_index,
                        "match_span": list(ref.match_span),
                        "corpus_snapshot_id": ref.corpus_snapshot_id,
                    }
                    for ref in candidate.evidence
                    if ref.poem_id == hit.poem_id
                )
                located = next(evidence, None) or {
                    "path": "",
                    "poem_id": hit.poem_id,
                    "verse_order": hit.verse_order,
                    "couplet_index": hit.couplet_index,
                    "match_span": [hit.token_start, hit.token_end],
                    "corpus_snapshot_id": hit.corpus_snapshot_id,
                }
                cues.append({
                    "candidate_id": candidate.candidate_id,
                    "kind": candidate.kind,
                    "form": candidate.form,
                    "raw_lexical_status": candidate.support_status,
                    "reason_shown": candidate.rationale,
                    "proposed_by": f"{candidate.proposer_type}:{candidate.proposer_id}",
                    "review_decision": review.decision if review else None,
                    "review_actor": review.actor if review else None,
                    "source": located,
                })

        return {"anchor_hit_id": hit.id, "cues": cues}
    finally:
        _current_poem_id = None
