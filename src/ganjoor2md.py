#!/usr/bin/env python3
"""ganjoor2md — convert the Ganjoor JSON corpus into an agent-ready Markdown corpus.

Input:  a clone of ganjoor/ganjoor-data (poets/ tree of poet.json, _cat.json, poem JSONs)
Output: md/poets/<slug>/... Markdown files:
          - <slug>.md                poet biography + works list
          - <catpath>/_cat.md        category index (children + poems, as links)
          - <catpath>/<poemslug>.md  one file per poem (YAML frontmatter + couplets +
                                     quality-gated Persian summary section)

Design notes (see AGENTS.md in the repo root):
  - Every non-poet/_cat JSON file is treated as a poem, wherever it lives.
  - Poem body is rendered from Verses (grouped by section + couplet); prose items
    (no Verses) fall back to section PlainText.
  - The Persian PoemSummary is stripped of its «هوش مصنوعی:» prefix and dropped if
    it is junk (< 100 chars), so it never pollutes the corpus.
  - Multiprocessed per poet (each worker owns one poet directory) and resumable:
    existing outputs are skipped unless --force.
  - Deterministic ordering for reproducible builds. Stdlib only — no dependencies.

Usage:
    python3 src/ganjoor2md.py --input <ganjoor-data-repo> --output <md-root>
    python3 src/ganjoor2md.py --input . --output md --poets hafez,khayyam --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

POET_FILE = "poet.json"
CAT_FILE = "_cat.json"
AI_PREFIX = "هوش مصنوعی:"
AI_PREFIX_RE = re.compile(r"^\s*هوش\s+مصنوعی\s*[:：]?\s*")
SUMMARY_MIN_CHARS = 100  # below this the Persian summary is junk — drop it
RTL_BLANK = "\n"  # couplet separator

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def clean_ai_summary(text: str) -> str:
    """Strip the AI prefix, normalize whitespace, return '' if junk/short."""
    text = (text or "").strip()
    text = AI_PREFIX_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) < SUMMARY_MIN_CHARS:
        return ""
    return text


# Arabic diacritics (tashkeel) + tatweel; ZWNJ is kept in the canonical text but
# normalized to a space in the searchable plain section (Persian typing variants).
DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")
# Persian search normalization (versioned here — change forces a full corpus
# regenerate + re-embed, so bake in the complete mapping BEFORE big runs).
# Only map letters that are DISTINCT code points the QMD tokenizer does not
# unify; precomposed hamza letters (آ أ إ ؤ ئ) are deliberately left alone —
# SQLite unicode61 decomposes them symmetrically for doc AND query, so mapping
# them would only break the common correct spellings (آسان، رئیس).
#   Arabic yeh     ي ى  → ی (Farsi)
#   Arabic kaf     ك    → ک (Farsi)
#   teh marbuta    ة    → ه
#   Urdu-style heh ھ    → ه
CHAR_MAP = str.maketrans({
    "\u064A": "\u06CC", "\u0649": "\u06CC",
    "\u0643": "\u06A9",
    "\u0629": "\u0647", "\u06BE": "\u0647",
})
SPACE_RE = re.compile(r"[\u00A0\u2007\u202F \t]+")  # NBSP, figure space, narrow NBSP, spaces


def normalize_search_text(text: str) -> str:
    """Unvocalized, char-normalized text for the «متن ساده» search section."""
    text = DIACRITICS_RE.sub("", text)
    text = text.translate(CHAR_MAP)
    text = text.replace("\u200c", " ")
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def frontmatter(pairs: list) -> str:
    """Render YAML-ish frontmatter from an ordered (key, value) list."""
    lines = ["---"]
    for key, value in pairs:
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, (list, tuple)):
            items = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{items}]")
        else:
            # Quote only when needed (YAML-safe for Persian + special chars)
            s = str(value)
            if s != s.strip() or any(c in s for c in "\n:#[]{}&*!|>'\"%@`"):
                escaped = s.replace('"', '\\"')
                lines.append(f'{key}: "{escaped}"')
            else:
                lines.append(f"{key}: {s}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_couplets(poem: dict) -> str:
    """Render the poem body from Verses, grouped by (section, couplet).

    Returns '' when the poem has no usable verses (caller falls back to PlainText).
    """
    verses = poem.get("Verses") or []
    if not verses:
        return ""

    groups: dict[tuple, list] = {}
    for v in verses:
        section = v.get("SectionIndex1", 0)
        couplet = v.get("CoupletIndex", 0)
        groups.setdefault((section, couplet), []).append((v.get("VOrder", 0), v.get("Text", "")))

    blocks = []
    sections = sorted({s for s, _ in groups})
    for section in sections:
        if len(sections) > 1:
            blocks.append(f"## بخش {section + 1}\n")
        for key in sorted(k for k in groups if k[0] == section):
            ordered = sorted(groups[key])  # list of (VOrder, Text)
            texts = [text for _, text in ordered]
            if texts:
                blocks.append("\n".join(texts))
    return "\n\n".join(blocks)


def poem_format(poem: dict) -> str:
    """Most common PoemFormat across sections (sparse field — best effort)."""
    formats = [
        s.get("PoemFormat")
        for s in poem.get("Sections") or []
        if s.get("PoemFormat")
    ]
    if not formats:
        return ""
    return max(set(formats), key=formats.count)


def couplet_count(poem: dict) -> int:
    verses = poem.get("Verses") or []
    if verses:
        return len(verses) // 2
    return sum(int(s.get("CoupletsCount") or 0) for s in poem.get("Sections") or [])


def render_summary_fa(poem: dict, slug: str, poet_name: str, poem_md: Path, sum_md: Path) -> str | None:
    """Render the Persian-summary mirror file (md/summaries-fa/...) or None if no خلاصه.

    poem_md / sum_md are the *target* paths; the poem: pointer is computed relative
    to the summary file so the bridge works from either collection.
    """
    summary = clean_ai_summary(poem.get("PoemSummary") or "")
    if not summary:
        return None
    link = os.path.relpath(poem_md, start=sum_md.parent)
    full_url = poem.get("FullUrl", "")
    url = f"https://ganjoor.net{full_url}" if full_url else ""
    meta = [
        ("id", poem.get("Id")),
        ("title", poem.get("Title")),
        ("full_title", poem.get("FullTitle")),
        ("poet", poet_name),
        ("poet_slug", slug),
        ("format", poem_format(poem)),
        ("language", poem.get("Language") or "fa-IR"),
        ("url", url),
        ("poem", link),
    ]
    return frontmatter(meta) + summary.rstrip() + "\n"


def extract_enrichment(path: Path) -> dict:
    """Read enrichment state from an existing poem MD (for idempotent rebuilds).

    Returns keys: topics_en, summary_model, summary_date, summary_en ('' if absent).
    """
    result = {"topics_en": [], "summary_model": "", "summary_date": "", "summary_en": ""}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return result
    fm, body = split_frontmatter(text)
    topics = fm.get("topics_en", "")
    if isinstance(topics, str) and topics.startswith("["):
        inner = topics[1:-1].strip()
        result["topics_en"] = [v.strip().strip('"') for v in inner.split(",")] if inner else []
    result["summary_model"] = str(fm.get("summary_model", ""))
    result["summary_date"] = str(fm.get("summary_date", ""))
    m = re.search(r"## Summary \(EN\)\n+(.*?)(?=\n## |\Z)", body, re.S)
    if m:
        result["summary_en"] = m.group(1).strip()
    return result


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal frontmatter parse: (dict of str values, body)."""
    fm: dict = {}
    if not text.startswith("---"):
        return fm, text
    end = text.find("\n---", 3)
    if end < 0:
        return fm, text
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm, text[end + 4 :]


