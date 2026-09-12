#!/usr/bin/env python3
"""web-demo — a tiny, self-contained search page for the Ganjoor poetry corpus.

For non-technical users: run `python3 scripts/web-demo.py`, open
http://localhost:8090, type a line or a theme (Persian or English), and read
poems. No installs beyond Python 3.

Routing (automatic):
  - Persian text → exact-line search on the full poems first; if nothing
    strong, falls back to semantic search on the Persian summaries.
  - English text → semantic search on the English summaries.

Failure handling: every search distinguishes three states — results, a
genuine "nothing matched", and an engine failure (qmd missing, the index
absent, or a model download blocked/offline). The UI never shows an engine
failure as "no results" — it explains the cause in Persian and what to do.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Force UTF-8 on stdout/stderr so Persian progress/startup text can never
# crash on a Windows console whose codepage is cp1252 (UnicodeEncodeError).
# reconfigure() is Python 3.7+; guard anyway in case stdout is replaced by
# something that lacks it (e.g. some IDE/CI wrappers).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("WEB_DEMO_PORT", "8090"))
HOST = os.environ.get("WEB_DEMO_HOST", "127.0.0.1")
ENV = dict(os.environ, QMD_TRUST_LOCAL_CONFIG="1")

PAGE = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>گنجور — جستجوی شعر</title>
<style>
 body { font-family: Vazirmatn, "Segoe UI", Tahoma, sans-serif; background:#faf7f2; color:#2d2a26; margin:0; padding:0; }
 .wrap { max-width:760px; margin:0 auto; padding:40px 20px; }
 h1 { font-size:28px; margin:0 0 6px; }
 .sub { color:#8a857d; margin:0 0 24px; font-size:14px; }
 input[type=text] { width:100%; box-sizing:border-box; font-size:18px; padding:14px 16px; border:1px solid #d8d2c8; border-radius:10px; background:#fff; }
 button { margin-top:12px; font-size:16px; padding:10px 28px; border:0; border-radius:10px; background:#b23b2e; color:#fff; cursor:pointer; }
 .hint { color:#8a857d; font-size:13px; margin-top:8px; }
 .result { background:#fff; border:1px solid #e5e0d6; border-radius:12px; padding:18px 20px; margin-top:16px; }
 .poem { white-space:pre-line; line-height:2.1; font-size:17px; }
 .meta { color:#8a857d; font-size:13px; margin-top:10px; border-top:1px dashed #e5e0d6; padding-top:8px; }
 .score { color:#b23b2e; font-weight:bold; }
 .err { color:#b23b2e; margin-top:12px; }
 .notice { color:#8a5a1e; background:#fff6e8; border:1px solid #f0dcb0; border-radius:10px; padding:12px 16px; margin-top:12px; line-height:1.9; }
</style>
</head>
<body>
<div class="wrap">
 <h1>جستجوی شعر فارسی</h1>
 <p class="sub">بر پایهٔ داده‌های <a href="https://ganjoor.net">گنجور</a> — یک مصرع یا یک مضمون را بنویسید</p>
 <input type="text" id="q" placeholder="مثلاً: یوسف گم گشته بازآید به کنعان، غم مخور  یا  شعرهایی دربارهٔ دلتنگی و شب" autofocus>
 <button onclick="go()">جستجو</button>
 <div class="hint" id="hint">متن فارسی → جستجوی دقیق ابیات؛ مضمون فارسی یا انگلیسی → جستجوی معنایی</div>
 <div id="out"></div>
</div>
<script>
async function go() {
  const q = document.getElementById('q').value.trim();
  const out = document.getElementById('out');
  if (!q) return;
  const url = new URL(location.href);
  url.searchParams.set('q', q);
  history.replaceState(null, '', url);
  out.innerHTML = 'در حال جستجو…';
  let data;
  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    data = await r.json();
  } catch (e) {
    out.innerHTML = '<div class="err">ارتباط با سرور جستجو برقرار نشد. صفحه را دوباره بار کنید.</div>';
    return;
  }
  if (data.state === 'unavailable') {
    out.innerHTML = '<div class="notice">' + data.message + '</div>';
    return;
  }
  if (data.state !== 'results' || !data.results || !data.results.length) {
    out.innerHTML = '<div class="err">چیزی پیدا نشد — عبارت دیگری را امتحان کنید.</div>';
    return;
  }
  out.innerHTML = data.results.map(res => `
    <div class="result">
      <div class="poem">${res.poem || ''}</div>
      <div class="meta">${res.title || ''} — <span class="score">${res.score}٪</span><br>${res.url || ''}</div>
    </div>`).join('');
}
document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
// A shared/bookmarked link like /?q=... should search immediately on load.
(function () {
  const q = new URL(location.href).searchParams.get('q');
  if (q) {
    document.getElementById('q').value = q;
    go();
  }
})();
</script>
</body>
</html>
"""

