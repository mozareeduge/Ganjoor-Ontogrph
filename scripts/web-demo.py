#!/usr/bin/env python3
"""web-demo — a tiny, self-contained search page for the Ganjoor poetry corpus.

For non-technical users: run `python3 scripts/web-demo.py`, open
http://localhost:8090, type a line or a theme (Persian or English), and read
poems. No installs beyond Python 3.

Routing (automatic):
  - Persian text → exact-line search on the full poems first; if nothing
    strong, falls back to semantic search on the Persian summaries.
  - English text → semantic search on the English summaries.
"""
import html
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("WEB_DEMO_PORT", "8090"))
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
  out.innerHTML = 'در حال جستجو…';
  const r = await fetch('/api/search?q=' + encodeURIComponent(q));
  const data = await r.json();
  if (data.error) { out.innerHTML = '<div class="err">' + data.error + '</div>'; return; }
  if (!data.results.length) { out.innerHTML = '<div class="err">چیزی پیدا نشد — عبارت دیگری را امتحان کنید.</div>'; return; }
  out.innerHTML = data.results.map(res => `
    <div class="result">
      <div class="poem">${res.poem || ''}</div>
      <div class="meta">${res.title || ''} — <span class="score">${res.score}٪</span><br>${res.url || ''}</div>
    </div>`).join('');
}
document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
</script>
</body>
</html>
"""

HAS_PERSIAN = re.compile(r"[\u0600-\u06FF]")


def run_qmd(args):
    try:
        out = subprocess.run(["qmd"] + args, capture_output=True, text=True, env=ENV, cwd=ROOT, timeout=120)
        return out.stdout
    except Exception:
        return ""


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
    for m in re.finditer(r"qmd://([^\s#]+\.md)[^\n]*\nScore:\s+(\d+)%", out):
        rel = m.group(1)
        score = int(m.group(2))
        rel = rel.replace(f"{coll}/", "", 1) if rel.startswith(f"{coll}/") else rel
        md_path = Path("md") / coll / rel
        if coll in ("ganjoor-fa", "ganjoor-en"):
            # follow the poem: pointer
            try:
                card = (ROOT / md_path).read_text(encoding="utf-8")
                pm = re.search(r"^poem:\s*(.+)$", card, re.M)
                if pm:
                    md_path = (ROOT / md_path).parent / pm.group(1).strip()
                else:
                    continue
            except OSError:
                continue
        hits.append({
            "title": title_of(md_path),
            "score": score,
            "poem": first_couplets(md_path),
            "url": "",
        })
        if len(hits) >= limit:
            break
    return hits


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/search"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query).get("q", [""])[0].strip()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if not q:
                self.wfile.write(json.dumps({"results": []}).encode())
                return
            if HAS_PERSIAN.search(q):
                out = run_qmd(["search", q, "-c", "ganjoor", "-n", "6"])
                results = parse_hits(out, "ganjoor")
                if not results:
                    out = run_qmd(["query", q, "-c", "ganjoor-fa", "-n", "6"])
                    results = parse_hits(out, "ganjoor-fa")
            else:
                out = run_qmd(["query", q, "-c", "ganjoor-en", "-n", "6"])
                results = parse_hits(out, "ganjoor-en")
            self.wfile.write(json.dumps({"results": results}, ensure_ascii=False).encode())
            return
        if self.path in ("/", "/index.html"):
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
    print(f"گنجور search demo → http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