def render_poem(poem: dict, slug: str, poet_name: str, carry: dict | None = None) -> str:
    """Render one poem Markdown document."""
    carry = carry or {}
    title = poem.get("Title", "")
    full_title = poem.get("FullTitle", "")
    cat_path = ""
    full_url = poem.get("FullUrl", "")
    if full_url:
        parts = [p for p in full_url.split("/") if p]
        cat_path = "/".join(parts[1:-1])  # strip poet slug + poem slug
    url = f"https://ganjoor.net{full_url}" if full_url else ""

    summary = clean_ai_summary(poem.get("PoemSummary") or "")
    body = render_couplets(poem)
    if not body:
        body = "\n\n".join(
            (s.get("PlainText") or "").strip()
            for s in poem.get("Sections") or []
            if (s.get("PlainText") or "").strip()
        )
    plain = normalize_search_text(body) if body else ""

    parts = [body.strip()] if body.strip() else []
    if plain:
        parts.append("## متن ساده\n\n" + plain)
    if summary:
        parts.append("## خلاصه\n\n" + summary)
    if carry.get("summary_en"):
        parts.append("## Summary (EN)\n\n" + carry["summary_en"])
    content = parts[0] if len(parts) == 1 else "\n\n".join(parts)
    content = content.rstrip() + "\n"

    metre = poem.get("Metre") or {}
    meta = [
        ("id", poem.get("Id")),
        ("cat_id", poem.get("CatId")),
        ("title", title),
        ("full_title", full_title),
        ("poet", poet_name),
        ("poet_slug", slug),
        ("category_path", cat_path),
        ("format", poem_format(poem)),
        ("metre", metre.get("Rhythm")),
        ("metre_id", metre.get("Id")),
        ("rhyme", poem.get("RhymeLetters")),
        ("language", poem.get("Language") or "fa-IR"),
        ("source", poem.get("SourceName")),
        ("couplets", couplet_count(poem)),
        ("url", url),
        ("topics_en", carry.get("topics_en") or []),
        ("summary_model", carry.get("summary_model") or ""),
        ("summary_date", carry.get("summary_date") or ""),
    ]
    return frontmatter(meta) + content


