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
    # W09B: the inquiry history — staged records only, verbatim
    situations = _load_jsonl(release_dir / "records" / "research-situations.jsonl")
    catalogs = _load_jsonl(release_dir / "records" / "inquiry-catalogs.jsonl")
    reviews = _load_jsonl(release_dir / "records" / "inquiry-reviews.jsonl")

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

    # --- W09B inquiry history section (§19.7): verbatim values only ---
    md_lines.append("## Inquiry history")
    html_parts.append("<h2>Inquiry history</h2>")
    if situations:
        for s in situations:
            hunch = s.get("verbatim_hunch", "")
            md_lines.append(
                f"- situation `{s.get('id')}` ({s.get('status')}) by "
                f"{s.get('actor')}: “{hunch}”"
            )
            html_parts.append(
                f"<p>situation <code>{html.escape(str(s.get('id')))}</code> "
                f"({html.escape(str(s.get('status')))}) by "
                f"{html.escape(str(s.get('actor')))}: "
                f"“{html.escape(str(hunch))}”</p>"
            )
    else:
        md_lines.append("- _(no research situations recorded)_")
        html_parts.append("<p><em>no research situations recorded</em></p>")
    for c in catalogs:
        for cd in (c.get("candidates") or []):
            proposed_by = f"{cd.get('proposer_type', '')}:{cd.get('proposer_id', '')}"
            md_lines.append(
                f"- candidate `{cd.get('candidate_id')}` — form "
                f"“{cd.get('form') or ''}” ({cd.get('kind')}), "
                f"support: {cd.get('support_status')}, "
                f"proposed by {proposed_by}"
            )
            html_parts.append(
                f"<p>candidate <code>{html.escape(str(cd.get('candidate_id')))}</code> — "
                f"form “{html.escape(str(cd.get('form') or ''))}” "
                f"({html.escape(str(cd.get('kind')))}), "
                f"support: {html.escape(str(cd.get('support_status')))}, "
                f"proposed by {html.escape(proposed_by)}</p>"
            )
    for r in reviews:
        md_lines.append(
            f"- review by {r.get('actor')}: `{r.get('candidate_id')}` "
            f"→ {r.get('decision')}"
        )
        html_parts.append(
            f"<p>review by {html.escape(str(r.get('actor')))}: "
            f"<code>{html.escape(str(r.get('candidate_id')))}</code> → "
            f"{html.escape(str(r.get('decision')))}</p>"
        )
    governed = sum(1 for o in operations if o.get("situation_id"))
    unframed = len(operations) - governed
    md_lines.append(
        f"- operations: {governed} governed, {unframed} legacy-unframed"
    )
    html_parts.append(
        f"<p>operations: {governed} governed, {unframed} legacy-unframed</p>"
    )
    md_lines.append("")

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
