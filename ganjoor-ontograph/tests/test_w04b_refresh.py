"""Ledger row W04B (Amendment §19.4): `inquire --refresh <catalog-id>`.

Discriminating targets:

1. Refresh appends a NEW superseding catalog with verified support
   statuses (never rewrites the original — append-only).
2. Stale/unknown/mixed-situation input writes NOTHING and exits nonzero.
3. After refresh, the new catalog's lexical candidates carry real counts
   + located evidence; the original catalog is unchanged on disk.
4. Emits the review template + exact next command (W05 review).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.cli import main as cli_main
from ontograph.inquiry import read_catalogs, read_reviews
from ontograph.workspace import new_study


@pytest.fixture()
def study_with_catalog(tmp_path: Path) -> tuple[Path, str]:
    fixture = Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"
    study = new_study(tmp_path / "ws", "w04b-study", corpus_root=str(fixture))
    import contextlib, io

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = cli_main([
            "inquire", str(study), "--hunch", "آینه و زنگار", "--actor", "mz",
            "--persian-form", "آینه", "--persian-form", "آینه و زنگار",
            "--json",
        ])
    assert rc == 0
    catalog_id = read_catalogs(study)[0].id
    return study, catalog_id


def _run(study: Path, *args):
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(["inquire", str(study), *args, "--json"])
    return rc, out.getvalue(), err.getvalue()


def test_refresh_appends_superseding_verified_catalog(study_with_catalog) -> None:
    study, catalog_id = study_with_catalog
    rc, out, err = _run(study, "--refresh", catalog_id, "--actor", "mz")
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["catalog_id"] != catalog_id, "new catalog appended"
    assert payload["supersedes"] == catalog_id

    catalogs = read_catalogs(study)
    assert len(catalogs) == 2, "append-only: original preserved"
    new = [c for c in catalogs if c.id == payload["catalog_id"]][0]
    verified = [c for c in new.candidates if c.support_status == "supported"]
    assert verified, "آینه (and the phrase) should have support in the fixture corpus"
    assert all(c.evidence for c in verified)
    assert verified[0].hit_count > 0


def test_original_catalog_unchanged_on_disk(study_with_catalog) -> None:
    study, catalog_id = study_with_catalog
    before = (study / "research" / "inquiry-catalogs.jsonl").read_bytes()
    _run(study, "--refresh", catalog_id, "--actor", "mz")
    lines = (study / "research" / "inquiry-catalogs.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["id"] == catalog_id
    original = json.loads(lines[0])
    assert original["candidates"][0]["support_status"] == "unsupported", (
        "the ORIGINAL catalog's candidates stay unverified — verification lives "
        "in the new appended catalog"
    )


def test_unknown_catalog_id_writes_nothing(study_with_catalog) -> None:
    study, _ = study_with_catalog
    before = (study / "research" / "inquiry-catalogs.jsonl").read_bytes()
    rc, out, err = _run(study, "--refresh", "ic-nonexistent", "--actor", "mz")
    assert rc != 0 and out == ""
    assert (study / "research" / "inquiry-catalogs.jsonl").read_bytes() == before


def test_refresh_emits_review_next_command(study_with_catalog) -> None:
    study, catalog_id = study_with_catalog
    rc, out, _ = _run(study, "--refresh", catalog_id, "--actor", "mz")
    payload = json.loads(out)
    assert payload["next_command"]
    assert "review" in payload["next_command"] or payload.get("review_template")
