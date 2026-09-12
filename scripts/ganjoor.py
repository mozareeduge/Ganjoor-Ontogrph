#!/usr/bin/env python3
"""ganjoor.py — single cross-platform entrypoint for the Ganjoor corpus pipeline.

Wraps `qmd` and the project's own converter/enrichment scripts behind one
consistent CLI that behaves the same on Windows, macOS and Linux. Python
3.10+, standard library only — never installs anything with pip.

Commands:
    doctor                          capability report for this environment
    setup                           install qmd (via npm) and sanity-check Python
    corpus [--poets a,b] [--tar F]  build md/ from Ganjoor JSON (or extract a tarball)
           [--jobs N] [--force]
    index                           build/refresh the QMD index (BM25 + metadata)
    embed [-c COLLECTION]           generate vectors for the summary collections
    search "<query>" [-c ganjoor]   exact BM25 search (qmd), or --offline for a
           [-n 5] [--offline]       pure-Python fallback needing no qmd/Node/models
    query "<query>" [-c ganjoor-fa] semantic/hybrid search (qmd query)
          [-n 5]
    mcp [--http] [--port 8191]      run the MCP server (stdio by default)
        [--stop] [--daemon]
    demo [--port 8090]              run the local web search demo

Run `python3 scripts/ganjoor.py <command> --help` for per-command options.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MD_ROOT = REPO_ROOT / "md"
QMD_DIR = REPO_ROOT / ".qmd"
QMD_INDEX = QMD_DIR / "index.sqlite"

COLLECTIONS = ("ganjoor", "ganjoor-fa", "ganjoor-en")
SUMMARY_COLLECTIONS = ("ganjoor-fa", "ganjoor-en")

HF_URL = "https://huggingface.co"

_SEMANTIC_FAILURE_MARKERS = (
    "huggingface.co",
    "StatusCodeError",
    "ECONNREFUSED",
    "ENOTFOUND",
    "EAI_AGAIN",
    "Tunnel connection failed",
    "Forbidden",
    "getaddrinfo",
    "host_not_allowed",
    "ETIMEDOUT",
)


# --------------------------------------------------------------------------
# Environment plumbing (UTF-8 output, qmd discovery, subprocess helpers)
# --------------------------------------------------------------------------


def _reconfigure_utf8() -> None:
    """Persian text must never crash on Windows when stdout/stderr is
    redirected (cp1252 -> UnicodeEncodeError). Degrade safely if the stream
    doesn't support reconfigure() (e.g. it's already been replaced)."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_reconfigure_utf8()


def find_qmd() -> str | None:
    """Locate the qmd executable. On Windows, npm's global install exposes a
    .cmd shim (and sometimes .exe) rather than a bare `qmd` — a plain
    ["qmd"] subprocess call fails there, so check those names too."""
    names = ["qmd.cmd", "qmd.exe", "qmd"] if os.name == "nt" else ["qmd"]
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def qmd_env() -> dict:
    env = dict(os.environ)
    env["QMD_TRUST_LOCAL_CONFIG"] = "1"
    return env


def require_qmd() -> str:
    qmd_path = find_qmd()
    if not qmd_path:
        print("error: `qmd` not found on PATH.", file=sys.stderr)
        print("Install it with:  npm install -g @tobilu/qmd", file=sys.stderr)
        print(
            "(On Windows this installs qmd.cmd — ganjoor.py already looks for that.)",
            file=sys.stderr,
        )
        sys.exit(1)
    return qmd_path


def run_qmd(qmd_path: str, args: list, **kwargs):
    """Run qmd with the project-local config trusted and cwd pinned to the
    repo root — never the caller's cwd."""
    kwargs.setdefault("cwd", REPO_ROOT)
    kwargs.setdefault("env", qmd_env())
    # qmd emits UTF-8. Without an explicit encoding, text mode decodes captured
    # output with the locale codec — cp1252 on Windows — which mangles or
    # crashes on Persian. Only applies to piped streams, so it is harmless for
    # the inherited-stdio cases (mcp stdio, demo).
    if kwargs.get("capture_output") or kwargs.get("text"):
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return subprocess.run([qmd_path, *args], **kwargs)


