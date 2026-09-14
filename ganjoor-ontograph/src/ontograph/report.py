"""Ledger row P9.8: Research Release rendering.

Renders what is actually in the study workspace — Profiles, Findings,
comparison/ablation numbers, Traces — as an HTML artifact plus a Markdown
report, by default. `generate_release()` already writes `release.json`
and a minimal `RELEASE.md`; this module renders the FULL picture:
embedded release content (object addresses, profiles, findings, traces
via the workspace's own record files) into `report.md` and `report.html`
next to the release JSON.

Design rules honored here:
- renders what exists; missing sections are shown as explicitly empty,
  never silently dropped;
- the researcher's binding decision (P9.8, user's own words): artifact/HTML
  + Markdown BY DEFAULT; other formats only on request (so this module has
  no other formats);
- numbers come from the release's embedded content — rendering adds no
  computation of its own (no epistemic logic in a renderer).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from ontograph.records import read_records


def _esc(s) -> str:
    return html.escape(str(s))


def collect_workspace_facts(workspace: Path) -> dict:
    """Traces are workspace records (P4.1) but not release-embedded lists —
    read them from the workspace so the report shows what actually exists.
    Same for object addresses when the release embedded none (the CLI's
    `release` verb passes no kwargs in v0.1, so release.json's
    object_addresses is empty even when the workspace has objects)."""
    ws = Path(workspace)
    traces = [
        _as_dict(r) for r in read_records(ws, "trace")
    ]
    facts = {"traces": traces}

    return facts


def _object_addresses_for(release: dict, ws: Path) -> list:
    embedded = release.get("object_addresses") or []
    if embedded:
        return embedded
    # fall back to the workspace's own object-addresses jsonl (the release
    # reflects the workspace; the renderer reads, never computes)
    path = ws / "objects" / "object-addresses.jsonl"
    if path.exists():
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out
    return []


def _as_dict(record) -> dict:
    from dataclasses import asdict, is_dataclass

    if is_dataclass(record):
        return asdict(record)
    return dict(record)


def render_markdown(release: dict, facts: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Research Release v{release.get('version', '?')}")
    lines.append("")
    lines.append(f"Release id: `{release.get('id', '?')}`")
    lines.append("")

    lines.append("## Object Addresses")
    lines.append("")
    objects = release.get("object_addresses") or []
    if objects:
        for o in objects:
            anchors = ", ".join(f"`{a}`" for a in o.get("anchors", []))
            lines.append(f"- **{_esc(o.get('id'))}** — anchors: {anchors}")
    else:
        lines.append("_(none embedded in this release)_")
    lines.append("")

    lines.append("## Load-Bearing Profiles")
    lines.append("")
    profiles = release.get("load_bearing_profiles") or []
    if profiles:
        for p in profiles:
            lines.append(f"- `{_esc(p.get('id', p))}`")
    else:
        lines.append("_(none embedded in this release)_")
    lines.append("")

    lines.append("## Findings")
    lines.append("")
    findings = release.get("findings") or []
    if findings:
        for f in findings:
            lines.append(f"- `{_esc(f.get('id', f))}`")
    else:
        lines.append("_(none embedded in this release)_")
    lines.append("")

    lines.append("## Traces")
    lines.append("")
    traces = facts.get("traces") or []
    if traces:
        for t in traces:
            lines.append(
                f"- `{_esc(t.get('id'))}` — {_esc(t.get('what_appeared') or '')} "
                f"(status: {_esc(t.get('status'))})"
            )
    else:
        lines.append("_(none in the workspace)_")
    lines.append("")

    lines.append("## Relation Objects / Experiments / Claims / Residue")
    lines.append("")
    for key, label in (
        ("active_relation_objects", "Relation Objects"),
        ("experiments", "Experiments"),
        ("claims", "Claims"),
        ("residue", "Residue"),
    ):
        items = release.get(key) or []
        lines.append(f"- {label}: {len(items)}")
    lines.append("")

    lines.append("## Data license notice")
    lines.append("")
    lines.append(release.get("data_license_notice", ""))
    lines.append("")
    return "\n".join(lines)


def render_html(release: dict, facts: dict) -> str:
    e = _esc

    def section(title: str, items: list, render_item) -> str:
        if not items:
            body = "<p><em>none embedded in this release</em></p>"
        else:
            body = "<ul>" + "".join(f"<li>{render_item(x)}</li>" for x in items) + "</ul>"
        return f"<h2>{e(title)}</h2>{body}"

    obj_items = "".join(
        f"<li><strong>{e(o.get('id'))}</strong> — anchors: "
        + "".join(f"<code>{e(a)}</code> " for a in o.get("anchors", []))
        + "</li>"
        for o in (release.get("object_addresses") or [])
    )

    traces = facts.get("traces") or []
    trace_items = "".join(
        f"<li><code>{e(t.get('id'))}</code> — {e(t.get('what_appeared') or '')} "
        f"(status: {e(t.get('status'))})</li>"
        for t in traces
    )

    counts = "".join(
        f"<li>{e(label)}: {len(release.get(key) or [])}</li>"
        for key, label in (
            ("active_relation_objects", "Relation Objects"),
            ("experiments", "Experiments"),
            ("claims", "Claims"),
            ("residue", "Residue"),
        )
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Research Release v{e(release.get('version', '?'))}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 50rem; margin: 2rem auto;
       padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }}
h1 {{ border-bottom: 2px solid #444; padding-bottom: .3rem; }}
h2 {{ margin-top: 1.6rem; font-size: 1.15rem; }}
code {{ background: #f2f2f2; padding: .05rem .3rem; border-radius: 3px; }}
em {{ color: #666; }}
footer {{ margin-top: 3rem; font-size: .85rem; color: #555;
          border-top: 1px solid #ccc; padding-top: .8rem; }}
</style>
</head>
<body>
<h1>Research Release v{e(release.get('version', '?'))}</h1>
<p>Release id: <code>{e(release.get('id', '?'))}</code></p>
<h2>Object Addresses</h2>
<ul>{obj_items if obj_items else '<li><em>none embedded in this release</em></li>'}</ul>
{section("Load-Bearing Profiles", release.get("load_bearing_profiles") or [],
         lambda p: f"<code>{e(p.get('id', p))}</code>")}
{section("Findings", release.get("findings") or [],
         lambda f: f"<code>{e(f.get('id', f))}</code>")}
<h2>Traces</h2>
<ul>{trace_items if trace_items else '<li><em>none in the workspace</em></li>'}</ul>
<h2>Relation Objects / Experiments / Claims / Residue</h2>
<ul>{counts}</ul>
<footer><h2>Data license notice</h2><p>{e(release.get("data_license_notice", ""))}</p></footer>
</body>
</html>
"""


def render_release_reports(workspace: str | Path, version: str) -> dict:
    """Render report.md + report.html into releases/v<version>/ from that
    directory's own release.json plus the workspace's record files."""
    ws = Path(workspace)
    release_dir = ws / "releases" / f"v{version}"
    release_json = release_dir / "release.json"
    if not release_json.exists():
        from ontograph.release import MissingLicenseNoticeError

        raise FileNotFoundError(
            f"no release.json at {release_json} — run 'ontograph release' first"
        )
    release = json.loads(release_json.read_text(encoding="utf-8"))
    facts = collect_workspace_facts(ws)
    release["object_addresses"] = _object_addresses_for(release, ws)

    md = render_markdown(release, facts)
    html_out = render_html(release, facts)
    (release_dir / "report.md").write_text(md, encoding="utf-8")
    (release_dir / "report.html").write_text(html_out, encoding="utf-8")
    return {
        "markdown": str(release_dir / "report.md"),
        "html": str(release_dir / "report.html"),
    }
