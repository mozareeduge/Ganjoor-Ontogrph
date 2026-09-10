"""Ledger row W07B: bind operations to inquiry.

Discriminating targets (openspec tasks.md W07B, design §8, §19.2/§19.6):

1. In a GOVERNED workspace (inquiry history exists), field construction
   and every analytical command run the shared situation preflight:
   inherit one active situation, refuse zero (naming `inquire`), refuse
   many without --situation -- BEFORE any computation or write.
2. Governed analytical commands persist a governed OperationRecord
   (situation_id + inquiry_status=governed) BEFORE returning, and stdout
   carries operation_record_id -- a result without a persisted record
   cannot exist.
3. Ungoverned workspaces are untouched: no preflight, no persisted
   operation (the legacy route the amendment keeps as legacy-unframed).
4. Higher-record eligibility: a Finding citing a legacy-unframed or
   missing operation is refused -- never retro-linked, never auto-filled.
5. status shows governed vs unframed operation counts and stale/orphan
   records separately (chain stays additive so U01 pins still hold).
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.cli import main
from ontograph.records_v2 import ResearchSituation, persist_situation
from ontograph.w07 import governed_operation_eligible

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed_study(capsys, tmp_path: Path, study_id: str) -> tuple[str, list[str]]:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    code, out, err = _run(
        capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT,
                 "--workspaces-dir", ws_dir]
    )
    assert code == 0, err or out
    return ws_dir, ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]


def _make_governed(ws_dir: str, study_id: str, n: int = 1) -> list[str]:
    """Write n situations directly (real files; the situation store is the
    preflight's input, not the code under test)."""
    ws = Path(ws_dir) / study_id
    ids = []
    for i in range(n):
        s = ResearchSituation(
            study_id=study_id,
            verbatim_hunch=f"hunch {i} about mirrors",
            normalized_display_hunch=f"hunch {i} about mirrors",
            actor="mz",
        )
        persist_situation(ws, s)
        ids.append(s.id)
    return ids


def _conf_file(tmp_path: Path, object_id: str) -> str:
    p = tmp_path / "confirmation.json"
    p.write_text(json.dumps({
        "human_actor": "mz", "receipt": "receipt-1", "object_id": object_id,
    }), encoding="utf-8")
    return str(p)


# --- 1. governed preflight ----------------------------------------------------


def test_governed_field_build_inherits_single_situation(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-field")
    (sid,) = _make_governed(ws_dir, "w07b-field")
    code, out, err = _run(capsys, ["field", "build", "w07b-field", *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["situation_id"] == sid, "governed field build inherits the one active situation"
    charter = (Path(ws_dir) / "w07b-field" / "field" / "charter.yml").read_text(encoding="utf-8")
    assert sid in charter


def test_governed_field_build_zero_situations_refuses(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-field0")
    # governed via inquiry history but zero situations: catalog file exists
    ws = Path(ws_dir) / "w07b-field0"
    (ws / "research").mkdir(parents=True, exist_ok=True)
    (ws / "research" / "inquiry-catalogs.jsonl").write_text(
        json.dumps({"id": "ic1-x", "supersedes": None}) + "\n", encoding="utf-8")
    code, out, err = _run(capsys, ["field", "build", "w07b-field0", *base, "--json"])
    assert code != 0
    assert "inquire" in err
    assert not (ws / "field" / "charter.yml").exists(), "refusal happens before any write"


def test_governed_census_many_situations_refuse_without_explicit(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-many")
    _make_governed(ws_dir, "w07b-many", n=2)
    code, out, err = _run(
        capsys, ["object", "add", "w07b-many", "--address", "mirror",
                 "--label", "Mirror", "--anchor", "آینه",
                 "--confirmation-file", _conf_file(tmp_path, "mirror"),
                 "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["census", "w07b-many", "--object", "mirror", "--mode", "anchor",
                 *base, "--json"])
    assert code != 0
    assert "--situation" in err
    # explicit --situation disambiguates; preflight order matters: unknown ID refused
    code2, out2, err2 = _run(
        capsys, ["census", "w07b-many", "--object", "mirror", "--mode", "anchor",
                 "--situation", "rs1-nope", *base, "--json"])
    assert code2 != 0 and "not found" in err2


# --- 2. governed operations persist before return ------------------------------


def test_governed_census_persists_governed_operation(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-op")
    (sid,) = _make_governed(ws_dir, "w07b-op")
    code, out, err = _run(
        capsys, ["object", "add", "w07b-op", "--address", "mirror",
                 "--label", "Mirror", "--anchor", "آینه",
                 "--confirmation-file", _conf_file(tmp_path, "mirror"),
                 "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["census", "w07b-op", "--object", "mirror", "--mode", "anchor",
                 *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["operation_record_id"], "stdout carries the persisted record id"
    ops_path = Path(ws_dir) / "w07b-op" / "corpus" / "operations.jsonl"
    rows = [json.loads(l) for l in ops_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 1, "persisted exactly once, before return"
    assert rows[0]["id"] == result["operation_record_id"]
    assert rows[0]["situation_id"] == sid
    assert rows[0]["inquiry_status"] == "governed"
    assert rows[0]["result"]["hit_count"] == result["hit_count"], "record carries the computed result"


# --- 3. ungoverned flows are untouched ------------------------------------------


def test_ungoverned_census_has_no_operation_record(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-legacy")
    code, out, err = _run(
        capsys, ["object", "add", "w07b-legacy", "--address", "mirror",
                 "--label", "Mirror", "--anchor", "آینه", "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    code, out, err = _run(
        capsys, ["census", "w07b-legacy", "--object", "mirror", "--mode", "anchor",
                 *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert "operation_record_id" not in result
    assert not (Path(ws_dir) / "w07b-legacy" / "corpus" / "operations.jsonl").exists()


# --- 4. higher-record eligibility ------------------------------------------------


def test_finding_citing_unframed_or_missing_operation_refused(tmp_path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir(parents=True)
    legacy = {
        "id": "op-old", "schema_version": "2.0.0", "study_id": "s",
        "operation_type": "census", "operation_version": "1.0.0",
        "created_at": "2026-09-05T10:00:00+00:00",
        "field_charter_version": "1.0.0", "scope_spec": {},
        "object_address_ids": ["mirror"], "parameters": {}, "result": {},
        "source_manifest": [], "corpus_snapshot": {"snapshot_id": "cs1-x"},
        "limitations": [],
    }
    ops = ws / "corpus" / "operations.jsonl"
    ops.parent.mkdir(parents=True)
    ops.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    # missing reference: refused (orphans cannot support anything)
    ok, why = governed_operation_eligible(ws, ["op-absent"])
    assert not ok and why

    # legacy-unframed reference: refused with the reason naming the state
    ok, why = governed_operation_eligible(ws, ["op-old"])
    assert not ok and "legacy-unframed" in why

    # governed reference: eligible
    from ontograph.operations import build_operation_record, persist_operation_record
    from ontograph.anchors import AnchorHit
    hit = AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=9101,
        couplet_index=0, position="Right", original_text="ت", normalized_text="ت",
        token_start=0, token_end=1, verse_order=1, corpus_snapshot_id="cs1-test",
    )
    rec = build_operation_record(
        "s", "census", "1.0.0", {}, {"hit_count": 1}, [hit], "cs1-test",
        workspace=ws, situation_id="rs1-a",
    )
    persist_operation_record(ws, rec)
    ok, why = governed_operation_eligible(ws, [rec["id"]])
    assert ok, why


# --- 5. status chain additions ----------------------------------------------------


def test_status_shows_governed_unframed_and_stale(tmp_path, capsys) -> None:
    ws_dir, base = _seed_study(capsys, tmp_path, "w07b-status")
    _make_governed(ws_dir, "w07b-status")
    # study status takes only `common` (no --corpus-root) -- status reads
    # stored workspace state, never the corpus index (U01 contract)
    code, out, err = _run(
        capsys, ["study", "status", "w07b-status",
                 "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    chain = result["chain"]
    assert "operations_governed" in chain and "operations_unframed" in chain
    assert "stale" in chain and "orphans" in chain
