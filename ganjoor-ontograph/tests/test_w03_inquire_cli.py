"""Ledger row W03 (Amendment §19.4): `ontograph inquire <study> --hunch
... --json` — the CREATE form.

Discriminating targets:

1. Persists exactly ONE ResearchSituation and ONE candidate
   InquiryCatalog (atomically: both or neither).
2. Changes NO field/object/assessment/operation state.
3. Emits ONE JSON object on stdout; invalid input writes nothing.
4. Emits a review template + the exact next command (the machine guides
   the researcher to the next action — Amendment §19.4).
5. Works end-to-end against the fixture corpus via the CLI with the
   stored corpus_root (P9.1 flow).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ontograph.cli import main as cli_main


@pytest.fixture()
def study(tmp_path: Path) -> Path:
    """A fresh study bound to the fixture corpus (P9.1 stored root)."""
    from ontograph.workspace import new_study

    fixture = Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"
    return new_study(tmp_path / "workspaces", "inq-study", corpus_root=str(fixture))


def _run(study: Path, *args):
    import contextlib, io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(["inquire", str(study), *args, "--json"])
    return rc, out.getvalue(), err.getvalue()


def test_inquire_creates_situation_and_catalog_atomically(study: Path) -> None:
    rc, out, err = _run(
        study, "--hunch", "I keep noticing Rostam winning by cunning",
        "--actor", "mz",
        "--proposal", json.dumps({
            "kind": "lexical-anchor", "form": "کمند",
            "proposer": "mz", "rationale": "signature rope trick",
        }),
    )
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["situation_id"].startswith("rs-")
    assert payload["catalog_id"].startswith("ic-")
    assert payload["next_command"], "machine emits the exact next action"

    from ontograph.records_v2 import read_situations
    from ontograph.inquiry import read_catalogs

    situations = read_situations(study)
    catalogs = read_catalogs(study)
    assert len(situations) == 1 and len(catalogs) == 1
    # proposal landed as candidate-tier, unsupported
    assert catalogs[0].candidates[0].form == "کمند"
    assert catalogs[0].candidates[0].support_status == "unsupported"


def test_inquire_changes_no_analytical_state(study: Path) -> None:
    before = {
        p.name: p.read_bytes()
        for p in study.rglob("*") if p.is_file() and "research" not in p.parts
    }
    _run(study, "--hunch", "نبردهای رستم", "--actor", "mz")
    after = {
        p.name: p.read_bytes()
        for p in study.rglob("*") if p.is_file() and "research" not in p.parts
    }
    assert before == after, "inquire must not touch field/objects/corpus/events"


def test_invalidate_input_writes_nothing(study: Path) -> None:
    rc, out, err = _run(study, "--hunch", "x", "--actor", "")  # no actor
    assert rc != 0 and out == ""
    from ontograph.records_v2 import read_situations

    assert read_situations(study) == []


def test_english_hunch_reports_needs_vocabulary(study: Path) -> None:
    rc, out, err = _run(study, "--hunch", "Cunning beats force", "--actor", "mz")
    payload = json.loads(out)
    assert payload["needs_vocabulary"] is True
    assert "supplied attributed candidates" in payload["next_command"] or \
           payload["needs_vocabulary"] is True and payload.get("vocabulary_hint")
