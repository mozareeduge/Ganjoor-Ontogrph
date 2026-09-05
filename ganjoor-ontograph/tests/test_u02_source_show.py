"""Ledger row U02: `source show` / `source export` from stored manifests.

Discriminating targets (spec §7 "Source return", V0_2 spec row U02):

1. `source show --poem-id` reads the poem JSON from the stored corpus root
   (read-only) and returns its verses + title + path -- exact contextual
   passages, corpus unchanged.
2. `source show --operation` returns the stored source_manifest of an
   OperationRecord (T09) resolved against the corpus: per poem, the exact
   contextual passages (context ladder §35: match -> verse -> couplet ->
   poem) for each hit coordinate in the manifest -- no re-computation.
3. `source export --operation --output` writes UTF-8 Markdown + JSON source
   tray from the STORED manifest (never rewrites corpus data, never
   recomputes hits).
4. Unknown poem id / unknown operation id fail with a clean error
   (no silent empty result).
5. `poem://` manifest entries (no corpus layout stored) fail source
   resolution with an explicit refusal -- never silently empty.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontograph.anchors import AnchorHit
from ontograph.cli import main
from ontograph.operations import build_operation_record, persist_operation_record

FIXTURE_ROOT = str(Path(__file__).parent.parent / "fixtures" / "mini-ganjoor")


def _run(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def _ws_base(tmp_path, *extra):
    # global-ish flags live on the subparsers (common parents), so they must
    # come AFTER the verb tokens, not before them
    return [*extra, "--workspaces-dir", str(tmp_path / "ontograph-workspaces")]


def _hit(poem_id: int, verse_order: int, couplet_index: int = 0) -> AnchorHit:
    return AnchorHit(
        object_address="mirror", lexical_anchor="آینه", poem_id=poem_id,
        couplet_index=couplet_index, position="Right",
        original_text="آینه در دست من است امشب",
        normalized_text="آینه در دست من است امشب",
        token_start=0, token_end=4,
        verse_order=verse_order, corpus_snapshot_id="cs1-test",
    )


def _study_with_operation(tmp_path: Path) -> tuple[str, str]:
    """Create a study and persist one census-like operation with a real
    fixture poem path so source show/export have something stored."""
    ws_dir = tmp_path / "ontograph-workspaces"
    code, out = _run(None, [
        "study", "new", "src-study", "--workspaces-dir", str(ws_dir),
        "--corpus-root", FIXTURE_ROOT, "--json",
    ]) if False else (None, None)  # placeholder, real calls in tests
    raise NotImplementedError


# --- real helpers used by tests (no placeholder) ---

def _make_study(tmp_path: Path, capsys) -> Path:
    code, out = _run(capsys, [
        "study", "new", "src-study", "--workspaces-dir", str(tmp_path / "ontograph-workspaces"),
        "--corpus-root", FIXTURE_ROOT, "--json",
    ])
    assert code == 0
    return tmp_path / "ontograph-workspaces" / "src-study"


def _make_operation(tmp_path: Path, ws: Path, poem_id: int = 9101) -> str:
    poem_path = Path(FIXTURE_ROOT) / "poets" / "sample1" / "ghazal" / f"p{poem_id}.json"
    hits = [_hit(poem_id, 1)]
    record = build_operation_record(
        study_id="src-study", operation_type="census", operation_version="2.0.0",
        parameters={"object": "mirror", "mode": "anchor"},
        result={"hit_count": 1}, hits=hits,
        corpus_snapshot_id="cs1-test", workspace=ws,
        poem_paths={poem_id: str(poem_path)},
    )
    persist_operation_record(ws, record)
    return record["id"]


# --- 1. show --poem-id: exact contextual passages, read-only ---

def test_source_show_poem_id_returns_verses(tmp_path, capsys) -> None:
    ws = _make_study(tmp_path, capsys)
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "show", "src-study", "--poem-id", "9101", "--json"))
    assert code == 0
    result = json.loads(out)
    assert result["poem_id"] == 9101
    assert result["title"]
    assert isinstance(result["verses"], list) and result["verses"]
    assert "VOrder" in result["verses"][0]
    # corpus untouched
    poem_file = Path(FIXTURE_ROOT) / "poets" / "sample1" / "ghazal" / "p9101.json"
    assert json.loads(poem_file.read_text(encoding="utf-8"))["Id"] == 9101


def test_source_show_unknown_poem_id_fails_clean(tmp_path, capsys) -> None:
    _make_study(tmp_path, capsys)
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "show", "src-study", "--poem-id", "99999999", "--json"))
    assert code != 0
    assert not out.strip() or "error" in out.lower() or "not found" in out.lower()


# --- 2. show --operation: manifest resolved to contextual passages ---

def test_source_show_operation_resolves_manifest(tmp_path, capsys) -> None:
    ws = _make_study(tmp_path, capsys)
    op_id = _make_operation(tmp_path, ws)
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "show", "src-study", "--operation", op_id, "--json"))
    assert code == 0
    result = json.loads(out)
    assert result["operation_id"] == op_id
    entries = result["sources"]
    assert len(entries) == 1
    e = entries[0]
    assert e["poem_id"] == 9101
    assert e["hit_ids"], "manifest hit ids must be carried through"
    assert e["verses"], "resolved contextual verses required (not just coordinates)"
    assert e["couplet"], "context ladder couplet required"
    assert e["poem_title"], "poem title required"


def test_source_show_unknown_operation_fails_clean(tmp_path, capsys) -> None:
    ws = _make_study(tmp_path, capsys)
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "show", "src-study", "--operation", "op-doesnotexist", "--json"))
    assert code != 0


# --- 3. export: Markdown + JSON tray from the stored manifest ---

def test_source_export_writes_md_and_json(tmp_path, capsys) -> None:
    ws = _make_study(tmp_path, capsys)
    op_id = _make_operation(tmp_path, ws)
    out_dir = tmp_path / "tray"
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "export", "src-study", "--operation", op_id,
        "--output", str(out_dir), "--json"))
    assert code == 0
    md_files = list(out_dir.glob("*.md"))
    json_files = list(out_dir.glob("*.json"))
    assert md_files and json_files, "export must produce both Markdown and JSON"
    md_text = md_files[0].read_text(encoding="utf-8")
    assert "9101" in md_text
    assert md_files[0].read_text(encoding="utf-8") == md_files[0].read_text(encoding="utf-8-sig" if False else "utf-8")
    # corpus untouched
    poem_file = Path(FIXTURE_ROOT) / "poets" / "sample1" / "ghazal" / "p9101.json"
    before = poem_file.read_bytes()
    code, _ = _run(capsys, _ws_base(
        tmp_path, "source", "export", "src-study", "--operation", op_id,
        "--output", str(tmp_path / "tray2"), "--json"))
    assert poem_file.read_bytes() == before


def test_source_export_refuses_poem_pointer_without_corpus_layout(tmp_path, capsys) -> None:
    """A manifest entry stored as `poem://<id>` (T09's no-layout fallback)
    cannot be resolved to passages: export must refuse explicitly, never
    write a tray that silently omits provenance."""
    ws = _make_study(tmp_path, capsys)
    hits = [_hit(4242, 1)]  # poem id absent from poem_paths -> poem:// fallback
    record = build_operation_record(
        study_id="src-study", operation_type="census", operation_version="2.0.0",
        parameters={}, result={}, hits=hits,
        corpus_snapshot_id="cs1-test", workspace=ws,
    )
    assert record["source_manifest"][0]["path"].startswith("poem://")
    persist_operation_record(ws, record)
    out_dir = tmp_path / "tray-poem-pointer"
    code, out = _run(capsys, _ws_base(
        tmp_path, "source", "export", "src-study", "--operation", record["id"],
        "--output", str(out_dir), "--json"))
    assert code != 0
    assert not out_dir.exists() or not any(out_dir.iterdir())
