"""Ledger row T11: release report rendering — staged release content
ONLY (no workspace fallback, no recomputation), actual values, sources,
and limitations carried verbatim into report.md + report.html.

Spec §3 invariant: "a renderer never computes research results." Every
number, path, and limitation here is a READ of staged records; the only
transformation is formatting.
"""
from __future__ import annotations

import html
import json
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def render_release_reports(release_dir: Path) -> tuple[Path, Path]:
    """Render report.md + report.html from the staged release directory
    alone. Returns (markdown_path, html_path). Overwrites the T10
    placeholder reports; touches nothing else."""
    release_dir = Path(release_dir)
    release = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    operations = _load_jsonl(release_dir / "records" / "operations.jsonl")

    md_lines = [
        f"# Research Release v{release['version']}",
        "",
        f"Study: `{release['study_id']}` · corpus snapshot: `{release['corpus_snapshot_id']}`",
        "",
    ]
    html_parts = [
        f"<h1>Research Release v{html.escape(release['version'])}</h1>",
        f"<p>Study: <code>{html.escape(release['study_id'])}</code> · "
        f"corpus snapshot: <code>{html.escape(str(release['corpus_snapshot_id']))}</code></p>",
    ]

    md_lines.append("## Operations")
    html_parts.append("<h2>Operations</h2>")
    for op in operations:
        params = op.get("parameters", {})
        result = op.get("result", {})
        md_lines += [
            f"### `{op['id']}` — {op['operation_type']} ({op.get('operation_version')})",
            f"- parameters: {json.dumps(params, ensure_ascii=False)}",
            f"- result: {json.dumps(result, ensure_ascii=False)}",
        ]
        html_parts.append(
            f"<h3><code>{html.escape(op['id'])}</code> — {html.escape(op['operation_type'])}</h3>"
            f"<p>result: <code>{html.escape(json.dumps(result, ensure_ascii=False))}</code></p>"
        )
        for src in op.get("source_manifest", []):
            md_lines.append(f"- source: `{src['path']}` (poem {src['poem_id']})")
            html_parts.append(
                f"<p>source: <code>{html.escape(src['path'])}</code> "
                f"(poem {src['poem_id']})</p>"
            )
        for lim in op.get("limitations", []):
            md_lines.append(f"- limitation: {lim}")
            html_parts.append(f"<p>limitation: {html.escape(lim)}</p>")

    md_lines.append("")
    md_lines.append(f"Record counts: {json.dumps(release['record_counts'])}")

    md_path = release_dir / "report.md"
    html_path = release_dir / "report.html"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    html_path.write_text(
        "<!doctype html><html><body>" + "\n".join(html_parts) + "</body></html>",
        encoding="utf-8",
    )
    return md_path, html_path
