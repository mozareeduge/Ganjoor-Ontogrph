#!/usr/bin/env python3
"""enrich — generate English semantic summaries for the persian-poetry-ai-agent-plugin corpus.

Reads the Markdown corpus produced by ganjoor2md.py (md/poets/...), asks an
OpenAI-compatible chat API to write a concise English semantic summary + topic
keywords for each poem, then:

  1. Writes the summary mirror at md/summaries-en/<poet>/<path>/<slug>.md
     (frontmatter carries a relative `poem:` pointer back to the full Persian
     file — this is the `ganjoor-en` QMD collection).
  2. Patches the original poem file: `topics_en`, `summary_model`,
     `summary_date` in frontmatter and a `## Summary (EN)` section in the body.

Fully pluggable — any OpenAI-compatible endpoint works:

    OPENAI_BASE_URL   (default https://api.deepseek.com/v1)
    OPENAI_API_KEY    (required)
    ENRICH_MODEL      (default deepseek-v4-flash)

Quality gate: if the Persian خلاصه section is absent (ganjoor2md dropped junk
summaries), the prompt falls back to the poem text alone — still one call.

Resumable: poems whose frontmatter already contains `summary_model` are
skipped unless --force. Concurrent (IO-bound) via ThreadPoolExecutor.

Usage:
    python3 src/enrich.py --md md
    python3 src/enrich.py --md md --limit 100 --poets hafez --workers 8
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib import error as urlerror
from urllib import request

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
SUMMARY_SECTION = "## Summary (EN)"

SYSTEM_PROMPT = (
    "You are a literary translator specializing in classical Persian poetry. "
    "Convert the given Persian poem (and its Persian summary, if present) into a "
    "concise English semantic summary — 2-3 sentences capturing themes, imagery, "
    "and sentiment in plain modern English, written as a search anchor that someone "
    "might type when looking for this poem. Then list 4-8 short English topic keywords. "
    'Reply with ONLY valid JSON: {"summary_en": "...", "topics_en": ["...", "..."]}'
)

USER_TEMPLATE = """TITLE: {title}
POET: {poet}
FORMAT: {format}

POEM (Persian):
{poem}

{summary_block}Write the English semantic summary and topic keywords."""


# --------------------------------------------------------------------------
# Frontmatter helpers (mirror ganjoor2md conventions)
# --------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body after the closing ---)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fm_text = text[3:end]
    fm: dict = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"')
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            value = [v.strip().strip('"') for v in inner.split(",")] if inner else []
        fm[key] = value
    return fm, text[end + 4 :]


def set_frontmatter_key(text: str, key: str, value) -> str:
    """Set or replace a frontmatter key in a document."""
    fm, body = parse_frontmatter(text)
    if not text.startswith("---"):
        return text
    fm[key] = value
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            items = ", ".join(str(i) for i in v)
            lines.append(f"{k}: [{items}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + body


def get_summary_fa(body: str) -> str:
    """Extract the Persian خلاصه section from the body ('' if absent)."""
    m = re.search(r"## خلاصه\n+(.*?)(?=\n## |\Z)", body, re.S)
    if not m:
        return ""
    return m.group(1).strip()


def get_poem_text(body: str) -> str:
    """Poem text = everything before the first ## heading (or whole body)."""
    m = re.split(r"\n## ", body, maxsplit=1)
    return m[0].strip()


# --------------------------------------------------------------------------
# LLM call (stdlib urllib — zero dependencies)
# --------------------------------------------------------------------------


def call_llm(base_url: str, api_key: str, model: str, user_prompt: str, timeout: int = 120) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"].get("content") or ""
    if not content.strip():
        raise ValueError("empty LLM response content")
    return parse_json_response(content)