def md_rel_link(current_full_url: str, target_full_url: str, suffix: str = "") -> str:
    """Relative markdown path between two ganjoor FullUrls (e.g. '/hafez/ghazal' → '/hafez/ghazal/sh1').

    current_full_url: the directory of the file being rendered
    target_full_url:  the file being linked to
    suffix:           '.md' for poems, '/_cat.md' for categories
    Both FullUrls share the leading poet slug, which is dropped before comparing.
    """
    from posixpath import join as pjoin

    cur = [p for p in current_full_url.split("/") if p][1:]  # drop poet slug
    tgt = [p for p in target_full_url.split("/") if p][1:]
    i = 0
    while i < len(cur) and i < len(tgt) and cur[i] == tgt[i]:
        i += 1
    ups = [".."] * (len(cur) - i)
    return pjoin(*(ups + tgt[i:])).rstrip("/") + suffix


def render_poet(poet: dict, root_cat: dict | None, slug: str) -> str:
    name = poet.get("Name", "")
    bio = (poet.get("Description") or "").strip()
    base = f"/{slug}"
    links = []
    if root_cat:
        for child in root_cat.get("ChildCats") or []:
            links.append(f"- [{child.get('Title', '')}]({md_rel_link(base, child.get('FullUrl', ''), '/_cat.md')})")
        for p in root_cat.get("Poems") or []:
            links.append(f"- [{p.get('Title', '')}]({md_rel_link(base, p.get('FullUrl', ''), '.md')})")

    body = []
    if bio:
        body.append(bio)
    if links:
        body.append("## آثار (Works)\n\n" + "\n".join(links))
    content = "\n\n".join(body).rstrip() + "\n" if body else "\n"

    meta = [
        ("id", poet.get("Id")),
        ("slug", slug),
        ("name", name),
        ("nickname", poet.get("Nickname")),
        ("birth_year_lunar_hijri", poet.get("BirthYearInLHijri")),
        ("death_year_lunar_hijri", poet.get("DeathYearInLHijri")),
        ("birth_place", poet.get("BirthPlace")),
        ("death_place", poet.get("DeathPlace")),
        ("url", f"https://ganjoor.net{poet.get('FullUrl', '')}" if poet.get("FullUrl") else ""),
    ]
    return frontmatter(meta) + content


def render_cat(cat: dict, slug: str, poet_name: str) -> str:
    title = cat.get("Title", "")
    desc = (cat.get("Description") or "").strip()
    full_url = cat.get("FullUrl", "")
    url = f"https://ganjoor.net{full_url}" if full_url else ""

    body = [f"# {title}"]
    if desc:
        body.append(desc)
    children = cat.get("ChildCats") or []
    poems = cat.get("Poems") or []
    cur_url = full_url or ""
    if children:
        lines = []
        for ch in children:
            lines.append(f"- [{ch.get('Title', '')}]({md_rel_link(cur_url, ch.get('FullUrl', ''), '/_cat.md')})")
        body.append("## زیرشاخه‌ها (Categories)\n\n" + "\n".join(lines))
    if poems:
        lines = []
        for p in poems:
            lines.append(f"- [{p.get('Title', '')}]({md_rel_link(cur_url, p.get('FullUrl', ''), '.md')})")
        body.append("## شعرها (Poems)\n\n" + "\n".join(lines))
    content = "\n\n".join(body).rstrip() + "\n"

    meta = [
        ("id", cat.get("Id")),
        ("poet_id", cat.get("PoetId")),
        ("poet", poet_name),
        ("poet_slug", slug),
        ("title", title),
        ("parent_id", cat.get("ParentId")),
        ("url", url),
    ]
    return frontmatter(meta) + content


