"""Ledger row U01 (Amendment §19.8/§19.9): `study status` and legal next actions.

The status verb reads STORED workspace state only (situations, catalogs,
reviews, objects, occurrence ledger, operations, findings) — it never
touches the corpus index, so it stays fast on the real corpus. Coverage
questions belong to `census --mode assessed` (T06 enforcement); status
reports the chain and the one legal next action per the §19.9 table.
"""
import json
import pathlib

from ontograph.cli import main


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def _ws(tmp_path, study="s1"):
    ws = tmp_path / "ontograph-workspaces" / study
    ws.mkdir(parents=True)
    return ws, ["--workspaces-dir", str(tmp_path / "ontograph-workspaces")]


# --- state 1: no situation -> inquire (never field/object promotion) ---

def test_no_situation_suggests_inquire(tmp_path, capsys):
    ws, base = _ws(tmp_path)
    code, out = _run(capsys, ["study", "status", "s1", *base, "--json"])
    assert code == 0, out
    result = json.loads(out)
    assert result["state"] == "no-situation"
    assert "inquire" in result["suggestion"]
    for forbidden in ("assessed census", "companions", "object add",
                       "promotion", "analysis"):
        assert forbidden not in result["suggestion"], forbidden
    assert result["chain"]["situations"] == 0


def _sit(ws, sid="rs-1", status="situational"):
    p = ws / "research" / "research-situations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": sid, "study_id": "s1", "verbatim_hunch": "h",
            "normalized_display_hunch": "h", "language_observations": [],
            "premature_decisions": [], "status": status, "actor": "human",
            "supersedes": None,
        }) + "\n")


def _cat(ws, cid="ic-1", sid="rs-1", candidates=None, supersedes=None):
    p = ws / "research" / "inquiry-catalogs.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": cid, "study_id": "s1", "situation_id": sid,
            "corpus_snapshot_id": "cs1-x", "field_id": "field-unbuilt",
            "scope_spec": {"kind": "all"}, "parameters": {},
            "limitations": [], "candidates": candidates or [],
            "supersedes": supersedes,
        }) + "\n")


def _cand(cid, kind="lexical-anchor", form="جن", support="unsupported"):
    return {"candidate_id": cid, "kind": kind, "form": form,
            "proposer_type": "human", "proposer_id": "u",
            "rationale": "r", "support_status": support,
            "hit_count": 0, "poem_count": 0, "poet_count": 0, "evidence": []}


def _rev(ws, catalog_id, candidate_id, decision="accept"):
    p = ws / "research" / "inquiry-reviews.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "catalog_id": catalog_id, "situation_id": "rs-1",
            "candidate_id": candidate_id, "decision": decision,
            "actor": "human", "rationale": "r", "receipt": "rc-1",
            "predecessor": None, "outputs": [],
        }) + "\n")


def _status(capsys, tmp_path, study="s1"):
    base = ["--workspaces-dir", str(tmp_path / "ontograph-workspaces")]
    code, out = _run(capsys, ["study", "status", study, *base, "--json"])
    assert code == 0, out
    return json.loads(out)


# --- state 2: no vocabulary -> attributed candidates, never invented ---

def test_no_vocabulary_suggests_attributed_candidates(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _sit(ws)
    _cat(ws, candidates=[_cand("c1", kind="non-object-note", form="")])
    result = _status(capsys, tmp_path)
    assert result["state"] == "no-vocabulary"
    assert "attributed" in result["suggestion"]
    assert "invented" not in result["suggestion"]


# --- state 3: unverified -> refresh, never promotion ---

def test_unverified_catalog_suggests_refresh(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _sit(ws)
    _cat(ws, candidates=[_cand("c1")])
    result = _status(capsys, tmp_path)
    assert result["state"] == "unverified-candidates"
    assert "refresh" in result["suggestion"]
    assert "promotion" not in result["suggestion"]


# --- state 4: stale review -> refresh/re-review, never promotion ---

def test_stale_review_suggests_refresh(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _sit(ws)
    _cat(ws, cid="ic-1", candidates=[_cand("c1")])
    _cat(ws, cid="ic-2", candidates=[_cand("c1")], supersedes="ic-1")
    _rev(ws, "ic-1", "c1")
    result = _status(capsys, tmp_path)
    assert result["state"] == "stale-review"
    assert "refresh" in result["suggestion"]
    assert "promotion" not in result["suggestion"]


# --- state 5: pending review -> human review, never automatic ---

def test_pending_review_suggests_human_review(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _sit(ws)
    _cat(ws, cid="ic-1", candidates=[_cand("c1")])
    _cat(ws, cid="ic-2", candidates=[_cand("c1")], supersedes="ic-1")
    result = _status(capsys, tmp_path)
    assert result["state"] == "pending-review"
    assert "human review" in result["suggestion"]
    assert "automatic" not in result["suggestion"]


def _obj(ws, addr="mirror", anchors=None):
    p = ws / "objects" / "object-addresses.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": addr, "label": addr,
                            "anchors": anchors or ["آینه"]}) + "\n")


def _op(ws, situation_id="rs-1"):
    p = ws / "corpus" / "operations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"operation_id": "op-1", "mode": "assessed-full"}
    if situation_id is not None:
        rec["situation_id"] = situation_id
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _finding(ws):
    from ontograph.records import FindingRecord, write_record
    write_record(ws, "finding", FindingRecord(id="f-1"))


def _reviewed(ws):
    _sit(ws)
    _cat(ws, cid="ic-1", candidates=[_cand("c1")])
    _cat(ws, cid="ic-2", candidates=[_cand("c1")], supersedes="ic-1")
    _rev(ws, "ic-2", "c1")
    _obj(ws)


# --- state 6: legacy-unframed operation -> inquire and rerun ---

def test_legacy_operation_suggests_inquire_and_rerun(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _sit(ws)
    _op(ws, situation_id=None)
    result = _status(capsys, tmp_path)
    assert result["state"] == "legacy-unframed"
    assert "inquire" in result["suggestion"] and "rerun" in result["suggestion"]
    assert "release" not in result["suggestion"]
    assert "higher-record" not in result["suggestion"]


# --- state 7: reviewed objects, no operation -> walk/rule/estimate ---

def test_objects_without_operation_suggest_walk(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _reviewed(ws)
    result = _status(capsys, tmp_path)
    assert result["state"] == "assess-objects"
    assert "walk" in result["suggestion"]
    assert "assessed-full" not in result["suggestion"]
    assert "catalog" not in result["suggestion"]


# --- state 8: governed operation, no finding -> source return + finding ---

def test_governed_operation_suggests_source_return_and_finding(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _reviewed(ws)
    _op(ws, situation_id="rs-1")
    result = _status(capsys, tmp_path)
    assert result["state"] == "operation-no-finding"
    assert "source" in result["suggestion"] and "Finding" in result["suggestion"]
    assert "automatic" not in result["suggestion"]


# --- state 9: finding -> release/continue/reopen, never final ---

def test_finding_suggests_release(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _reviewed(ws)
    _op(ws, situation_id="rs-1")
    _finding(ws)
    result = _status(capsys, tmp_path)
    assert result["state"] == "releaseable"
    assert "release" in result["suggestion"]
    assert "final" not in result["suggestion"]