def call_llm_with_retry(base_url: str, api_key: str, model: str, user_prompt: str, retries: int = 4) -> dict:
    """Call with exponential backoff; empty/truncated JSON and rate limits are retried.

    HTTP 429/503 (rate limit, provider overload) get a long backoff (15s * attempt)
    so free-tier crawls survive; other errors use a short backoff.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return call_llm(base_url, api_key, model, user_prompt)
        except urlerror.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 503) and attempt < retries:
                time.sleep(15 * attempt)
            elif attempt < retries:
                time.sleep(1.5 * attempt)
        except Exception as exc:  # noqa: BLE001 — network/JSON all retried
            last_exc = exc
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise last_exc or ValueError("LLM call failed")


def parse_json_response(content: str) -> dict:
    """Robustly extract a JSON object from an LLM response."""
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise ValueError(f"no JSON object in response: {content[:200]!r}")
    return json.loads(m.group(0))


# --------------------------------------------------------------------------
# Per-poem work
# --------------------------------------------------------------------------


@dataclass
class EnrichStats:
    done: int = 0
    skipped: int = 0
    failed: int = 0


def enrich_one(path: Path, out_root: Path, base_url: str, api_key: str, model: str, force: bool, stats: EnrichStats) -> None:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if not force and fm.get("summary_model"):
        stats.skipped += 1
        return

    poem = get_poem_text(body)
    summary_fa = get_summary_fa(body)
    summary_block = f"PERSIAN SUMMARY:\n{summary_fa}\n\n" if summary_fa else ""
    user = USER_TEMPLATE.format(
        title=fm.get("full_title") or fm.get("title", ""),
        poet=fm.get("poet", ""),
        format=fm.get("format", ""),
        poem=poem[:4000],
        summary_block=summary_block,
    )

    result = call_llm_with_retry(base_url, api_key, model, user)
    summary_en = (result.get("summary_en") or "").strip()
    topics = [str(t).strip() for t in (result.get("topics_en") or []) if str(t).strip()]
    if not summary_en:
        raise ValueError(f"empty summary_en for {path}")

    today = time.strftime("%Y-%m-%d")

    # 1. Patch the poem file
    patched = set_frontmatter_key(text, "topics_en", topics)
    patched = set_frontmatter_key(patched, "summary_model", model)
    patched = set_frontmatter_key(patched, "summary_date", today)
    if SUMMARY_SECTION in patched:
        # Replace the existing English summary section (fresh generation wins).
        patched = re.sub(
            r"## Summary \(EN\)\n+.*?(?=\n## |\Z)",
            f"## Summary (EN)\n\n{summary_en}",
            patched,
            flags=re.S,
        )
    else:
        patched = patched.rstrip() + f"\n\n{SUMMARY_SECTION}\n\n{summary_en}\n"
    path.write_text(patched, encoding="utf-8")

    # 2. Write the summaries-en mirror
    rel = path.relative_to(out_root / "poets")
    sum_path = out_root / "summaries-en" / rel
    sum_path.parent.mkdir(parents=True, exist_ok=True)
    poem_link = os.path.relpath(path, start=sum_path.parent)
    meta = [
        f"---",
        f"id: {fm.get('id', '')}",
        f"title: {fm.get('title', '')}",
        f"full_title: {fm.get('full_title', '')}",
        f"poet: {fm.get('poet', '')}",
        f"poet_slug: {fm.get('poet_slug', '')}",
        f"format: {fm.get('format', '')}",
        f"url: {fm.get('url', '')}",
        f"poem: {poem_link}",
        f"topics_en: [{', '.join(topics)}]",
        f"summary_model: {model}",
        f"summary_date: {today}",
        f"---",
    ]
    sum_path.write_text("\n".join(meta) + f"\n\n{summary_en}\n", encoding="utf-8")
    stats.done += 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def discover_poems(md_root: Path, poets: list[str]) -> list[Path]:
    base = md_root / "poets"
    if poets:
        paths = []
        for slug in poets:
            paths.extend((base / slug).rglob("*.md"))
    else:
        paths = list(base.rglob("*.md"))
    # Exclude poet.md and _cat.md — enrichment is per poem
    return sorted(p for p in paths if p.name not in ("poet.md", "_cat.md"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate English semantic summaries.")
    parser.add_argument("--md", default="md", help="markdown corpus root (default: md)")
    parser.add_argument("--limit", type=int, default=0, help="max poems to enrich (0 = all)")
    parser.add_argument("--poets", default="", help="comma-separated poet slugs (default: all)")
    parser.add_argument("--workers", type=int, default=8, help="concurrent LLM calls")
    parser.add_argument("--force", action="store_true", help="re-enrich even if already done")
    args = parser.parse_args()

    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("ENRICH_MODEL", DEFAULT_MODEL)
    if not api_key:
        sys.exit("error: OPENAI_API_KEY is not set (any OpenAI-compatible provider works)")

    md_root = Path(args.md).resolve()
    poems = discover_poems(md_root, [p.strip() for p in args.poets.split(",") if p.strip()])
    if args.limit:
        poems = poems[: args.limit]
    print(f"enriching {len(poems)} poems | model={model} | base={base_url} | workers={args.workers}")

    stats = EnrichStats()
    failed_paths: list[tuple[Path, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(enrich_one, p, md_root, base_url, api_key, model, args.force, stats): p
            for p in poems
        }
        for i, fut in enumerate(as_completed(futures), 1):
            path = futures[fut]
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                stats.failed += 1
                failed_paths.append((path, str(exc)))
            if i % 25 == 0 or i == len(poems):
                print(f"  progress {i}/{len(poems)} | done={stats.done} skipped={stats.skipped} failed={stats.failed}")

    print("\n=== SUMMARY ===")
    print(f"done:    {stats.done}")
    print(f"skipped: {stats.skipped}")
    print(f"failed:  {stats.failed}")
    for path, err in failed_paths[:10]:
        print(f"  FAIL {path}: {err[:120]}")
    sys.exit(1 if stats.failed else 0)


if __name__ == "__main__":
    main()
