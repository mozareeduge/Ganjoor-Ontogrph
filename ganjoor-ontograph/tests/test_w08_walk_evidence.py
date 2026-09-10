"""Ledger row W08: walk evidence tray and candidate encounter.

Discriminating targets (openspec tasks.md W08, Amendment §19.5):

1. The evidence tray shows ONLY candidates whose form is actually
   located in the current verse/couplet — absent forms are never shown.
2. Every tray cue carries a source pointer (poem + verse coordinates)
   resolvable through `source show` — never a bare label.
3. The tray NEVER recommends a/r/u — no action advice anywhere in it.
4. `c:<candidate-id>` writes ONLY a proposal event pinned to the stable
   hit — no assessment row, no promotion, hit stays undecided.
5. Unknown/stale candidate IDs (superseded catalog) fail ATOMICALLY —
   nothing is written.
6. Four-way completion summary: accepted/rejected/ambiguous/unassessed.
7. `done`/empty responses remain a stop — never aggregation or a
   completeness override.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.anchors import AnchorHit
from ontograph.cli import main
from ontograph.inquiry import (
    CandidateEvidenceRef,
    InquiryCandidate,
    InquiryCatalog,
    InquiryReview,
    persist_catalog,
    persist_review,
)
from ontograph.walk_evidence import build_evidence_tray
from ontograph.walk_state import WalkAction, WalkResponse, WalkState, apply_action, run_walk

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _hit(verse: str = "آینه در دست من است امشب", poem_id: int = 9101) -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=0, position="Right", original_text=verse,
        normalized_text=verse, token_start=0, token_end=1,
        verse_order=1, corpus_snapshot_id="cs1-test",
    )


def _candidate(cid: str, form: str, support: str, kind: str = "lexical-anchor") -> InquiryCandidate:
    evidence = []
    if support == "supported":
        evidence = [CandidateEvidenceRef(
            path="poets/sample1/sh9101.json", poem_id=9101, verse_order=1,
            couplet_index=0, match_span=[0, 5], corpus_snapshot_id="cs1-test",
        )]
    return InquiryCandidate(
        candidate_id=cid, kind=kind, form=form,
        proposer_type="agent", proposer_id="hermes", rationale="proposal for study",
        support_status=support, hit_count=3 if support == "supported" else 0,
        evidence=evidence,
    )


def _catalog(candidates: list, supersedes: str | None = None) -> InquiryCatalog:
    return InquiryCatalog(
        study_id="w08-study", situation_id="rs1-a", corpus_snapshot_id="cs1-test",
        field_id="field-1", scope_spec={}, parameters={}, limitations=[],
        candidates=candidates, supersedes=supersedes,
    )


def _state(catalogs: list, hits: list | None = None) -> WalkState:
    return WalkState(
        object_address="mirror", sample=hits or [_hit()],
        corpus_snapshot_id="cs1-test", catalogs=catalogs,
    )


# --- 1+2+3. the evidence tray --------------------------------------------------


def test_tray_shows_only_cues_located_in_verse() -> None:
    present = _candidate("cand1-present", "آینه", "supported")
    absent = _candidate("cand2-absent", "زنگار", "unsupported")
    tray = build_evidence_tray(_hit(), [_catalog([present, absent])], situation_id="rs1-a")
    shown = {c["candidate_id"] for c in tray["cues"]}
    assert shown == {"cand1-present"}, "a candidate absent from the verse is never displayed"


def test_tray_cues_carry_source_pointer() -> None:
    present = _candidate("cand1", "آینه", "supported")
    tray = build_evidence_tray(_hit(), [_catalog([present])], situation_id="rs1-a")
    cue = tray["cues"][0]
    assert cue["source"]["poem_id"] == 9101
    assert cue["source"]["verse_order"] == 1
    assert cue["source"]["path"] == "poets/sample1/sh9101.json"
    assert cue["raw_lexical_status"] == "supported"


def test_tray_shows_human_review_decision_without_recommending() -> None:
    cand = _candidate("cand1", "آینه", "supported")
    catalog = _catalog([cand])
    review = InquiryReview(
        catalog_id=catalog.id, situation_id="rs1-a", candidate_id="cand1",
        decision="accept", actor="mz", rationale="human call", receipt="r-1",
    )
    tray = build_evidence_tray(_hit(), [catalog], reviews=[review], situation_id="rs1-a")
    cue = tray["cues"][0]
    assert cue["review_decision"] == "accept"
    assert cue["review_actor"] == "mz"
    # §19.5: the tray never recommends a/r/u
    blob = json.dumps(tray, ensure_ascii=False)
    assert "recommend" not in blob and "decide" not in blob


def test_tray_isolates_situation() -> None:
    cand_other = _candidate("cand-other", "آینه", "supported")
    cat_other = _catalog([cand_other])
    object.__setattr__(cat_other, "situation_id", "rs1-OTHER")
    tray = build_evidence_tray(_hit(), [cat_other], situation_id="rs1-a")
    assert tray["cues"] == [], "candidates from other situations are not in this tray"


# --- 4. c: candidate encounter in the state machine -----------------------------


def test_candidate_encounter_writes_proposal_event_only() -> None:
    cand = _candidate("cand1", "آینه", "supported")
    state = _state([_catalog([cand])])
    result = apply_action(state, WalkAction(token="c", hit_id=state.sample[0].id, candidate_id="cand1"))
    assert result.candidate_encounters[0]["candidate_id"] == "cand1"
    assert result.candidate_encounters[0]["hit_id"] == state.sample[0].id
    assert result.ledger_rows == [], "an encounter is never an assessment"
    assert result.undecided == [state.sample[0].id], "the hit stays undecided"
    assert result.trace is None and result.new_objects == [], "no promotion side effects"


def test_candidate_encounter_unknown_candidate_fails() -> None:
    state = _state([_catalog([_candidate("cand1", "آینه", "supported")])])
    with pytest.raises(ValueError):
        apply_action(state, WalkAction(token="c", hit_id=state.sample[0].id, candidate_id="cand-ghost"))


def test_candidate_encounter_stale_catalog_refused() -> None:
    old = _catalog([_candidate("cand-old", "آینه", "supported")])
    new = _catalog([_candidate("cand-new", "آینه", "supported")], supersedes=old.id)
    state = _state([old, new])
    with pytest.raises(ValueError):
        apply_action(state, WalkAction(token="c", hit_id=state.sample[0].id, candidate_id="cand-old"))


def test_candidate_encounter_unknown_hit_fails_atomically() -> None:
    state = _state([_catalog([_candidate("cand1", "آینه", "supported")])])
    with pytest.raises(ValueError):
        apply_action(state, WalkAction(token="c", hit_id="ah1-ghost", candidate_id="cand1"))


# --- 6+7. four-way summary; done stays a stop ------------------------------------


def _seven_hits() -> list[AnchorHit]:
    return [_hit(poem_id=9100 + i) for i in range(1, 8)]


def test_four_way_completion_summary() -> None:
    hits = _seven_hits()
    state = WalkState(object_address="mirror", sample=hits, corpus_snapshot_id="cs1-test")
    responses = (
        [WalkResponse(anchor_hit_id=h.id, action="accepted") for h in hits[:5]]
        + [WalkResponse(anchor_hit_id=hits[5].id, action="rejected")]
        + [WalkResponse(anchor_hit_id=hits[6].id, action="ambiguous")]
    )
    result = run_walk(state, responses)
    assert (result.accepted, result.rejected, result.ambiguous) == (5, 1, 1)
    assert result.unassessed == 0


def test_done_is_a_stop_never_aggregation() -> None:
    hits = _seven_hits()
    state = WalkState(object_address="mirror", sample=hits, corpus_snapshot_id="cs1-test")
    result = run_walk(state, [])  # stopped immediately: nothing decided
    assert result.unassessed == 7, "unassessed stays visible; completeness is never manufactured"
    assert result.ledger_rows == []


# --- CLI wiring: `ontograph walk` accepts c: and stays atomic ---------------------


def _conf_file(tmp_path: Path, object_id: str) -> str:
    p = tmp_path / "confirmation.json"
    p.write_text(json.dumps({
        "human_actor": "mz", "receipt": "receipt-1", "object_id": object_id,
    }), encoding="utf-8")
    return str(p)


def _seed_walk_workspace(capsys, tmp_path: Path, study_id: str):
    ws_dir = str(tmp_path / "ontograph-workspaces")
    ws = Path(ws_dir) / study_id

    def run(argv):
        code = main(argv)
        captured = capsys.readouterr()
        assert code == 0, captured.err or captured.out
        return captured.out

    run(["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])
    run(["object", "add", study_id, "--address", "mirror", "--label", "Mirror",
         "--anchor", "آینه", "--workspaces-dir", ws_dir])
    # W07B: walk is a governed command -- a situation is required. The
    # situation store is the preflight's input, written directly here.
    from ontograph.records_v2 import ResearchSituation, persist_situation

    persist_situation(ws, ResearchSituation(
        study_id=study_id, verbatim_hunch="w08 fixture hunch",
        normalized_display_hunch="w08 fixture hunch", actor="mz",
    ))
    return ws, ws_dir


def test_cli_walk_candidate_encounter_appends_event(capsys, tmp_path) -> None:
    ws, ws_dir = _seed_walk_workspace(capsys, tmp_path, "w08-cli")
    cand = _candidate("cand1", "آینه", "supported")
    persist_catalog(ws, _catalog([cand]))
    script = tmp_path / "script.json"
    # mirror has 7 fixture hits: first pins an encounter, then 5/1/1 replay
    script.write_text(json.dumps({"responses": ["c:cand1", "a", "a", "a", "a", "a", "r"]}),
                      encoding="utf-8")
    code = main(["walk", "w08-cli", "--object", "mirror", "--script", str(script),
                 "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    events_path = ws / "events" / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    enc = [e for e in events if e["event_type"] == "walk-candidate_encounter"]
    assert len(enc) == 1 and enc[0]["target_ids"] == ["cand1"]


def test_cli_walk_unknown_candidate_atomic_refusal(capsys, tmp_path) -> None:
    ws, ws_dir = _seed_walk_workspace(capsys, tmp_path, "w08-atomic")
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"responses": ["c:ghost", "a"]}), encoding="utf-8")
    code = main(["walk", "w08-atomic", "--object", "mirror", "--script", str(script),
                 "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    captured = capsys.readouterr()
    assert code != 0
    assert "ghost" in captured.err
    # atomic: nothing was appended anywhere (events.jsonl exists empty from
    # `study new` scaffolding; the refusal must have added no event)
    assert (ws / "events" / "events.jsonl").read_text(encoding="utf-8").strip() == ""
    assert not (ws / "corpus" / "hit-assessments.jsonl").exists()
