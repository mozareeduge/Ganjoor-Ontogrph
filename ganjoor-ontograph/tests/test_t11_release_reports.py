"""Ledger row T11: reports solely from release content; actual
values/limits/sources; the §6.7 5/27 fixture appears in the OperationRecord,
release references, and Markdown+HTML.

Discriminating targets:

1. The renderer reads ONLY the staged release directory — no workspace
   fallback, no recomputation (a renderer that computes is the forbidden
   shortcut; spec §3: "a renderer never computes research results").
2. Actual operation values appear verbatim: the fixture operation's
   5/27 prevalence shows up in release.json references, report.md, and
   report.html.
3. Limitations from the OperationRecord are carried into the report.
4. Source manifest entries are cited in the report (poem paths).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.release_v2 import collect_release
from ontograph.report_v2 import render_release_reports


def _stage(tmp_path: Path) -> Path:
    return collect_release(
        workspace=tmp_path, version="0.1.1", study_id="fixture-study",
        corpus_snapshot={"snapshot_id": "cs1-test"},
        operations=[{
            "id": "op-1", "operation_type": "census", "operation_version": "2.0.0",
            "parameters": {"object": "mirror", "mode": "assessed-full"},
            "result": {"numerator": 5, "denominator": 27, "prevalence": "5/27"},
            "source_manifest": [
                {"poem_id": 9101, "path": "poets/sample1/ghazal/p9101.json",
                 "hit_ids": ["ah1-a"], "verse_orders": [1], "couplet_indexes": [0]},
                {"poem_id": 9102, "path": "poets/sample1/ghazal/p9102.json",
                 "hit_ids": ["ah1-b"], "verse_orders": [2], "couplet_indexes": [1]},
            ],
            "limitations": ["ambiguous poem 9105 stays in the denominator"],
            "corpus_snapshot": {"snapshot_id": "cs1-test"},
        }],
    )


def test_report_carries_actual_values_sources_limits(tmp_path: Path) -> None:
    out = _stage(tmp_path)
    md_path, html_path = render_release_reports(out)
    md = md_path.read_text(encoding="utf-8")
    assert "5/27" in md
    assert "poets/sample1/ghazal/p9101.json" in md
    assert "ambiguous poem 9105 stays in the denominator" in md
    html = html_path.read_text(encoding="utf-8")
    assert "5/27" in html and "p9101.json" in html


def test_renderer_reads_staged_only_no_workspace_fallback(tmp_path: Path) -> None:
    out = _stage(tmp_path)
    # poison the workspace with a value that must NOT appear if the
    # renderer accidentally falls back to it
    ws_ops = tmp_path / "corpus" / "operations.jsonl"
    ws_ops.parent.mkdir(parents=True, exist_ok=True)
    ws_ops.write_text(json.dumps({"id": "ws-only", "result": {"prevalence": "999/999"}}), encoding="utf-8")
    md_path, _ = render_release_reports(out)
    md = md_path.read_text(encoding="utf-8")
    assert "999/999" not in md
    assert "ws-only" not in md


def test_renderer_never_mutates_records(tmp_path: Path) -> None:
    out = _stage(tmp_path)
    before = (out / "records" / "operations.jsonl").read_bytes()
    render_release_reports(out)
    assert (out / "records" / "operations.jsonl").read_bytes() == before
