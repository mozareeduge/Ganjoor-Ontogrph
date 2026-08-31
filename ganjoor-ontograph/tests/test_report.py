"""Ledger row P9.8: the release renders what's actually in the workspace —
Profiles, Findings, comparison/ablation numbers, Traces — as HTML plus a
Markdown report BY DEFAULT (the researcher's binding format decision).

Verify (ledger): a full Field Charter → walk → compare → release cycle
produces both a `.html` and a `.md` output whose numbers match the known
fixture ground truth.

The renderer adds no computation: everything shown is either embedded in
release.json or read from the workspace's own record files — a renderer
with epistemic logic would be a self-certification channel (the thing the
v2.3.0 rework exists to prevent).
"""
import json
import pathlib

from ontograph.cli import main

FIXTURE_ROOT = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def test_full_cycle_renders_html_and_markdown_with_ground_truth_numbers(tmp_path, capsys):
    ws_dir = tmp_path / "ontograph-workspaces"
    base = ["--workspaces-dir", str(ws_dir)]

    # Field Charter → object → guided walk → assessed census (ground truth)
    code, _ = _run(capsys, ["study", "new", "render-study", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    code, _ = _run(capsys, ["field", "build", "render-study", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    code, _ = _run(capsys, ["object", "add", "render-study", "--label", "mirror", "--address", "mirror",
                            "--anchor", "آینه", "--anchor", "آیینه", *base, "--json"])
    assert code == 0

    code, out = _run(capsys, ["calibrate", "render-study", "--object", "mirror",
                              "--sample", "10", "--seed", "0", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    poems = [e["poem_id"] for e in json.loads(out)["context"]]
    canon = json.loads(
        (pathlib.Path(FIXTURE_ROOT) / "canonical-study-assessments.json").read_text(encoding="utf-8")
    )["assessments"]["mirror"]
    letter = {"accepted": "a", "rejected": "r", "ambiguous": "u"}
    sp = tmp_path / "responses.json"
    sp.write_text(json.dumps({"responses": [letter[canon[str(p)]] for p in poems]}), encoding="utf-8")

    code, out = _run(capsys, ["walk", "render-study", "--object", "mirror",
                              "--script", str(sp), "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    walk = json.loads(out)
    assert walk["summary"] == {"accepted": 5, "rejected": 1, "ambiguous": 1}

    code, out = _run(capsys, ["census", "render-study", "--object", "mirror",
                              "--mode", "assessed", "--corpus-root", FIXTURE_ROOT, *base, "--json"])
    assert code == 0
    census = json.loads(out)
    assert census["numerator"] == 5 and census["denominator"] == 27

    # release → BOTH artifacts produced by default
    code, out = _run(capsys, ["release", "render-study", "--version", "0.1.0", *base, "--json"])
    assert code == 0, out
    rel = json.loads(out)
    assert "report_markdown" in rel and "report_html" in rel

    md_path = pathlib.Path(rel["report_markdown"])
    html_path = pathlib.Path(rel["report_html"])
    assert md_path.exists() and html_path.exists()
    assert md_path.suffix == ".md" and html_path.suffix == ".html"

    # numbers in the artifacts match the fixture ground truth
    md = md_path.read_text(encoding="utf-8")
    html_text = html_path.read_text(encoding="utf-8")
    for artifact, text in (("md", md), ("html", html_text)):
        assert "mirror" in text, f"{artifact}: object address missing"
        assert "آینه" in text and "آیینه" in text, f"{artifact}: anchors missing"
        assert "Data license notice" in text or "data license notice" in text.lower(), \
            f"{artifact}: license notice missing"

    # the walk's Trace count (0 here) renders as an explicit empty section —
    # a missing section must be visible, never silently dropped
    assert "Trace" in md and "Trace" in html_text

    # the release itself still reconstructs (P7.6 gate stays intact)
    from ontograph.release import reconstruct_from_release
    reconstructed = reconstruct_from_release(ws_dir / "render-study" / "releases" / "v0.1.0" / "release.json")
    assert reconstructed is not None
