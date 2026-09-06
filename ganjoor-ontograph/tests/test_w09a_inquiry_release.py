"""Ledger row W09A: inquiry release collection and verification.

Discriminating targets (openspec tasks.md W09A, Amendment §19.7):

1. A governed release contains ResearchSituations, Seeds,
   InquiryCatalogs, InquiryReviews, and the event log (candidate
   encounter events included) — collected from the workspace stores.
2. Empty types are EXPLICIT empty files, never omitted.
3. A copied release verifies standalone (no workspace access).
4. Hash tampering fails verification.
5. Reference tampering fails verification even with a re-signed
   manifest: reviews citing missing catalogs, catalogs citing missing
   situations, and governed operations citing missing situations are
   all refused (§19.7: verify checks inquiry/review references and
   operation situation eligibility).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ontograph.cli import main
from ontograph.release_v2 import collect_governed_release
from ontograph.verify_release import verify_release

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _governed_workspace(capsys, tmp_path: Path) -> Path:
    """The governed chain through the CLI (situation, catalog with a
    candidate, one candidate-encounter walk event, assessments)."""
    ws_dir = str(tmp_path / "ontograph-workspaces")
    ws = Path(ws_dir) / "w09a"

    def run(argv, expect=0):
        code, out, err = _run(capsys, argv)
        assert code == expect, err or out
        return out

    run(["study", "new", "w09a", "--corpus-root", FIXTURE_ROOT,
         "--workspaces-dir", ws_dir])
    proposals = tmp_path / "proposals.json"
    proposals.write_text(json.dumps([{
        "kind": "lexical-anchor", "label": "mirror", "form": "آینه",
        "proposer": "hermes", "proposer_type": "agent",
        "rationale": "surface motif probe",
    }]), encoding="utf-8")
    out = run(["inquire", "w09a", "--hunch", "mirrors as self-division",
               "--actor", "mz", "--file", str(proposals),
               "--workspaces-dir", ws_dir, "--json"])
    cand_id = json.loads(out)["candidates"][0]
    conf = tmp_path / "confirmation.json"
    conf.write_text(json.dumps({
        "human_actor": "mz", "receipt": "receipt-9a", "object_id": "mirror",
        "rationale": "human review of the mirror candidate",
    }), encoding="utf-8")
    run(["object", "add", "w09a", "--address", "mirror", "--label", "Mirror",
         "--anchor", "آینه", "--confirmation-file", str(conf),
         "--workspaces-dir", ws_dir])
    script = tmp_path / "walk.json"
    # walk 1: pin a candidate encounter on hit 1 (stays undecided)
    script.write_text(json.dumps({"responses": [f"c:{cand_id}"] + [""] * 6}),
                      encoding="utf-8")
    run(["walk", "w09a", "--object", "mirror", "--script", str(script),
         "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    # walk 2: assess all hits (hit 1 now decided; encounter stays in the log)
    script.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    run(["walk", "w09a", "--object", "mirror", "--script", str(script),
         "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    # a governed census (walk writes assessments; census writes operations)
    run(["census", "w09a", "--object", "mirror", "--mode", "assessed-full",
         "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    return ws


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _collect(ws: Path, tmp_path: Path):
    return collect_governed_release(
        ws, version="0.9.0", study_id="w09a",
        corpus_snapshot={"snapshot_id": "cs1-fixture"},
        field_charter="purpose: w09a",
    )


# --- 1+2. collection ----------------------------------------------------------


def test_release_contains_inquiry_history(tmp_path, capsys) -> None:
    ws = _governed_workspace(capsys, tmp_path)
    release_dir = _collect(ws, tmp_path)
    recs = release_dir / "records"
    situations = _read_jsonl(recs / "research-situations.jsonl")
    catalogs = _read_jsonl(recs / "inquiry-catalogs.jsonl")
    events = _read_jsonl(recs / "events.jsonl")
    assert len(situations) == 1 and situations[0]["verbatim_hunch"] == "mirrors as self-division"
    assert len(catalogs) == 1 and catalogs[0]["candidates"][0]["form"] == "آینه"
    assert any("candidate" in str(e.get("event_type", "")) for e in events), \
        "the candidate-encounter event is collected"
    # empty types stay explicit
    assert (recs / "inquiry-reviews.jsonl").exists()
    assert (recs / "inquiry-reviews.jsonl").read_text(encoding="utf-8").strip() == ""


def test_release_record_counts_match_files(tmp_path, capsys) -> None:
    ws = _governed_workspace(capsys, tmp_path)
    release_dir = _collect(ws, tmp_path)
    rj = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    for rtype in ("research-situations", "seeds", "inquiry-catalogs",
                  "inquiry-reviews", "events"):
        rows = _read_jsonl(release_dir / "records" / f"{rtype}.jsonl")
        assert rj["record_counts"][rtype] == len(rows), rtype


# --- 3+4. standalone verify + hash tamper ---------------------------------------


def test_copied_release_verifies_and_hash_tamper_fails(tmp_path, capsys) -> None:
    ws = _governed_workspace(capsys, tmp_path)
    release_dir = _collect(ws, tmp_path)
    copy = tmp_path / "copy"
    shutil.copytree(release_dir, copy)
    assert verify_release(copy)["valid"], "copied release verifies without workspace"

    # hash tamper: flip a byte in a record file WITHOUT re-signing
    sit = copy / "records" / "research-situations.jsonl"
    lines = sit.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["verbatim_hunch"] = "TAMPERED"
    lines[0] = json.dumps(row, ensure_ascii=False)
    sit.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify_release(copy)
    assert not result["valid"]
    assert any("research-situations.jsonl" in i for i in result["issues"])


# --- 5. reference tampering fails even with a re-signed manifest -----------------


def _re_sign(release_dir: Path) -> None:
    """Recompute the manifest after an edit (simulates a malicious
    re-signed release — hash checks pass, references must not)."""
    lines = []
    for f in sorted(p for p in release_dir.rglob("*") if p.is_file()):
        rel = str(f.relative_to(release_dir)).replace("\\", "/")
        if rel == "manifest.sha256":
            continue
        lines.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}")
    (release_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_review_citing_missing_catalog_refused_after_re_sign(tmp_path, capsys) -> None:
    ws = _governed_workspace(capsys, tmp_path)
    release_dir = _collect(ws, tmp_path)
    copy = tmp_path / "copy-ref"
    shutil.copytree(release_dir, copy)

    reviews = copy / "records" / "inquiry-reviews.jsonl"
    reviews.write_text(json.dumps({
        "catalog_id": "ic1-ghost", "situation_id": "rs1-ghost",
        "candidate_id": "cand-1", "decision": "accept",
        "actor": "mz", "rationale": "forged", "receipt": "r-x",
    }) + "\n", encoding="utf-8")
    _re_sign(copy)
    result = verify_release(copy)
    assert not result["valid"], "a re-signed forged reference must still fail"
    assert any("catalog" in i for i in result["issues"])


def test_governed_operation_citing_missing_situation_refused(tmp_path, capsys) -> None:
    ws = _governed_workspace(capsys, tmp_path)
    release_dir = _collect(ws, tmp_path)
    copy = tmp_path / "copy-op"
    shutil.copytree(release_dir, copy)

    ops_path = copy / "records" / "operations.jsonl"
    ops = _read_jsonl(ops_path)
    assert ops, "the governed census operation was collected"
    ops[0]["situation_id"] = "rs1-vanished"
    ops_path.write_text(
        "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in ops),
        encoding="utf-8",
    )
    _re_sign(copy)
    result = verify_release(copy)
    assert not result["valid"]
    assert any("situation" in i for i in result["issues"])
