"""Ledger row W06 (Amendment §19.2/§19.4): review CLI + direct-route guard.

Discriminating targets:

1. `inquire <study> --review decisions.json --json` reports
   promoted/rejected/deferred IDs and emits the next walk command per
   promoted object.
2. The direct-route guard: in a GOVERNED workspace (one with inquiry
   history), bare `object add` without `--review-id` or
   `--confirmation-file` is REFUSED — an agent cannot bypass human
   review by calling the legacy route.
3. Legacy compatibility: a workspace with NO inquiry history (pre-W01)
   keeps the old behavior explicitly (Amendment §19.2 "explicit legacy").
4. The refusal happens BEFORE any write.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.cli import main as cli_main
from ontograph.inquiry import (
    CandidateEvidenceRef, InquiryCandidate, InquiryCatalog, persist_catalog,
)
from ontograph.workspace import new_study


def _governed_study(tmp_path: Path) -> tuple[Path, str]:
    fixture = Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"
    study = new_study(tmp_path / "ws", "w06-study", corpus_root=str(fixture))
    cand = InquiryCandidate(
        candidate_id="cand-ayene", kind="lexical-anchor", form="آینه",
        proposer_type="human", proposer_id="mz", rationale="mirror motif",
        support_status="supported", hit_count=6, poem_count=6, poet_count=2,
        evidence=[CandidateEvidenceRef(
            path="poets/sample1/ghazal/p9101.json", poem_id=9101,
            verse_order=1, couplet_index=0, match_span=[0, 4],
            corpus_snapshot_id="cs1-x",
        )],
    )
    cat = InquiryCatalog(
        study_id="w06-study", situation_id="rs-x", corpus_snapshot_id="cs1-x",
        field_id="field-1", scope_spec={"kind": "all"}, parameters={},
        limitations=[], candidates=[cand],
    )
    persist_catalog(study, cat)
    return study, cat.id


def _run(study: Path, *args):
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(["inquire", str(study), *args, "--json"])
    return rc, out.getvalue(), err.getvalue()


def test_review_cli_reports_and_emits_walk_commands(tmp_path: Path) -> None:
    study, catalog_id = _governed_study(tmp_path)
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps([
        {"candidate_id": "cand-ayene", "decision": "accept", "rationale": "verified"}
    ]), encoding="utf-8")
    rc, out, err = _run(study, "--review", str(decisions), "--situation", "rs-x",
                        "--review-actor", "mz", "--receipt", "rc-1")
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["promoted"] == ["cand-ayene"]
    assert payload["next_walk_command"], "each promoted object gets its next walk command"
    # the object is actually promoted
    from ontograph.inquiry_review import load_object_address_ids

    assert "cand-ayene" in load_object_address_ids(study)


def test_direct_object_add_refused_in_governed_workspace(tmp_path: Path) -> None:
    study, catalog_id = _governed_study(tmp_path)
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main([
            "object", "add", str(study), "--address", "sneaky",
            "--label", "bypass", "--anchor", "زنگار", "--json",
        ])
    assert rc != 0 and out.getvalue() == "", "governed workspaces refuse unreviewed direct object add"
    assert "review" in err.getvalue().lower() or "governed" in err.getvalue().lower()


def test_direct_add_allowed_with_confirmation_file(tmp_path: Path) -> None:
    study, catalog_id = _governed_study(tmp_path)
    conf = tmp_path / "confirmation.json"
    conf.write_text(json.dumps({
        "human_actor": "mz", "receipt": "rc-manual",
        "object_id": "manual-obj", "rationale": "researcher's own direct entry",
    }), encoding="utf-8")
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main([
            "object", "add", str(study), "--address", "manual-obj",
            "--label", "manual", "--anchor", "زنگار",
            "--confirmation-file", str(conf), "--json",
        ])
    assert rc == 0, err


def test_legacy_workspace_keeps_direct_add(tmp_path: Path) -> None:
    """Explicit legacy compatibility (Amendment §19.2): a workspace with
    NO inquiry history is not governed; direct add behaves as before."""
    from ontograph.workspace import new_study

    study = new_study(tmp_path / "ws", "legacy-study")
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main([
            "object", "add", str(study), "--address", "old-style",
            "--label", "old", "--anchor", "شب", "--json",
        ])
    assert rc == 0, err