def _tool_version(cmd: list, env: dict | None = None, timeout: float = 8.0) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=REPO_ROOT,
        )
        text = (result.stdout or result.stderr or "").strip()
        return text.splitlines()[0] if text else None
    except Exception:
        return None


def _human_size(n: float) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# --------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------


def _count_md_files(root: Path) -> int:
    total = 0
    for _dirpath, _dirnames, filenames in os.walk(root):
        total += sum(1 for f in filenames if f.endswith(".md"))
    return total


def _qmd_status_text(qmd_path: str, timeout: float = 20.0) -> tuple[str | None, str | None]:
    try:
        result = run_qmd(qmd_path, ["status"], capture_output=True, text=True, timeout=timeout)
        return result.stdout, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _parse_collection_counts(text: str) -> dict:
    """Parse the per-collection `Files:` counts out of `qmd status` output."""
    counts = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^\s{2}(\S+) \(qmd://", line)
        if m:
            current = m.group(1)
            continue
        m2 = re.match(r"^\s+Files:\s+(\d+)", line)
        if m2 and current:
            counts[current] = int(m2.group(1))
            current = None
    return counts


def _parse_vectors_total(text: str) -> int | None:
    m = re.search(r"Vectors:\s+(\d+) embedded", text)
    return int(m.group(1)) if m else None


def _check_hf_reachable(timeout: float = 5.0) -> tuple[bool, str]:
    """Never hang: a short timeout, and any failure just means 'unreachable'."""
    try:
        req = urllib.request.Request(HF_URL, method="HEAD")
        urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
        return True, "reachable"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def _model_cache_present() -> bool:
    cache_dir = Path.home() / ".cache" / "qmd" / "models"
    if not cache_dir.is_dir():
        return False
    try:
        return any(p.is_file() and p.stat().st_size > 0 for p in cache_dir.rglob("*"))
    except OSError:
        return False


def cmd_doctor(args: argparse.Namespace) -> None:
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    node_ver = _tool_version([node_path, "--version"]) if node_path else None
    npm_ver = _tool_version([npm_path, "--version"]) if npm_path else None

    qmd_path = find_qmd()
    qmd_ver = _tool_version([qmd_path, "--version"], env=qmd_env()) if qmd_path else None

    md_exists = MD_ROOT.is_dir()
    md_files = _count_md_files(MD_ROOT) if md_exists else 0

    index_exists = QMD_INDEX.is_file()
    index_size = QMD_INDEX.stat().st_size if index_exists else 0

    coll_counts: dict = {}
    vectors_total = None
    status_err = None
    if qmd_path:
        status_text, status_err = _qmd_status_text(qmd_path)
        if status_text:
            coll_counts = _parse_collection_counts(status_text)
            vectors_total = _parse_vectors_total(status_text)

    free_bytes = shutil.disk_usage(REPO_ROOT).free
    hf_ok, hf_reason = _check_hf_reachable()
    model_cached = _model_cache_present()

    print("=" * 64)
    print("Ganjoor doctor")
    print("=" * 64)
    print(f"OS:              {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python:          {platform.python_version()} ({sys.executable})")
    print(
        "Node:            "
        + (f"{node_ver or 'unknown version'}  ({node_path})" if node_path else "NOT FOUND")
    )
    print(
        "npm:             "
        + (f"{npm_ver or 'unknown version'}  ({npm_path})" if npm_path else "NOT FOUND")
    )
    print(
        "qmd:             "
        + (
            f"{qmd_ver or 'unknown version'}  ({qmd_path})"
            if qmd_path
            else "NOT FOUND — npm install -g @tobilu/qmd"
        )
    )
    print()
    print(
        "md/:             "
        + (f"exists, {md_files} .md files" if md_exists else "MISSING — run `corpus`")
    )
    print(
        ".qmd/index.sqlite: "
        + (f"exists, {_human_size(index_size)}" if index_exists else "MISSING — run `index`")
    )
    if coll_counts:
        for c in COLLECTIONS:
            print(f"  collection {c:12s} {coll_counts.get(c, 'unknown')} docs")
    elif qmd_path:
        print(f"  (could not read collection counts from `qmd status`: {status_err})")
    if vectors_total is not None:
        print(f"  vectors embedded (index-wide): {vectors_total}")
    print(f"Free disk space: {_human_size(free_bytes)}")
    print(f"huggingface.co:  {'reachable' if hf_ok else 'UNREACHABLE'} ({hf_reason})")
    print(f"cached models:   {'present' if model_cached else 'none found'} (~/.cache/qmd/models)")

    ganjoor_docs = coll_counts.get("ganjoor")
    fa_docs = coll_counts.get("ganjoor-fa")
    en_docs = coll_counts.get("ganjoor-en")
    semantic_models_ok = hf_ok or model_cached

    caps = []

    if qmd_path and ganjoor_docs:
        caps.append(("Persian exact search", True, f"`search -c ganjoor` (BM25, {ganjoor_docs} docs indexed)"))
    elif md_files:
        reason = (
            "qmd not installed — using the offline exact-line fallback"
            if not qmd_path
            else "ganjoor collection has 0 docs indexed — using the offline fallback"
        )
        caps.append(("Persian exact search", True, f"{reason} (`search --offline`)"))
    else:
        caps.append(("Persian exact search", False, "no md/ corpus and no qmd index — run `corpus` then `index`"))

    for label, coll, docs, missing_hint in (
        ("Persian semantic", "ganjoor-fa", fa_docs, "run `index`"),
        ("English semantic", "ganjoor-en", en_docs, "md/summaries-en missing — run enrichment, then `index`"),
    ):
        if not qmd_path:
            caps.append((label, False, "qmd not installed"))
        elif not docs:
            caps.append((label, False, f"{coll} collection has 0 docs indexed — {missing_hint}"))
        elif not semantic_models_ok:
            caps.append(
                (
                    label,
                    False,
                    f"embedding model host huggingface.co is unreachable ({hf_reason}) "
                    "and no model is cached locally — `embed`/`query` cannot fetch it",
                )
            )
        else:
            caps.append((label, True, f"models available — run `embed -c {coll}` then `query`"))

    if qmd_path:
        caps.append(("MCP (stdio)", True, "`mcp` — works fully offline, this is what agents use"))
        caps.append(("MCP (HTTP)", True, "`mcp --http --port 8191` — works fully offline"))
    else:
        caps.append(("MCP (stdio)", False, "qmd not installed"))
        caps.append(("MCP (HTTP)", False, "qmd not installed"))

    if md_files:
        caps.append(
            ("Offline search (no Node)", True, f"`search --offline` — pure Python over {md_files} md files")
        )
    else:
        caps.append(("Offline search (no Node)", False, "md/ missing — run `corpus` first"))

    print()
    print("Capability matrix")
    print("-" * 64)
    any_ok = False
    for name, ok, reason in caps:
        any_ok = any_ok or ok
        tag = "OK" if ok else "UNAVAILABLE"
        print(f"  [{tag:11s}] {name:26s} {reason}")
    print("-" * 64)

    if args.strict and not any_ok:
        sys.exit(1)
    sys.exit(0)


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------


def cmd_setup(args: argparse.Namespace) -> None:
    qmd_path = find_qmd()
    if not qmd_path:
        npm_path = shutil.which("npm")
        if not npm_path:
            print(
                "error: npm not found. Install Node.js, then: npm install -g @tobilu/qmd",
                file=sys.stderr,
            )
            sys.exit(1)
        print("qmd not found — installing with `npm install -g @tobilu/qmd` ...")
        result = subprocess.run([npm_path, "install", "-g", "@tobilu/qmd"], cwd=REPO_ROOT)
        if result.returncode != 0:
            print("error: npm install failed.", file=sys.stderr)
            sys.exit(result.returncode)
        qmd_path = find_qmd()
        if not qmd_path:
            print(
                "error: qmd still not found on PATH after install "
                "(check that your npm global bin directory is on PATH).",
                file=sys.stderr,
            )
            sys.exit(1)

    qmd_ver = _tool_version([qmd_path, "--version"], env=qmd_env())
    print(f"qmd:     {qmd_ver or 'installed'}  ({qmd_path})")
    print(f"python3: {platform.python_version()}  ({sys.executable})")
    sys.exit(0)


# --------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------


def _safe_extractall(tf: tarfile.TarFile, dest: Path) -> None:
    """Manual path-traversal guard for Python versions without the
    `filter` kwarg on extractall (pre-3.12, pre security backport)."""
    dest_resolved = dest.resolve()
    for member in tf.getmembers():
        member_path = (dest / member.name).resolve()
        if member_path != dest_resolved and dest_resolved not in member_path.parents:
            print(f"error: refusing to extract unsafe path: {member.name}", file=sys.stderr)
            sys.exit(1)
        if member.issym() or member.islnk():
            link_target = ((dest / member.name).parent / member.linkname).resolve()
            if link_target != dest_resolved and dest_resolved not in link_target.parents:
                print(f"error: refusing to extract unsafe link: {member.name}", file=sys.stderr)
                sys.exit(1)
    tf.extractall(dest)  # noqa: S202 — members already validated above


def _extract_tar(tar_path: Path, dest: Path) -> None:
    if not tar_path.is_file():
        print(f"error: tar file not found: {tar_path}", file=sys.stderr)
        sys.exit(1)
    dest.mkdir(parents=True, exist_ok=True)  # the release tarball is packed with `tar -C md .`
    with tarfile.open(tar_path, "r:*") as tf:
        try:
            tf.extractall(dest, filter="data")  # noqa: S202 — "data" filter blocks traversal
        except TypeError:
            _safe_extractall(tf, dest)


def cmd_corpus(args: argparse.Namespace) -> None:
    MD_ROOT.mkdir(parents=True, exist_ok=True)
    if args.tar:
        _extract_tar(Path(args.tar), MD_ROOT)
        print(f"corpus extracted from {args.tar} -> {MD_ROOT}")
        sys.exit(0)

    jobs = args.jobs or os.cpu_count() or 4
    cmd = [
        sys.executable,
        str(REPO_ROOT / "src" / "ganjoor2md.py"),
        "--input", str(REPO_ROOT),
        "--output", str(MD_ROOT),
        "--jobs", str(jobs),
    ]
    if args.poets:
        cmd += ["--poets", args.poets]
    if args.force:
        cmd.append("--force")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    sys.exit(result.returncode)


# --------------------------------------------------------------------------
# index
# --------------------------------------------------------------------------


def cmd_index(args: argparse.Namespace) -> None:
    qmd_path = require_qmd()
    result = run_qmd(qmd_path, ["update"])
    sys.exit(result.returncode)


# --------------------------------------------------------------------------
# embed
# --------------------------------------------------------------------------


def cmd_embed(args: argparse.Namespace) -> None:
    qmd_path = require_qmd()
    collections = args.collections or list(SUMMARY_COLLECTIONS)

    bad = [c for c in collections if c not in SUMMARY_COLLECTIONS]
    if bad:
        print(
            f"error: refusing to embed {', '.join(bad)} — only "
            f"{', '.join(SUMMARY_COLLECTIONS)} may be embedded.",
            file=sys.stderr,
        )
        print(
            "The `ganjoor` collection (135k full poems) is BM25-only by design; "
            "embedding it wastes hours for nothing.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.collections:
        print(
            "note: no -c given — embedding both summary collections "
            f"({', '.join(SUMMARY_COLLECTIONS)}).",
            file=sys.stderr,
        )
        print(
            "      A bare `qmd embed` would embed EVERY collection, including `ganjoor` "
            "(135k full poems, BM25-only by design) — ganjoor.py never does that.",
            file=sys.stderr,
        )

    rc = 0
    for coll in collections:
        result = run_qmd(qmd_path, ["embed", "-c", coll])
        rc = rc or result.returncode
    sys.exit(rc)


# --------------------------------------------------------------------------
# search (qmd BM25, with a pure-Python --offline fallback)
# --------------------------------------------------------------------------


def _extract_frontmatter_field(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip('"') if m else None


# Punctuation-insensitive comparison key, layered ON TOP of
# normalize_search_text (never reimplementing it) — a query typed without the
# Persian comma／other punctuation the source couplet happens to carry should
# still match.
_PUNCT_RE = re.compile(r"[،؛؟,.!:;\"'«»()\[\]{}]")


def _fuzzy_key(normalized_text: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT_RE.sub(" ", normalized_text)).strip()


def _search_offline(args: argparse.Namespace) -> None:
    """Pure-Python exact-line search over md/poets/**/*.md — no Node, no
    qmd, no models. Reuses normalize_search_text from src/ganjoor2md.py so
    matching stays consistent with how the corpus was generated."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        from ganjoor2md import normalize_search_text  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(
            f"error: could not import normalize_search_text from src/ganjoor2md.py: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    poets_root = MD_ROOT / "poets"
    if not poets_root.is_dir():
        print(f"error: {poets_root} not found — run `ganjoor.py corpus` first.", file=sys.stderr)
        sys.exit(1)

    query_norm = normalize_search_text(args.query)
    if not query_norm:
        print("error: empty query.", file=sys.stderr)
        sys.exit(1)
    query_key = _fuzzy_key(query_norm)

    limit = args.n
    hits = 0
    scanned = 0
    print(f"[offline] scanning {poets_root} (no qmd/Node/models used) ...", file=sys.stderr)
    for path in sorted(poets_root.rglob("*.md")):
        scanned += 1
        if scanned % 20000 == 0:
            print(f"[offline] scanned {scanned} files, {hits} hit(s) so far ...", file=sys.stderr)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        norm = normalize_search_text(text)
        if query_norm not in norm and query_key not in _fuzzy_key(norm):
            continue

        title = _extract_frontmatter_field(text, "full_title") or path.stem
        matching_lines = [
            line
            for line in text.splitlines()
            if line.strip()
            and (
                query_norm in normalize_search_text(line)
                or query_key in _fuzzy_key(normalize_search_text(line))
            )
        ]
        print(f"\n{title}")
        for line in matching_lines[:6]:
            print(f"  {line.strip()}")
        print(f"  ({path.relative_to(REPO_ROOT)})")
        hits += 1
        if hits >= limit:
            break

    print(f"\n[offline] scanned {scanned} files, {hits} hit(s).", file=sys.stderr)
    sys.exit(0 if hits else 1)


def cmd_search(args: argparse.Namespace) -> None:
    if args.offline:
        _search_offline(args)
        return

    qmd_path = find_qmd()
    if not qmd_path:
        print(
            "qmd not found on PATH — falling back to offline exact-line search "
            "(install qmd for BM25/semantic search: npm install -g @tobilu/qmd).",
            file=sys.stderr,
        )
        _search_offline(args)
        return

    cmd = ["search", args.query, "-n", str(args.n)]
    if args.collection:
        cmd += ["-c", args.collection]
    result = run_qmd(qmd_path, cmd)
    sys.exit(result.returncode)


# --------------------------------------------------------------------------
# query (qmd hybrid/semantic search)
# --------------------------------------------------------------------------


def _looks_like_semantic_failure(text: str) -> bool:
    return any(marker in text for marker in _SEMANTIC_FAILURE_MARKERS)


def _explain_semantic_failure(text: str) -> str | None:
    for marker in _SEMANTIC_FAILURE_MARKERS:
        if marker in text:
            for line in text.splitlines():
                if marker in line:
                    return line.strip()
    return None


def cmd_query(args: argparse.Namespace) -> None:
    qmd_path = require_qmd()
    cmd = ["query", args.query, "-n", str(args.n)]
    if args.collection:
        cmd += ["-c", args.collection]
    result = run_qmd(qmd_path, cmd, capture_output=True, text=True)
    combined = (result.stdout or "") + (result.stderr or "")

    if result.returncode != 0 or _looks_like_semantic_failure(combined):
        print("Semantic search is unavailable in this environment.", file=sys.stderr)
        reason = _explain_semantic_failure(combined) or "the `qmd query` command failed"
        print(f"  reason: {reason}", file=sys.stderr)
        print(
            "  qmd needs to download embedding/expansion models from huggingface.co the "
            "first time; if that host is blocked here, semantic search cannot work.",
            file=sys.stderr,
        )
        print(f'  try instead:  ganjoor.py search "{args.query}" -c ganjoor       (exact BM25)', file=sys.stderr)
        print(f'            or:  ganjoor.py search "{args.query}" --offline      (no qmd/Node needed)', file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    sys.exit(0)


# --------------------------------------------------------------------------
# mcp
# --------------------------------------------------------------------------


def cmd_mcp(args: argparse.Namespace) -> None:
    qmd_path = require_qmd()

    if args.stop:
        result = run_qmd(qmd_path, ["mcp", "stop", "--port", str(args.port)])
        sys.exit(result.returncode)

    if args.http:
        cmd = ["mcp", "--http", "--port", str(args.port)]
        if args.daemon:
            cmd.append("--daemon")
        result = run_qmd(qmd_path, cmd)
        sys.exit(result.returncode)

    if args.daemon:
        print("error: --daemon requires --http (stdio cannot be daemonized).", file=sys.stderr)
        sys.exit(2)

    # Default: stdio transport, foreground — what Claude Code/Codex/Hermes use.
    result = run_qmd(qmd_path, ["mcp"])
    sys.exit(result.returncode)


# --------------------------------------------------------------------------
# demo
# --------------------------------------------------------------------------


def cmd_demo(args: argparse.Namespace) -> None:
    demo_script = REPO_ROOT / "scripts" / "web-demo.py"
    if not demo_script.is_file():
        print(f"error: {demo_script} not found.", file=sys.stderr)
        sys.exit(1)
    env = dict(os.environ)
    env["WEB_DEMO_PORT"] = str(args.port)
    env["QMD_TRUST_LOCAL_CONFIG"] = "1"
    result = subprocess.run([sys.executable, str(demo_script)], cwd=REPO_ROOT, env=env)
    sys.exit(result.returncode)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ganjoor.py",
        description="Ganjoor corpus pipeline — single cross-platform entrypoint.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="Report what works in this environment.")
    p.add_argument("--strict", action="store_true", help="exit non-zero if nothing works")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("setup", help="Install qmd (via npm) and check Python.")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("corpus", help="Build md/ from Ganjoor JSON, or extract a release tarball.")
    p.add_argument("--poets", default="", help="comma-separated poet slugs (default: all)")
    p.add_argument("--tar", default=None, help="extract this tarball into md/ instead of converting")
    p.add_argument("--jobs", type=int, default=0, help="worker processes (default: CPU count)")
    p.add_argument("--force", action="store_true", help="reconvert even if output exists")
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser("index", help="Build/refresh the QMD index (BM25 + metadata).")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("embed", help="Generate vectors for the summary collections (ganjoor-fa/-en).")
    p.add_argument(
        "-c", "--collection", dest="collections", action="append",
        choices=list(SUMMARY_COLLECTIONS),
        help="restrict to one collection (repeatable); default: both summary collections",
    )
    p.set_defaults(func=cmd_embed)

    p = sub.add_parser("search", help="Exact BM25 search (qmd); --offline needs no qmd/Node/models.")
    p.add_argument("query")
    p.add_argument("-c", "--collection", default="ganjoor")
    p.add_argument("-n", type=int, default=5)
    p.add_argument("--offline", action="store_true", help="pure-Python exact search, no qmd/Node/models")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("query", help="Semantic/hybrid search (qmd query); needs reachable embedding models.")
    p.add_argument("query")
    p.add_argument("-c", "--collection", default="ganjoor-fa")
    p.add_argument("-n", type=int, default=5)
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("mcp", help="Run the MCP server (stdio by default; --http for HTTP).")
    p.add_argument("--http", action="store_true", help="run the HTTP transport instead of stdio")
    p.add_argument("--port", type=int, default=8191)
    p.add_argument("--stop", action="store_true", help="stop the HTTP daemon on --port")
    p.add_argument("--daemon", action="store_true", help="with --http, run as a background daemon")
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser("demo", help="Run the local web search demo.")
    p.add_argument("--port", type=int, default=8090)
    p.set_defaults(func=cmd_demo)

    return parser


def main(argv: list | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
