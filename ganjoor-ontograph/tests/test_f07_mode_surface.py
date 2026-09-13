"""Amendment 20 F07: CLI --mode surface for inventory/positioned-full/
positioned-concordant.

Discriminating targets (Plans.md F07 DoD):
1. `census --mode inventory` runs with zero positions recorded.
2. Every mode name is accepted by argparse (no "invalid choice" error).
3. Old `assessed`/`assessed-full` still work exactly as before.
4. The other four verbs refuse the new modes clearly instead of silently
   computing old semantics under a new label.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    from ontograph.cli import main

    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _seed(capsys, tmp_path: Path, study_id: str):
    ws_dir = str(tmp_path / "ontograph-workspaces")
    base = ["--workspaces-dir", ws_dir, "--corpus-root", FIXTURE_ROOT]
    code, out, err = _run(capsys, ["study", "new", study_id, "--corpus-root", FIXTURE_ROOT, "--workspaces-dir", ws_dir])
    assert code == 0, err or out
    code, out, err = _run(capsys, [
        "object", "add", study_id, "--address", "mirror", "--label", "Mirror",
        "--anchor", "آینه", "--anchor", "آیینه", "--workspaces-dir", ws_dir,
    ])
    assert code == 0, err or out
    return ws_dir, base


def test_census_inventory_mode_runs_with_zero_positions(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed(capsys, tmp_path, "f07-inventory")
    code, out, err = _run(capsys, ["census", "f07-inventory", "--object", "mirror", "--mode", "inventory", *base, "--json"])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["mode"] == "inventory"
    assert result["positioning"]["positioned_hits"] == 0
    assert "resolution_policy" not in result  # inventory never resolves an aggregate


def test_every_documented_mode_name_is_accepted_by_argparse(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed(capsys, tmp_path, "f07-modes")
    for mode in ("anchor", "inventory"):  # the two always-computable modes
        code, out, err = _run(capsys, ["census", "f07-modes", "--object", "mirror", "--mode", mode, *base, "--json"])
        assert code == 0, f"mode {mode!r} failed: {err or out}"
    # positioned-full/positioned-concordant are accepted by argparse but
    # correctly REFUSE at the gate with no policy declared (not an argparse error)
    for mode in ("positioned-full", "positioned-concordant"):
        code, out, err = _run(capsys, ["census", "f07-modes", "--object", "mirror", "--mode", mode, *base, "--json"])
        assert code == 1  # a clean refusal, not an argparse "invalid choice"
        assert "invalid choice" not in err.lower()
        assert "resolutionpolicy" in err.lower() or "policy" in err.lower()


def test_assessed_full_unchanged_via_old_route(tmp_path: Path, capsys) -> None:
    """The pre-existing assessed-full route must be untouched by F07."""
    ws_dir, base = _seed(capsys, tmp_path, "f07-old-route")
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps({"responses": ["a"] * 7}), encoding="utf-8")
    code, out, err = _run(capsys, [
        "walk", "f07-old-route", "--object", "mirror", "--script", str(sp), *base, "--json",
    ])
    assert code == 0, err or out
    code, out, err = _run(capsys, [
        "census", "f07-old-route", "--object", "mirror", "--mode", "assessed-full", *base, "--json",
    ])
    assert code == 0, err or out
    result = json.loads(out)
    assert result["mode"] == "assessed-full"
    assert result["numerator"] == 7  # all 7 hits scripted "a" (accepted)


def test_other_verbs_refuse_flat_modes_clearly(tmp_path: Path, capsys) -> None:
    ws_dir, base = _seed(capsys, tmp_path, "f07-refuse")
    code, out, err = _run(capsys, [
        "map", "recurrence", "f07-refuse", "--object", "mirror", "--mode", "inventory", *base, "--json",
    ])
    assert code == 1
    assert "not yet implemented" in err

    code, out, err = _run(capsys, [
        "ablate", "f07-refuse", "--remove", "poet:x", "--rerun", "relation:a-b",
        "--mode", "positioned-full", *base, "--json",
    ])
    assert code == 1
    assert "not yet implemented" in err