HAS_PERSIAN = re.compile(r"[\u0600-\u06FF]")

# QMD collection name → directory under md/
COLL_DIR = {"ganjoor": "poets", "ganjoor-fa": "summaries-fa", "ganjoor-en": "summaries-en"}
EN_SUMMARIES_DIR = ROOT / "md" / "summaries-en"

MSG_EN_UNAVAILABLE = (
    "جستجوی انگلیسی هنوز فعال نیست: خلاصه‌های انگلیسی شعرها (English summaries) در این نسخه هنوز "
    "ساخته نشده‌اند و در نسخهٔ ۰.۲ اضافه می‌شوند. این «هیچ چیزی پیدا نشد» نیست — این بخش هنوز خالی است. "
    "برای جستجو، یک مصرع یا یک موضوع فارسی را امتحان کنید."
)


class QmdError(Exception):
    """qmd could not be run, or ran and failed. Carries enough to explain why."""

    def __init__(self, kind, detail=""):
        super().__init__(detail)
        self.kind = kind  # "not_found" | "timeout" | "failed"
        self.detail = detail


def find_qmd():
    """Resolve the qmd executable. On Windows an npm-global install is a
    qmd.cmd shim, so a bare "qmd" is not directly executable by subprocess."""
    for name in ("qmd", "qmd.cmd", "qmd.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def run_qmd(args):
    """Run qmd and return stdout. Raises QmdError on any failure — never swallows it."""
    qmd_path = find_qmd()
    if qmd_path is None:
        raise QmdError("not_found", "qmd was not found on PATH")
    try:
        # encoding is explicit: qmd emits UTF-8, but text=True would otherwise
        # decode with the locale codec (cp1252 on Windows) and mangle or crash
        # on Persian output.
        out = subprocess.run(
            [qmd_path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=ENV,
            cwd=ROOT,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise QmdError("not_found", str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise QmdError("timeout", str(exc)) from exc
    if out.returncode != 0:
        raise QmdError("failed", (out.stderr or out.stdout or "").strip())
    return out.stdout


def engine_failure_message(exc, semantic_only):
    """Plain-language Persian explanation of a QmdError, with what to do."""
    if exc.kind == "not_found":
        return (
            "ابزار جستجو «qmd» روی این سیستم پیدا نشد یا در PATH نیست — این یک خطای فنی است، نه نبود نتیجه. "
            "نصب qmd را طبق AGENTS.md بررسی کنید."
        )
    if exc.kind == "timeout":
        return "موتور جستجو در زمان مناسب پاسخ نداد (timeout). دوباره تلاش کنید."

    detail = (exc.detail or "").strip()
    dl = detail.lower()
    model_blocked = (
        "huggingface.co" in dl
        or "statuscodeerror" in dl
        or ("model" in dl and ("403" in dl or "forbidden" in dl))
    )
    network_issue = any(tok in dl for tok in ("enotfound", "econnrefused", "etimedout"))
    if model_blocked or network_issue:
        cause = (
            "دانلود مدل هوش مصنوعی لازم برای جستجوی معنایی از huggingface.co مسدود شده (خطای HTTP 403 Forbidden)"
            if model_blocked
            else "اتصال شبکه برای دانلود مدل هوش مصنوعی برقرار نشد"
        )
        if semantic_only:
            return (
                f"جستجوی معنایی در این محیط ممکن نیست: {cause}. این خطای فنی است، نه نبود نتیجه — "
                "جستجوی خطی دقیق (BM25) همچنان فعال است؛ عین یک مصرع از شعر را وارد کنید."
            )
        return f"موتور جستجو در این محیط اجرا نشد: {cause}. این خطای فنی است، نه نبود نتیجه."

    short = detail.splitlines()[-1][:200] if detail else "بدون جزئیات بیشتر"
    scope = "جستجوی معنایی" if semantic_only else "موتور جستجو (qmd)"
    return f"{scope} با خطای فنی متوقف شد — این «هیچ چیزی پیدا نشد» نیست. جزئیات: {html.escape(short)}"


def has_any_md(dir_path):
    if not dir_path.is_dir():
        return False
    return next(dir_path.rglob("*.md"), None) is not None


def first_couplets(md_path, n=4):
    try:
        text = (ROOT / md_path).read_text(encoding="utf-8")
    except OSError:
        return ""
    body = text.split("---", 2)[-1]
    body = re.split(r"\n## ", body, maxsplit=1)[0]
    lines = [l for l in body.splitlines() if l.strip()]
    return "\n".join(lines[: n * 2])


def title_of(md_path):
    try:
        text = (ROOT / md_path).read_text(encoding="utf-8")
        m = re.search(r"^full_title:\s*(.+)$", text, re.M)
        return m.group(1).strip() if m else ""
    except OSError:
        return ""


def parse_hits(out, coll, limit=5):
    hits = []
    cur = None
    for line in out.splitlines():
        m = re.search(r"qmd://([^\s#]+\.md)", line)
        if m:
            cur = m.group(1)
            continue
        s = re.search(r"Score:\s+(\d+)%", line)
        if not (s and cur):
            continue
        rel = cur.replace(f"{coll}/", "", 1) if cur.startswith(f"{coll}/") else cur
        md_path = Path("md") / COLL_DIR.get(coll, coll) / rel
        if coll in ("ganjoor-fa", "ganjoor-en"):
            # follow the poem: pointer
            try:
                card = (ROOT / md_path).read_text(encoding="utf-8")
                pm = re.search(r"^poem:\s*(.+)$", card, re.M)
                if pm:
                    md_path = (ROOT / md_path).parent / pm.group(1).strip()
                else:
                    cur = None
                    continue
            except OSError:
                cur = None
                continue
        hits.append({
            "title": title_of(md_path),
            "score": int(s.group(1)),
            "poem": first_couplets(md_path),
            "url": "",
        })
        cur = None
        if len(hits) >= limit:
            break
    return hits


def search_persian(q):
    """Exact-line BM25 first; semantic fallback on Persian summaries second."""
    try:
        out = run_qmd(["search", q, "-c", "ganjoor", "-n", "6"])
    except QmdError as exc:
        return {"state": "unavailable", "message": engine_failure_message(exc, semantic_only=False)}

    results = parse_hits(out, "ganjoor")
    if results:
        return {"state": "results", "results": results}

    # No exact line matched — try semantic search on the Persian summaries.
    try:
        out = run_qmd(["query", q, "-c", "ganjoor-fa", "-n", "6"])
    except QmdError as exc:
        return {"state": "unavailable", "message": engine_failure_message(exc, semantic_only=True)}

    results = parse_hits(out, "ganjoor-fa")
    if results:
        return {"state": "results", "results": results}
    return {"state": "no_match"}


def search_english(q):
    """Semantic search on English summaries — a v0.2 feature, empty in a fresh install."""
    if not has_any_md(EN_SUMMARIES_DIR):
        return {"state": "unavailable", "message": MSG_EN_UNAVAILABLE}

    try:
        out = run_qmd(["query", q, "-c", "ganjoor-en", "-n", "6"])
    except QmdError as exc:
        return {"state": "unavailable", "message": engine_failure_message(exc, semantic_only=True)}

    results = parse_hits(out, "ganjoor-en")
    if results:
        return {"state": "results", "results": results}
    return {"state": "no_match"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/search":
            q = parse_qs(parsed.query).get("q", [""])[0].strip()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if not q:
                self.wfile.write(json.dumps({"state": "no_match", "results": []}).encode())
                return
            result = search_persian(q) if HAS_PERSIAN.search(q) else search_english(q)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
            return

        # Serve the page for the root path regardless of query string
        # (a shared link like /?q=... must not 404).
        if path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"گنجور search demo → http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
