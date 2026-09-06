"""Ledger row U05: result cards + Findings linked to operations/sources.

Discriminating targets (execution spec U05 + Gate E):

1. Governed census results carry a RESULT CARD: sentence, denominator,
   source (operation + poem provenance), legal choices, and construction
   detail. The card is assembled from the computed result only — the
   renderer never computes (§3 invariant).
2. Card choices follow the §19.9 table: an operation without a Finding
   offers source-return/finding routes; it never offers an automatic
   argument. Hits without full review offer walk/rule/estimate — never
   assessed-full.
3. Gate E fixture: the full governed chain runs end-to-end on the
   fixture — study → inquire → field → object(review receipt) → walk →
   assessed-full census → source show → Finding → release — and every
   stage's contract is asserted (status suggests only legal actions).
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.cli import main
from ontograph.result_cards import build_result_card

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _ws_dir(tmp_path: Path, study_id: str) -> str:
    return str(tmp_path / "ontograph-workspaces")


# --- 1. the result card -------------------------------------------------------


def test_card_carries_sentence_denominator_source_choices() -> None:
    card = build_result_card(
        "census",
        {"object_address": "mirror", "mode": "assessed-full",
         "numerator": 5, "denominator": 27, "ambiguous_only_count": 1,
         "operation_record_id": "op-123",
         "accepted_poems": [9101], "ambiguous_only_poems": [9105]},
    )
    assert card["denominator"] == 27
    assert "5/27" in card["sentence"] and "mirror" in card["sentence"]
    assert card["source"]["operation_record_id"] == "op-123"
    assert 9101 in card["source"]["poems"]
    assert card["choices"], "legal next actions are always listed"
    assert card["construction"]["mode"] == "assessed-full"


def test_card_anchor_mode_denominator_is_lexical() -> None:
    card = build_result_card(
        "census",
        {"object_address": "mirror", "mode": "anchor", "hit_count": 7,
         "poem_count": 5, "operation_record_id": "op-1", "poems": [9101]},
    )
    assert card["denominator"] == 5
    assert "7" in card["sentence"]


def test_card_never_offers_automatic_argument() -> None:
    card = build_result_card(
        "census",
        {"object_address": "m", "mode": "assessed-full", "numerator": 1,
         "denominator": 1, "ambiguous_only_count": 0,
         "operation_record_id": "op-1", "accepted_poems": [1],
         "ambiguous_only_poems": []},
    )
    blob = json.dumps(card)
    assert "argument" not in blob, "the card never suggests an automatic argument"
    assert any("source" in c or "finding" in c for c in card["choices"])


def test_card_partial_review_offers_walk_not_assessed_full() -> None:
    card = build_result_card(
        "census",
        {"object_address": "m", "mode": "anchor", "hit_count": 9,
         "poem_count": 4, "operation_record_id": "op-2", "poems": [1]},
    )
    assert any("walk" in c for c in card["choices"])
    assert not any("assessed-full" in c for c in card["choices"]), \
        "hits/incomplete state must not suggest assessed-full (§19.9)"


# --- 2. Gate E fixture: the full governed chain ---------------------------------


def test_gate_e_full_chain(tmp_path, capsys) -> None:
    ws_dir = _ws_dir(tmp_path, "gate-e")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]

    # study
    code, out, err = _run(capsys, ["study", "new", "gate-e", "--corpus-root",
                                   FIXTURE_ROOT, "--workspaces-dir", ws_dir])
    assert code == 0, err

    # status first: no situation -> only legal action is inquire
    code, out, err = _run(capsys, ["study", "status", "gate-e",
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0
    status = json.loads(out)
    assert status["state"] == "no-situation" and "inquire" in status["suggestion"]

    # inquire (situation + attributed candidate) — intake verb: no
    # --corpus-root (create performs no corpus computation)
    proposals = tmp_path / "proposals.json"
    proposals.write_text(json.dumps([{
        "kind": "lexical-anchor", "label": "mirror", "form": "آینه",
        "proposer": "hermes", "proposer_type": "agent",
        "rationale": "surface motif probe",
    }]), encoding="utf-8")
    code, out, err = _run(capsys, ["inquire", "gate-e", "--hunch",
                                   "mirrors as self-division", "--actor", "mz",
                                   "--file",
                                   str(proposals), "--workspaces-dir", ws_dir,
                                   "--json"])
    assert code == 0, err or out

    # field build (governed: inherits the single situation)
    code, out, err = _run(capsys, ["field", "build", "gate-e", *base, "--json"])
    assert code == 0, err or out

    # object promotion needs the human receipt in a governed workspace
    conf = tmp_path / "confirmation.json"
    conf.write_text(json.dumps({
        "human_actor": "mz", "receipt": "receipt-e", "object_id": "mirror",
        "rationale": "human review of the mirror candidate",
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["object", "add", "gate-e", "--address",
                                   "mirror", "--label", "Mirror",
                                   "--anchor", "آینه", "--anchor", "آیینه",
                                   "--confirmation-file", str(conf),
                                   "--workspaces-dir", ws_dir])
    assert code == 0, err or out

    # walk: accept all 7 mirror hits (assessed-full coverage)
    script = tmp_path / "walk.json"
    script.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    code, out, err = _run(capsys, ["walk", "gate-e", "--object", "mirror",
                                   "--script", str(script), *base, "--json"])
    assert code == 0, err or out
    walk = json.loads(out)
    assert walk["summary"]["accepted"] == 7 and walk["unassessed"] == 0

    # assessed-full census: the card appears, operation persisted
    code, out, err = _run(capsys, ["census", "gate-e", "--object", "mirror",
                                   "--mode", "assessed-full", *base, "--json"])
    assert code == 0, err or out
    census = json.loads(out)
    assert census["mode"] == "assessed-full"
    op_id = census["operation_record_id"]
    card = census["card"]
    assert card["denominator"] > 0 and "sentence" in card and "choices" in card

    # source return from the stored manifest (no --corpus-root: the
    # stored manifest + study config resolve the passages)
    code, out, err = _run(capsys, ["source", "show", "gate-e", "--operation",
                                   op_id, "--workspaces-dir", ws_dir,
                                   "--json"])
    assert code == 0, err or out

    # Finding citing the governed operation (U04 route)
    finding = tmp_path / "finding.json"
    finding.write_text(json.dumps({
        "id": "f-gate-e", "pressure": "does mirror concentrate?",
        "operation_or_construction": op_id,
        "observation": f"mirror assessed at {census['numerator']}/{census['denominator']}",
        "consequence": "concentrated in sample1", "limits": "fixture corpus",
    }), encoding="utf-8")
    code, out, err = _run(capsys, ["record", "add", "gate-e", "--type",
                                   "finding", "--file", str(finding),
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out

    # release renders
    code, out, err = _run(capsys, ["release", "gate-e", "--version", "0.5.0",
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    assert json.loads(out)["tag"] == "v0.5.0"
