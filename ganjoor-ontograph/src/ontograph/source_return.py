"""Ledger row U02: source return (spec §7 "Source return").

`source show` / `source export` resolve the STORED source manifests of
OperationRecords (T09) back to exact contextual passages from the pinned
corpus, and render a portable source tray (Markdown + JSON). Nothing here
recomputes hits, rewrites corpus data, or invents provenance:

- Manifest entries carry `poem_id`, `path`, `hit_ids`, `verse_orders`,
  `couplet_indexes` (see operations.build_operation_record).
- `poem://<id>` entries (T09's no-corpus-layout fallback) cannot be
  resolved to passages -- show reports them as unresolved; export
  refuses outright (a tray with silently omitted provenance must never
  be produced).
- Context ladder per hit (§35): match verse -> couplet (right+left
  verses of CoupletIndex) -> poem title/path. Poem body is read from
  the stored corpus root; the poem JSON is never modified.
"""
from __future__ import annotations

import json
from pathlib import Path

SOURCE_EXPORT_MD_NAME = "source-tray.md"
SOURCE_EXPORT_JSON_NAME = "source-tray.json"


class SourceResolutionError(Exception):
    """Raised when a stored manifest cannot be resolved against the corpus."""


def read_operation(workspace: Path, operation_id: str) -> dict:
    """Find one OperationRecord by id in the workspace ledger."""
    path = Path(workspace) / "corpus" / "operations.jsonl"
    if not path.exists():
        raise SourceResolutionError(f"no operations ledger at {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("id") == operation_id:
            return rec
    raise SourceResolutionError(f"unknown operation id: {operation_id}")


def _load_poem(corpus_root: str, entry: dict) -> dict:
    rel = entry.get("path", "")
    if not rel or rel.startswith("poem://"):
        raise SourceResolutionError(
            f"poem {entry.get('poem_id')} has no stored corpus layout "
            f"({rel!r}); passages cannot be returned without re-running "
            "the operation against the corpus"
        )
    poem_path = Path(corpus_root) / rel
    if not poem_path.exists():
        raise SourceResolutionError(
            f"stored source path does not exist under corpus root: {rel}"
        )
    return json.loads(poem_path.read_text(encoding="utf-8"))


def _verses_for(poem: dict, entry: dict) -> list[dict]:
    """Exact match verses for the manifest's verse_orders, in manifest order."""
    by_order = {v.get("VOrder"): v for v in poem.get("Verses", [])}
    out = []
    for vo in entry.get("verse_orders", []):
        v = by_order.get(vo)
        if v is None:
            raise SourceResolutionError(
                f"poem {entry.get('poem_id')}: verse order {vo} not found"
            )
        out.append({"VOrder": v["VOrder"], "Position": v["Position"], "Text": v["Text"]})
    return out


def _couplet_for(poem: dict, entry: dict) -> list[dict]:
    """Full couplet(s) for the manifest's couplet_indexes: right+left verses
    sharing the CoupletIndex, in corpus order."""
    wanted = set(entry.get("couplet_indexes", []))
    verses = [
        {"VOrder": v["VOrder"], "Position": v["Position"], "Text": v["Text"]}
        for v in poem.get("Verses", [])
        if v.get("CoupletIndex") in wanted
    ]
    return verses


def resolve_operation_sources(
    corpus_root: str, record: dict, *, require_resolvable: bool = False
) -> list[dict]:
    """Resolve every source_manifest entry of an OperationRecord to exact
    contextual passages. With require_resolvable=True (export path), the
    first unresolvable entry raises instead of producing a silent gap."""
    sources = []
    for entry in record.get("source_manifest", []):
        try:
            poem = _load_poem(corpus_root, entry)
        except SourceResolutionError:
            if require_resolvable:
                raise
            sources.append({
                "poem_id": entry.get("poem_id"),
                "path": entry.get("path"),
                "resolved": False,
                "hit_ids": entry.get("hit_ids", []),
                "verses": [],
                "couplet": [],
                "poem_title": None,
            })
            continue
        sources.append({
            "poem_id": entry["poem_id"],
            "path": entry["path"],
            "resolved": True,
            "hit_ids": entry.get("hit_ids", []),
            "verse_orders": entry.get("verse_orders", []),
            "couplet_indexes": entry.get("couplet_indexes", []),
            "verses": _verses_for(poem, entry),
            "couplet": _couplet_for(poem, entry),
            "poem_title": poem.get("Title") or poem.get("FullTitle") or "",
        })
    return sources


def show_poem(corpus_root: str, poem_id: int) -> dict:
    """Return the poem's identity + full verse list (exact passages), read-only."""
    # The corpus layout is <root>/poets/<poet>/.../p<ID>.json; discover it
    # via glob rather than assuming the study's corpus taxonomy.
    matches = sorted(
        p for p in Path(corpus_root).glob("poets/**/p*.json") if p.is_file()
    )
    for p in matches:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get("Id") == poem_id:
            rel = p.relative_to(corpus_root).as_posix()
            verses = [
                {"VOrder": v["VOrder"], "Position": v["Position"], "Text": v["Text"]}
                for v in data.get("Verses", [])
                if v.get("Position") != "Comment"
            ]
            return {
                "poem_id": poem_id,
                "title": data.get("Title") or data.get("FullTitle") or "",
                "full_title": data.get("FullTitle") or "",
                "path": rel,
                "verses": verses,
            }
    raise SourceResolutionError(f"poem id {poem_id} not found in corpus at {corpus_root}")


def render_tray_markdown(record: dict, sources: list[dict]) -> str:
    lines = [
        f"# Source tray — operation {record['id']}",
        "",
        f"- study: {record.get('study_id', '')}",
        f"- operation type: {record.get('operation_type', '')}",
        f"- corpus snapshot: {record.get('corpus_snapshot', {}).get('snapshot_id', '')}",
        "",
    ]
    for s in sources:
        lines.append(f"## Poem {s['poem_id']} — {s.get('poem_title') or '(unresolved)'}")
        lines.append("")
        if not s.get("resolved"):
            lines.append(f"- ⚠ unresolved: no stored corpus layout ({s.get('path')})")
            lines.append("")
            continue
        lines.append(f"- path: `{s['path']}`")
        lines.append(f"- hits: {', '.join(s.get('hit_ids', [])) or '(none)'}")
        lines.append("")
        lines.append("### Match verses")
        lines.append("")
        for v in s.get("verses", []):
            lines.append(f"- [{v['VOrder']} {v['Position']}] {v['Text']}")
        lines.append("")
        lines.append("### Couplet context")
        lines.append("")
        for v in s.get("couplet", []):
            lines.append(f"- [{v['VOrder']} {v['Position']}] {v['Text']}")
        lines.append("")
    return "\n".join(lines)


def export_sources(
    record: dict, sources: list[dict], output_dir: Path
) -> dict:
    """Write the source tray (Markdown + JSON). Callers must pass sources
    resolved with require_resolvable=True so unresolvable manifests never
    reach this function."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / SOURCE_EXPORT_MD_NAME
    json_path = output_dir / SOURCE_EXPORT_JSON_NAME
    md = render_tray_markdown(record, sources)
    payload = {
        "operation_id": record["id"],
        "study_id": record.get("study_id"),
        "operation_type": record.get("operation_type"),
        "corpus_snapshot": record.get("corpus_snapshot"),
        "sources": sources,
    }
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "markdown": str(md_path),
        "json": str(json_path),
        "source_count": len(sources),
    }
