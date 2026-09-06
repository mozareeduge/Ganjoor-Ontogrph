"""Ledger row U04: validated CRUD for all declared research records.

Discriminating targets (execution spec §7 record contract + §19.2):

1. `record add` accepts a YAML/JSON file for every declared type and
   validates the schema — round-trip: what you write is what `record
   show` returns and `record list` counts.
2. Invalid schemas fail BEFORE any write (exit != 0, no file mutated).
3. §19.2 store isolation: machine-managed stores (inquiry/review/
   assessment/operation/mapping/relation/claim/situation/seed) are
   refused on the generic route — they have their own governed writers.
4. Unknown types are refused.
5. Governed evidence rule (with W07B): a Finding may only cite governed
   operation records — legacy-unframed/missing citations refuse.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.cli import main

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed(capsys, tmp_path: Path, study_id: str) -> tuple[Path, list[str]]:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    ws = Path(ws_dir) / study_id
    code, out, err = _run(
        capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT,
                 "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    return ws, ["--workspaces-dir", ws_dir]


def _record_file(tmp_path: Path, name: str, payload: dict) -> str:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _trace_payload() -> dict:
    return {
        "id": "trace-u04-1",
        "initiating_encounters": [{
            "poem_id": 9101, "anchor": "آینه", "object_address": "mirror",
        }],
        "what_appeared": "mirror in poem 9101 during reading",
        "status": "active",
        "created_by": "u04-test",
    }


# --- 1. round-trip CRUD -------------------------------------------------------


def test_record_add_show_list_roundtrip(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-round")
    f = _record_file(tmp_path, "trace.json", _trace_payload())
    code, out, err = _run(
        capsys, ["record", "add", "u04-round", "--type", "trace",
                 "--file", f, *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["record_id"] == "trace-u04-1"

    code, out, err = _run(
        capsys, ["record", "show", "u04-round", "--id", "trace-u04-1",
                 *base, "--json"])
    assert code == 0, err or out
    assert json.loads(out)["what_appeared"] == "mirror in poem 9101 during reading"

    code, out, err = _run(
        capsys, ["record", "list", "u04-round", "--type", "trace",
                 *base, "--json"])
    assert code == 0, err or out
    listed = json.loads(out)
    assert listed["count"] == 1 and listed["ids"] == ["trace-u04-1"]


def test_record_yaml_file_accepted(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-yaml")
    p = tmp_path / "trace.yaml"
    p.write_text(
        "id: trace-y1\n"
        "initiating_encounters:\n"
        "  - poem_id: 9101\n"
        "    anchor: آینه\n"
        "    object_address: mirror\n"
        "what_appeared: yaml intake works\n"
        "status: active\n"
        "created_by: u04-test\n",
        encoding="utf-8",
    )
    code, out, err = _run(
        capsys, ["record", "add", "u04-yaml", "--type", "trace",
                 "--file", str(p), *base, "--json"])
    assert code == 0, err or out
    assert json.loads(out)["record_id"] == "trace-y1"


def test_record_add_all_declared_types(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-all")
    payloads = {
        "trace": _trace_payload(),
        "profile": {"id": "prof-1", "addressed_object_or_relation": "mirror",
                    "source_or_witness": "fixture mini-ganjoor",
                    "access_apparatus": "direct file access"},
        "experiment": {"id": "exp-1", "research_pressure": "does X hold"},
        "finding": {"id": "f-1", "pressure": "p", "observation": "o"},
    }
    for rtype, payload in payloads.items():
        f = _record_file(tmp_path, f"{rtype}.json", payload)
        code, out, err = _run(
            capsys, ["record", "add", "u04-all", "--type", rtype,
                     "--file", f, *base, "--json"])
        assert code == 0, f"{rtype}: {err or out}"
    code, out, err = _run(capsys, ["record", "list", "u04-all", *base, "--json"])
    listed = json.loads(out)
    assert listed["count"] == 4


# --- 2. invalid schemas refuse before write ------------------------------------


def test_record_add_invalid_schema_refuses(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-bad")
    before = (ws / "research" / "traces.jsonl").exists()
    # trace with no id and no observation content
    f = _record_file(tmp_path, "bad.json", {"status": "active"})
    code, out, err = _run(
        capsys, ["record", "add", "u04-bad", "--type", "trace",
                 "--file", f, *base])
    assert code != 0
    assert err.strip()
    assert (ws / "research" / "traces.jsonl").exists() == before


def test_record_add_unknown_type_refuses(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-unk")
    f = _record_file(tmp_path, "x.json", {"id": "x"})
    code, out, err = _run(
        capsys, ["record", "add", "u04-unk", "--type", "machine-store",
                 "--file", f, *base])
    assert code != 0


def test_record_add_missing_file_refuses(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-miss")
    code, out, err = _run(
        capsys, ["record", "add", "u04-miss", "--type", "trace",
                 "--file", str(tmp_path / "nope.json"), *base])
    assert code != 0


# --- 3. §19.2 machine-store isolation -------------------------------------------


def test_record_add_machine_managed_stores_refused(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-iso")
    for rtype in ("inquiry-catalog", "inquiry-review", "research-situation",
                  "seed", "occurrence-assessment", "operation", "mapping",
                  "relation", "claim"):
        f = _record_file(tmp_path, f"{rtype}.json", {"id": f"x-{rtype}"})
        code, out, err = _run(
            capsys, ["record", "add", "u04-iso", "--type", rtype,
                     "--file", f, *base])
        assert code != 0, f"{rtype} must be refused on the generic route"
        assert "governed" in err or "own route" in err or "refused" in err


# --- 5. governed evidence rule on Findings ---------------------------------------


def test_finding_citing_unframed_operation_refused(tmp_path, capsys) -> None:
    ws, base = _seed(capsys, tmp_path, "u04-gov")
    # a legacy-unframed operation in the store
    legacy = {
        "id": "op-old", "schema_version": "2.0.0", "study_id": "u04-gov",
        "operation_type": "census", "operation_version": "1.0.0",
        "created_at": "2026-09-06T10:00:00+00:00",
        "field_charter_version": "1.0.0", "scope_spec": {},
        "object_address_ids": ["mirror"], "parameters": {}, "result": {},
        "source_manifest": [], "corpus_snapshot": {"snapshot_id": "cs1-x"},
        "limitations": [],
    }
    ops = ws / "corpus" / "operations.jsonl"
    ops.parent.mkdir(parents=True, exist_ok=True)
    ops.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    payload = {"id": "f-bad", "pressure": "p", "observation": "o",
               "operation_or_construction": "op-old"}
    f = _record_file(tmp_path, "fbad.json", payload)
    code, out, err = _run(
        capsys, ["record", "add", "u04-gov", "--type", "finding",
                 "--file", f, *base])
    assert code != 0
    assert "legacy-unframed" in err
    assert not (ws / "research" / "findings.jsonl").exists()
