"""Ledger row W09B: inquiry status cards and reports.

Discriminating targets (openspec tasks.md W09B, Amendment §19.7):

1. `study status` carries an inquiry card: situation hunch (verbatim),
   candidates with support status + attribution, human reviews, and
   governed/unframed operation counts — exactly as stored.
2. Status card exposes assessment coverage per object and stale/orphan
   hygiene counts (W07B chain, now with the inquiry detail behind them).
3. Staged-only Markdown/HTML reports (report_v2, W09A layout) show the
   inquiry history: verbatim hunch, candidate support/attribution,
   review state, provenance links — values match the stored records.
4. No descriptive co-incidence grid is added anywhere.
5. The CLI `release` verb on a GOVERNED study stages the full §6.7+§19.7
   layout (records/ JSONL + manifest + RELEASE.md) and the staged
   release verifies standalone.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ontograph.cli import main
from ontograph.release_v2 import collect_governed_release
from ontograph.report_v2 import render_release_reports
from ontograph.verify_release import verify_release

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _governed_workspace(capsys, tmp_path: Path, study_id: str = "w09b") -> tuple[Path, str]:
    ws_dir = str(tmp_path / "ontograph-workspaces")
    ws = Path(ws_dir) / study_id

    def run(argv, expect=0):
        code, out, err = _run(capsys, argv)
        assert code == expect, err or out
        return out

    run(["study", "new", study_id, "--corpus-root", FIXTURE_ROOT,
         "--workspaces-dir", ws_dir])
    proposals = tmp_path / "proposals.json"
    proposals.write_text(json.dumps([{
        "kind": "lexical-anchor", "label": "mirror", "form": "آینه",
        "proposer": "hermes", "proposer_type": "agent",
        "rationale": "surface motif probe",
    }]), encoding="utf-8")
    run(["inquire", study_id, "--hunch", "mirrors as self-division",
         "--actor", "mz", "--file", str(proposals),
         "--workspaces-dir", ws_dir, "--json"])
    conf = tmp_path / "confirmation.json"
    conf.write_text(json.dumps({
        "human_actor": "mz", "receipt": "receipt-9b", "object_id": "mirror",
        "rationale": "human review of the mirror candidate",
    }), encoding="utf-8")
    run(["object", "add", study_id, "--address", "mirror", "--label", "Mirror",
         "--anchor", "آینه", "--confirmation-file", str(conf),
         "--workspaces-dir", ws_dir])
    script = tmp_path / "walk.json"
    # the fixture's mirror object has 6 hits (all assessed in one walk)
    script.write_text(json.dumps({"responses": ["a"] * 6}), encoding="utf-8")
    run(["walk", study_id, "--object", "mirror", "--script", str(script),
         "--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT, "--json"])
    return ws, ws_dir


# --- 1+2. the status inquiry card ------------------------------------------------


def test_status_inquiry_card_exact_as_stored(tmp_path, capsys) -> None:
    ws, ws_dir = _governed_workspace(capsys, tmp_path)
    code, out, err = _run(capsys, ["study", "status", "w09b",
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    card = json.loads(out)["inquiry"]
    assert card["situations"][0]["verbatim_hunch"] == "mirrors as self-division"
    cand = card["candidates"][0]
    assert cand["form"] == "آینه"
    assert cand["support_status"] == "unsupported", "never refreshed in this fixture"
    assert cand["proposed_by"] == "agent:hermes"
    assert card["reviews"] == []
    assert card["operations_governed"] == 0, "no census ran yet"
    assert card["operations_unframed"] == 0


def test_status_card_counts_governed_operations_and_coverage(tmp_path, capsys) -> None:
    ws, ws_dir = _governed_workspace(capsys, tmp_path)
    _run(capsys, ["census", "w09b", "--object", "mirror", "--mode",
                  "assessed-full", "--workspaces-dir", ws_dir,
                  "--corpus-root", FIXTURE_ROOT, "--json"])
    code, out, err = _run(capsys, ["study", "status", "w09b",
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0
    card = json.loads(out)["inquiry"]
    assert card["operations_governed"] == 1
    assert card["coverage"]["mirror"]["assessed_hits"] == 6


# --- 3+4. staged-only reports show the inquiry history ----------------------------


def test_staged_reports_show_inquiry_history(tmp_path, capsys) -> None:
    ws, ws_dir = _governed_workspace(capsys, tmp_path)
    release_dir = collect_governed_release(
        ws, version="0.9.1", study_id="w09b",
        corpus_snapshot={"snapshot_id": "cs1-fixture"},
        field_charter="purpose: w09b",
    )
    md_path, html_path = render_release_reports(release_dir)
    md = md_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")

    assert "mirrors as self-division" in md, "hunch verbatim in the report"
    assert "آینه" in md and "unsupported" in md and "agent:hermes" in md
    assert "mirrors as self-division" in html
    assert "unsupported" in html
    # governance counts appear
    assert "governed" in md and "legacy-unframed" in md
    # NO descriptive co-incidence grid (§19.7: none is added)
    assert "co-incidence" not in md.lower()
    assert "co-incidence" not in html.lower()


# --- 5. governed CLI release stages + verifies ------------------------------------


def test_cli_governed_release_stages_and_verifies(tmp_path, capsys) -> None:
    ws, ws_dir = _governed_workspace(capsys, tmp_path)
    _run(capsys, ["census", "w09b", "--object", "mirror", "--mode",
                  "assessed-full", "--workspaces-dir", ws_dir,
                  "--corpus-root", FIXTURE_ROOT, "--json"])
    code, out, err = _run(capsys, ["release", "w09b", "--version", "0.9.2",
                                   "--workspaces-dir", ws_dir, "--json"])
    assert code == 0, err or out
    assert json.loads(out)["tag"] == "v0.9.2"
    release_dir = ws / "releases" / "v0.9.2"
    assert (release_dir / "records" / "research-situations.jsonl").exists()
    md = (release_dir / "report.md").read_text(encoding="utf-8")
    assert "mirrors as self-division" in md
    assert verify_release(release_dir)["valid"]