# --------------------------------------------------------------------------
# One poet = one worker
# --------------------------------------------------------------------------


@dataclass
class PoetStats:
    poems: int = 0
    cats: int = 0
    errors: int = 0
    skipped: int = 0


def process_poet(args) -> tuple[str, PoetStats]:
    input_root, output_root, slug, force = args
    stats = PoetStats()
    src = Path(input_root) / "poets" / slug
    dst = Path(output_root) / "poets" / slug

    # Poet bio
    poet_path = src / POET_FILE
    try:
        poet = load_json(poet_path)
        root_cat = None
        root_cat_path = src / CAT_FILE
        if root_cat_path.exists():
            try:
                root_cat = load_json(root_cat_path)
            except Exception:
                root_cat = None
        out = dst / "poet.md"
        if force or not out.exists():
            write_md(out, render_poet(poet, root_cat, slug))
    except Exception as exc:  # noqa: BLE001 — per-file tolerance
        stats.errors += 1
        return slug, stats

    poet_name = poet.get("Name") or slug

    # Walk the poet's tree: categories and poems
    for dirpath, _dirnames, filenames in os.walk(src):
        dirpath_p = Path(dirpath)
        rel_dir = dirpath_p.relative_to(src)
        for fname in sorted(filenames):
            if not fname.endswith(".json"):
                continue
            src_file = dirpath_p / fname
            rel_file = (rel_dir / fname) if str(rel_dir) != "." else Path(fname)
            out_file = dst / rel_file.with_suffix(".md")

            if fname == CAT_FILE:
                try:
                    cat = load_json(src_file)
                    if force or not out_file.exists():
                        write_md(out_file, render_cat(cat, slug, poet_name))
                    stats.cats += 1
                except Exception:  # noqa: BLE001
                    stats.errors += 1
                continue

            if fname == POET_FILE:
                continue  # handled above

            # Poem
            if not force and out_file.exists():
                stats.skipped += 1
                continue
            carry = extract_enrichment(out_file) if (force and out_file.exists()) else None
            try:
                poem = load_json(src_file)
                write_md(out_file, render_poem(poem, slug, poet_name, carry))
                stats.poems += 1
                # Persian-summary mirror (md/summaries-fa/<slug>/...) — no LLM needed
                fa_out = Path(output_root) / "summaries-fa" / slug / rel_file.with_suffix(".md")
                fa_content = render_summary_fa(poem, slug, poet_name, out_file, fa_out)
                if fa_content:
                    write_md(fa_out, fa_content)
            except Exception:  # noqa: BLE001
                stats.errors += 1
    return slug, stats


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def discover_poets(input_root: Path) -> list[str]:
    poets_dir = input_root / "poets"
    if not poets_dir.is_dir():
        sys.exit(f"error: {input_root}/poets not found — is this a ganjoor-data clone?")
    return sorted(p.name for p in poets_dir.iterdir() if p.is_dir())


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Ganjoor JSON to agent-ready Markdown.")
    parser.add_argument("--input", default=".", help="path to the ganjoor-data clone (default: .)")
    parser.add_argument("--output", default="md", help="output root (default: md)")
    parser.add_argument("--poets", default="", help="comma-separated poet slugs; default: all")
    parser.add_argument("--force", action="store_true", help="reconvert even if output exists")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="worker processes")
    args = parser.parse_args()

    input_root = Path(args.input).resolve()
    output_root = Path(args.output).resolve()
    poets = [p.strip() for p in args.poets.split(",") if p.strip()] or discover_poets(input_root)

    tasks = [(str(input_root), str(output_root), slug, args.force) for slug in poets]
    totals = PoetStats()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for slug, stats in pool.map(process_poet, tasks, chunksize=1):
            totals.poems += stats.poems
            totals.cats += stats.cats
            totals.errors += stats.errors
            totals.skipped += stats.skipped
            print(f"{slug}: {stats.poems} poems, {stats.cats} cats, "
                  f"{stats.errors} errors, {stats.skipped} skipped", flush=True)

    print("\n=== SUMMARY ===")
    print(f"poets:      {len(poets)}")
    print(f"poems:      {totals.poems}")
    print(f"categories: {totals.cats}")
    print(f"errors:     {totals.errors}")
    print(f"skipped:    {totals.skipped}")
    print(f"output:     {output_root}")
    sys.exit(1 if totals.errors else 0)


if __name__ == "__main__":
    main()
