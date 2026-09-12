# Ganjoor-Ontograph

[**English**](README.md) | **فارسی**

**شعر فارسی، آماده برای agent های هوش مصنوعی — و یک ابزار پژوهشی در حال شکل‌گیری.**
کلِ گنجینهٔ شعر فارسیِ [گنجور](https://ganjoor.net/) — ۲۳۴ شاعر، ۱۳۲٬۵۳۸ شعر،
۲٬۲۶۱ دسته — را به یک دیتابیس Markdown قابل جستجو تبدیل می‌کند؛ چندزبانه،
آفلاین و در دسترس agent ها از طریق MCP.

**این پروژه بر کار دیگران ایستاده است.** خودِ گنجینهٔ داده را پروژهٔ
[گنجور](https://ganjoor.net/) در [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
منتشر می‌کند. لایه‌ای که این داده را برای agent ها قابل استفاده کرده — pipeline
تبدیل JSON به Markdown، طراحی enrichment، معماری سه‌collection ای جستجو با QMD،
و یکپارچگی با MCP — ساختهٔ **[عرفان بشر](https://github.com/erfanbashar1)** در
[erfanbashar1/persian-poetry-ai-agent-plugin](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin)
است و اینجا زیر مجوز MIT همان پروژه به کار رفته است.

**Ganjoor-Ontograph** (همین مخزن) یک fork از آن پروژه است که
[mozare](https://github.com/mozareeduge) نگه‌داری‌اش می‌کند. آنچه تا امروز
افزوده شده: قابلیت اجرا روی harness ها و سیستم‌عامل‌های مختلف، یک مسیر جستجوی
آفلاین برای محیط‌هایی که امکان دانلود model ندارند، و مجموعه‌سندهای حاکمیت و
تحویل پروژه. هدف بلندمدتش — که هنوز ساخته نشده — یک لایهٔ ontology/graph روی این
گنجینه است؛ یک ابزار پژوهشی، نه فقط یک موتور جستجو.

منبع و مجوز کامل: [NOTICE.md](NOTICE.md).

> **نکته دربارهٔ آدرس مخزن:** نام پروژه **Ganjoor-Ontograph** است، اما هم‌اکنون
> در `github.com/mozareeduge/Ganjoor-Ontogrph` میزبانی می‌شود (بدون حرف "a"ی
> دوم — تغییر نام برنامه‌ریزی شده، ببینید `ROADMAP.md` مورد GO-010، اما هنوز
> اتفاق نیفتاده). هر دستور clone و لینک در این فایل همان املایی را دارد که
> امروز واقعاً کار می‌کند.

## این پروژه برای چیست؟

آنچه امروز وجود دارد یک pipeline تبدیل + ایندکس + بازیابی است: خروجی JSON
گنجور به Markdown آماده برای agent تبدیل می‌شود، به‌صورت محلی قابل جستجوست
(جستجوی دقیق همیشه؛ جستجوی معنایی وقتی مدلی در دسترس باشد) و agent های هوش
مصنوعی از طریق MCP آن را query می‌کنند. اما هدف پروژه بزرگ‌تر از این است: یک
ابزار پژوهشی روی آرشیو کلاسیک فارسی — کاوش موضوعی بین شاعران، تحلیل ساختاری
روی بیش از ۱۳۲ هزار شعر، و در نهایت یک لایهٔ صریح ontology/graph روی شاعران،
شعرها، قالب‌ها، وزن‌ها و مضامین (همان "ontograph" در نام پروژه). **این لایه
هنوز ساخته نشده است.** برای چارچوب کامل [SPEC.md](SPEC.md) و برای وضعیت واقعیِ
در حال انجام [ROADMAP.md](ROADMAP.md) را ببینید.

## شروع سریع

```bash
# پیش‌نیاز: Python 3.10+. برای جستجوی آفلاین/دقیق همین کافی است.
# جستجوی معنایی علاوه‌بر آن به QMD 2.5+ (نسخهٔ ۲.۸.۳ تایید شده) و دسترسی
# شبکه به huggingface.co برای دانلود مدل embedding نیاز دارد.

git clone https://github.com/mozareeduge/Ganjoor-Ontogrph.git
cd Ganjoor-Ontogrph

# ۱. ببینید محیط شما واقعاً چه چیزی را می‌تواند اجرا کند — این را اول اجرا کنید
python3 scripts/ganjoor.py doctor

# ۲. گرفتن پیکرهٔ Markdown (این مخزن هنوز GitHub Release ندارد — ROADMAP مورد
#    GO-011 — پس آن را از JSON داخل مخزن بسازید):
python3 scripts/ganjoor.py corpus          # همهٔ ۲۳۴ شاعر، ~۶ دقیقه روی ۴ core
python3 scripts/ganjoor.py corpus --poets hafez,saadi,rumi   # یا فقط یک زیرمجموعه

# ۳. ایندکس کردن (سریع، بدون شبکه، بدون مدل)
python3 scripts/ganjoor.py index

# ۴. جستجو
python3 scripts/ganjoor.py search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
python3 scripts/ganjoor.py search "همای رحمت" --offline    # بدون qmd، بدون Node، بدون هیچ مدلی

# ۵. در دسترس قرار دادن برای agent ها از طریق MCP
python3 scripts/ganjoor.py mcp             # stdio، برای config های harness مثل .mcp.json
```

**جستجوی معنایی** (`embed`، `query`) باید یک مدل embedding را از
`huggingface.co` دانلود کند — که در محیط‌های sandbox/آفلاین (Claude Code
web/mobile، Codex cloud، دستگاه‌های بدون اینترنت) در دسترس نیست. این یک
محدودیت معماری است، نه یک باگ. در چنین محیط‌هایی به‌جای آن از جستجوی دقیق
(`search`، `search --offline`) استفاده کنید. `ganjoor-en` (معنایی انگلیسی)
هم تا زمانی که enrichment مربوط به v0.2 منتشر شود، خالی است.

`build.sh`، `mcp-server.sh` و `make setup|corpus|index|embed|all|search|mcp|demo`
همچنان کار می‌کنند — الان wrapper نازکی روی `scripts/ganjoor.py` هستند، برای
راحتی کسانی که با آن‌ها عادت کرده‌اند. برای فهرست کامل flag ها
`python3 scripts/ganjoor.py --help` و `<subcommand> --help` را اجرا کنید.

## استفاده از یک agent harness

هر agent سازگار با MCP می‌تواند به سرور `persian-poetry` (`.mcp.json`، از نوع
stdio) وصل شود. Claude Code آن را خودکار تشخیص می‌دهد؛ harness های دیگر
(Codex، Hermes، کلاینت‌های عمومی MCP) به یک config نیاز دارند — برای تنظیمات
دقیق و جدول قابلیت هر harness به **[docs/HARNESSES.md](docs/HARNESSES.md)**
مراجعه کنید. Claude Code همچنین playbook query را از
[`.claude/skills/persian-poetry/SKILL.md`](.claude/skills/persian-poetry/SKILL.md)
می‌گیرد. جزئیات عملیاتی کامل برای هر agent: [AGENTS.md](AGENTS.md).

## دموی ویدیویی

*به agent هوش مصنوعی‌ات — به فارسی — می‌گویی دلت برای کسی که دوستش داری تنگ شده. او در میان هفتصد سال شعر فارسی می‌گردد و با همان شعری که به حالِ تو می‌خورد جواب می‌دهد.*

[![تماشای دمو — یک گفت‌وگوی واقعی با MCP server](docs/assets/demo-poster.jpg)](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)

**[▶ تماشای ویدیوی دمو](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)** — یک گفت‌وگوی واقعی با MCP server: یک پیام فارسی دربارهٔ دوری از یار ← جستجوی معنایی در میان ۱۳۲٬۵۳۸ شعر ← [فخرالدین عراقی، غزل ۱۰۶](https://ganjoor.net/eraghi/divane/ghazale/sh106). ‏۳۰ ثانیه. تماماً فارسی، تماماً محلی.

*این ویدیو را پروژهٔ upstream ([erfanbashar1](https://github.com/erfanbashar1)) ضبط کرده و روی release خودش میزبانی می‌شود؛ اینجا فقط با ذکر منبع به آن link داده شده، بازنشر نشده است. این مخزن هنوز Release مستقلی ندارد — ببینید `ROADMAP.md` مورد GO-014.*

## معماری

```
دادهٔ JSON گنجور (poets/, index/)             ← بالادست، فقط‌خواندنی
        │  src/ganjoor2md.py (مبدل)
        ▼
md/poets/<slug>/…            → collection "ganjoor"     → جستجوی دقیق فارسی (BM25، بدون بردار)
md/summaries-fa/<slug>/…     → collection "ganjoor-fa"  → جستجوی معنایی فارسی (فقط خلاصه)
md/summaries-en/<slug>/…     → collection "ganjoor-en"  → جستجوی معنایی انگلیسی (تا v0.2 خالی)
        │  .qmd/index.yml (پروژه‌محلی، همراه مخزن)
        ▼
qmd / scripts/ganjoor.py (search، query، mcp)
```

embedding ها فقط روی دو collection خلاصه اجرا می‌شوند، طبق طراحی — شعرهای
کامل در یک collection واژگانی بدون بردار برای جستجوی دقیق ابیات می‌مانند، و
هر خلاصه یک pointer به نام `poem:` دارد که به متن واقعی فارسی برمی‌گردد.
چرایی این طراحی: [docs/DECISIONS.md](docs/DECISIONS.md).

## وضعیت

- داده تأیید شد: ۲۳۴ شاعر، **۱۳۲٬۵۳۸** شعر، ۲٬۲۶۱ دسته، ۰ خطا، ۲۶۳٬۶۰۳ فایل
  Markdown، حدود ۱٫۴ گیگابایت، ~۶ دقیقه ساخت روی ۴ core. (یک commit قدیمی‌تر
  عدد ۱۳۲٬۵۹۱ شعر را ادعا می‌کند — این ناهماهنگی در `CHANGELOG.md` ثبت شده؛
  عدد تایید‌شده همان ۱۳۲٬۵۳۸ است.)
- چندسکویی: یک entrypoint (`scripts/ganjoor.py`) روی Linux/macOS/Windows به
  یک شکل کار می‌کند (shim های `ganjoor.cmd`/`ganjoor.ps1`)، و روی هر سه در CI
  تست شده (`.github/workflows/ci.yml`).
- MCP server، مهارت Claude Code، اسناد multi-harness و دموی وب همه فعال‌اند؛
  دموی وب الان به‌جای گفتن «نتیجه‌ای نیست» خرابی موتور جستجو را صادقانه گزارش
  می‌کند.
- این مخزن هنوز GitHub Release ندارد (`ROADMAP.md` مورد GO-011) — فعلاً پیکره
  را محلی بسازید.
- خلاصه‌های معنایی انگلیسی (`ganjoor-en`) هنوز تولید نشده‌اند — v0.2
  (`ROADMAP.md` مورد GO-020).
- لایهٔ ontology/graph یک جهت اعلام‌شده است، نه چیزی ساخته‌شده — v0.3+
  (`ROADMAP.md`، exploratory).

فهرست کامل کارها: [ROADMAP.md](ROADMAP.md). چه چیزی چه زمانی منتشر شد:
[CHANGELOG.md](CHANGELOG.md).

## منبع و مجوز

جزئیات در [NOTICE.md](NOTICE.md). شعر کلاسیک فارسی مالکیت عمومی است؛ گردآوری و
خلاصه‌های هوش مصنوعی متعلق به پروژهٔ گنجور است. کد ما MIT است و خلاصه‌های
انگلیسی تولیدی‌مان هم MIT. بالادست (ganjoor-data) مجوزی اعلام نکرده — به منبع
احترام بگذارید. و از [گنجور](https://ganjoor.net) بابت این گنجینه سپاسگزار
باشید.
