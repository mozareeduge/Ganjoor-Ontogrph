"""OpenSpec row U06: researcher-facing skill documents the governed route.

The docs and allowlist must steer a fresh session through the actual
W09B-era apparatus:

study new -> inquire -> field/refresh -> human review -> walk ->
assessed-full operation -> source return -> Finding -> release.

The agent prepares proposal/review/script files and runs commands. The
researcher supplies semantic review and occurrence decisions.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontograph.cli import main
from ontograph.inquiry import read_catalogs

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / ".claude" / "skills" / "persian-poetry-ontograph"
FIXTURE_ROOT = PACKAGE_ROOT / "fixtures" / "mini-ganjoor"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_skill_surface_documents_governed_inquire_first_route() -> None:
    skill = _read(SKILL_ROOT / "SKILL.md")
    operations = _read(SKILL_ROOT / "references" / "operations.md")
    terminology = _read(SKILL_ROOT / "references" / "terminology.md")
    claim_permission = _read(SKILL_ROOT / "references" / "claim-permission.md")
    settings = json.loads(_read(REPO_ROOT / ".claude" / "settings.json"))

    lower_skill = skill.lower()
    assert "agent prepares" in lower_skill
    assert "researcher supplies" in lower_skill
    assert "governed fresh-session route" in lower_skill

    required_skill_fragments = [
        "ontograph study new",
        "ontograph inquire",
        "ontograph inquire \"$STUDY\" --refresh",
        "ontograph inquire \"$STUDY\" --review",
        "ontograph field build",
        "ontograph walk",
        "--mode assessed-full",
        "ontograph source show",
        "ontograph source export",
        "ontograph record add",
        "ontograph release",
    ]
    for fragment in required_skill_fragments:
        assert fragment in skill, f"skill route is missing {fragment!r}"

    assert skill.find("ontograph inquire") < skill.find("ontograph field build")
    assert "Every verb below `study new` also needs" not in skill
    assert "134 tests passing" not in skill
    assert "per poem, per\nobject" not in skill

    required_reference_fragments = [
        "ResearchSituation",
        "InquiryCatalog",
        "InquiryReview",
        "review approval != OccurrenceAssessment",
        "lexical neighbor != object",
        "CandidateEvidenceRef != Anchor Hit",
        "candidate cue != OccurrenceAssessment",
        "OperationRecord",
        "source manifest",
        "legacy-unframed",
        "co-incidence != Relation-Object",
        "Finding != artifact",
        "AI proposal != evidence",
        "provenance != corroboration",
    ]
    references_blob = "\n".join([operations, terminology, claim_permission])
    for fragment in required_reference_fragments:
        assert fragment in references_blob, f"references miss {fragment!r}"

    required_templates = [
        "inquiry-proposal.md",
        "inquiry-review.md",
        "walk-script.md",
        "finding.md",
        "research-situation.md",
        "field-charter.md",
        "research-release.md",
    ]
    for name in required_templates:
        assert (SKILL_ROOT / "templates" / name).is_file(), f"missing template {name}"

    allow = settings["permissions"]["allow"]
    required_allow_prefixes = [
        "ontograph study new",
        "ontograph inquire",
        "ontograph field build",
        "ontograph walk",
        "ontograph census",
        "ontograph source show",
        "ontograph source export",
        "ontograph record add",
        "ontograph release",
    ]
    for prefix in required_allow_prefixes:
        assert any(prefix in rule for rule in allow), f"missing allowlist rule for {prefix!r}"


def test_fresh_session_scripted_fixture_replay_matches_governed_skill_route(
    tmp_path: Path, capsys
) -> None:
    ws_dir = tmp_path / "ontograph-workspaces"
    study_id = "u06-fresh"
    base = ["--workspaces-dir", str(ws_dir), "--json"]

    code, out, err = _run(capsys, [
        "study", "new", study_id,
        "--corpus-root", str(FIXTURE_ROOT),
        "--workspaces-dir", str(ws_dir),
    ])
    assert code == 0, err or out
    study = ws_dir / study_id

    # The agent prepares an attributed proposal; the researcher supplies
    # the hunch and later the review decision.
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps([{
        "kind": "lexical-anchor",
        "label": "mirror",
        "form": "\u0622\u06cc\u0646\u0647",
        "proposer": "hermes",
        "proposer_type": "agent",
        "rationale": "candidate lexical route for the researcher's mirror hunch",
    }]), encoding="utf-8")

    code, out, err = _run(capsys, [
        "inquire", study_id,
        "--hunch", "mirrors as self-division",
        "--actor", "mz",
        "--file", str(proposal),
        *base,
    ])
    assert code == 0, err or out
    intake = json.loads(out)
    assert intake["situation_id"].startswith("rs-")
    first_catalog = intake["catalog_id"]

    code, out, err = _run(capsys, [
        "field", "build", study_id,
        "--workspaces-dir", str(ws_dir),
        "--corpus-root", str(FIXTURE_ROOT),
        "--json",
    ])
    assert code == 0, err or out

    code, out, err = _run(capsys, [
        "inquire", study_id,
        "--refresh", first_catalog,
        "--actor", "mz",
        *base,
    ])
    assert code == 0, err or out
    refreshed_catalog = json.loads(out)["catalog_id"]
    catalog = [c for c in read_catalogs(study) if c.id == refreshed_catalog][0]
    supported = [c for c in catalog.candidates if c.support_status == "supported"]
    assert supported and supported[0].evidence

    # W09B's implemented governed release path accepts an equivalent human
    # confirmation receipt for active object promotion. The skill still
    # documents `inquire --review` for the reviewed-candidate route.
    confirmation = tmp_path / "confirmation.json"
    confirmation.write_text(json.dumps({
        "human_actor": "mz",
        "receipt": "u06-human-review",
        "object_id": "mirror",
        "rationale": "human review accepts this as the provisional mirror route",
    }), encoding="utf-8")

    code, out, err = _run(capsys, [
        "object", "add", study_id,
        "--address", "mirror",
        "--label", "Mirror",
        "--anchor", "\u0622\u06cc\u0646\u0647",
        "--confirmation-file", str(confirmation),
        *base,
    ])
    assert code == 0, err or out
    object_id = "mirror"

    # The agent prepares the stable scripted walk; the researcher supplies
    # occurrence decisions. This one-anchor fixture route has 6 hits.
    walk_script = tmp_path / "walk.json"
    walk_script.write_text(json.dumps({"responses": ["a"] * 6}), encoding="utf-8")

    code, out, err = _run(capsys, [
        "walk", study_id,
        "--object", object_id,
        "--script", str(walk_script),
        "--workspaces-dir", str(ws_dir),
        "--json",
    ])
    assert code == 0, err or out
    walk = json.loads(out)
    assert walk["summary"]["accepted"] == 6
    assert walk["unassessed"] == 0

    code, out, err = _run(capsys, [
        "census", study_id,
        "--object", object_id,
        "--mode", "assessed-full",
        *base,
    ])
    assert code == 0, err or out
    census = json.loads(out)
    assert census["mode"] == "assessed-full"
    assert census["operation_record_id"]

    code, out, err = _run(capsys, [
        "source", "show", study_id,
        "--operation", census["operation_record_id"],
        *base,
    ])
    assert code == 0, err or out
    assert json.loads(out)["sources"]

    finding = tmp_path / "finding.json"
    finding.write_text(json.dumps({
        "id": "f-u06-mirror",
        "pressure": "does the reviewed mirror route produce a complete assessed count?",
        "operation_or_construction": census["operation_record_id"],
        "observation": f"mirror assessed at {census['numerator']}/{census['denominator']}",
        "consequence": "the fixture route can support a governed local Finding",
        "limits": "fixture corpus only",
    }), encoding="utf-8")

    code, out, err = _run(capsys, [
        "record", "add", study_id,
        "--type", "finding",
        "--file", str(finding),
        *base,
    ])
    assert code == 0, err or out

    code, out, err = _run(capsys, [
        "release", study_id,
        "--version", "0.6.0",
        *base,
    ])
    assert code == 0, err or out
    release = json.loads(out)
    assert release["tag"] == "v0.6.0"
    assert (study / "releases" / "v0.6.0" / "records" / "inquiry-catalogs.jsonl").is_file()
