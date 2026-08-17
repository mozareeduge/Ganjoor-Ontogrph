# persian-poetry-ai-agent-plugin

[**English**](README.md) | **فارسی**

**شعر فارسی، آماده برای agent های هوش مصنوعی** — کلِ گنجینهٔ شعر فارسیِ
[گنجور](https://ganjoor.net/) (۲۳۴ شاعر، حدود ۱۳۲٬۵۰۰ شعر) را به یک دیتابیس
Markdown قابل جستجو تبدیل می‌کند؛ چندزبانه، آفلاین و آماده برای agent ها.

این پروژه یک fork از [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
است با یک pipeline اضافه: **JSON ← Markdown ← QMD index** (جستجوی معنایی
انگلیسی + جستجوی معنایی فارسی + جستجوی دقیق ابیات، همه روی دستگاه خودتان).

## دموی ویدیویی

*به agent هوش مصنوعی‌ات — به فارسی — می‌گویی دلت برای کسی که دوستش داری تنگ شده. او در میان هفتصد سال شعر فارسی می‌گردد و با همان شعری که به حالِ تو می‌خورد جواب می‌دهد.*

[![تماشای دمو — یک گفت‌وگوی واقعی با MCP server](docs/assets/demo-poster.jpg)](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)

**[▶ تماشای ویدیوی دمو](https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin/releases/download/v0.1.1/demo.mp4)** — یک گفت‌وگوی واقعی با MCP server: یک پیام فارسی دربارهٔ دوری از یار ← جستجوی معنایی در میان حدود ۱۳۲٬۵۰۰ شعر ← [فخرالدین عراقی، غزل ۱۰۶](https://ganjoor.net/eraghi/divane/ghazale/sh106). ‏۳۰ ثانیه. تماماً فارسی، تماماً محلی.

## چرا؟

جستجوی معنایی در شعر کلاسیک فارسی همیشه سخت بوده. داده‌های گنجور به صورت JSON
خام با خلاصهٔ فارسی می‌آید و جستجوی ساده هم جواب نمی‌دهد. این پروژه:

1. هر شعر را به یک فایل Markdown تمیز تبدیل می‌کند — با YAML frontmatter
   (وزن، قافیه، قالب، منبع، لینک به گنجور)، متن اعراب‌دار، بخش «متن ساده» و
   خلاصهٔ فارسی
2. هر شعر را با یک **خلاصهٔ معنایی انگلیسی** و کلیدواژه غنی می‌کند (هر API
   سازگار با OpenAI — قابل تعویض). یعنی retrieval به انگلیسی کار می‌کند ولی
   خود شعر فارسی می‌ماند
3. یک **QMD index پروژه‌محلی** (`.qmd/index.yml`) با مدل چندزبانه
   Qwen3-Embedding-0.6B می‌دهد — هم فارسی، هم انگلیسی، هم semantic و هم exact
4. کاملاً ایزوله است: index این پروژه هیچ‌وقت با QMD سراسری دستگاه شما
   قاطی نمی‌شود

## شروع سریع

پیکره به صورت **GitHub Release artifact** توزیع می‌شود (فقط فایل‌های Markdown —
ایندکس برداری را خودتان روی دستگاهتان build می‌کنید).

```bash
# پیش‌نیازها: Python 3.10+ و QMD 2.5+
npm install -g @tobilu/qmd

# ۱. کلون کردن
git clone https://github.com/erfanbashar1/persian-poetry-ai-agent-plugin.git
cd persian-poetry-ai-agent-plugin

# ۲. گرفتن پیکره — از صفحهٔ Releases فایل ganjoor-md-v*.tar.gz را بگیرید و:
tar -xzf ganjoor-md-v0.1.0.tar.gz -C md
#    یا build از روی دادهٔ داخل مخزن:  python3 src/ganjoor2md.py --input . --output md

# ۳. ساخت index محلی (پروژه‌محلی و ایزوله)
export QMD_TRUST_LOCAL_CONFIG=1
qmd update
qmd embed -c ganjoor-fa      # برداریِ جستجوی معنایی فارسی (فقط خلاصه‌ها، طبق طراحی)
qmd embed -c ganjoor-en      # برداریِ جستجوی معنایی انگلیسی (از v0.2 که خلاصه‌ها بیاید)

# ۴. جستجو — دقیق فارسی، معنایی فارسی، معنایی انگلیسی
qmd search "که عشق آسان نمود اول ولی افتاد مشکل ها" -c ganjoor
qmd query "شعرهایی درباره غم و گذر عمر" -c ganjoor-fa
qmd query "poems about the pain of separation at night" -c ganjoor-en

# ۵. در دسترس قرار دادن برای agent ها از طریق MCP
./scripts/mcp-server.sh --daemon   # http://localhost:8191/mcp
```

ترجیح می‌دهید با `make`؟ [Makefile](Makefile) همان مراحل را شفاف اجرا می‌کند:
`make setup`، `make corpus`، `make index`، `make embed`، `make all`، `make search`،
`make mcp`.

راهنمای گام‌به‌گام کامل و playbook مخصوص agent ها در [AGENTS.md](AGENTS.md) است.
اگر agent شما با MCP کار می‌کند، [مهارت persian-poetry-mcp](skills/persian-poetry-mcp/SKILL.md)
را هم دارد — همانجا query ها و pattern های تست‌شده نوشته شده.

## معماری

```
دادهٔ JSON گنجور (poets/, index/)             ← بالادست، فقط‌خواندنی
        │  src/ganjoor2md.py (مبدل)
        ▼
md/poets/<slug>/…            → collection "ganjoor"     → جستجوی دقیق فارسی (BM25، بدون بردار)
md/summaries-fa/<slug>/…     → collection "ganjoor-fa"  → جستجوی معنایی فارسی (فقط خلاصه)
md/summaries-en/<slug>/…     → collection "ganjoor-en"  → جستجوی معنایی انگلیسی + BM25
        │  .qmd/index.yml (پروژه‌محلی، همراه مخزن)
        ▼
qmd query/search (ایزوله، Qwen3-Embedding چندزبانه)
```

تقسیم سه‌collection عمدی است: embedding ها **فقط روی خلاصه‌ها** می‌روند (هر زبان
خلاصهٔ خودش)، شعرهای کامل در یک collection واژگانی بدون بردار برای جستجوی دقیق
ابیات می‌مانند، و هر فایل خلاصه یک pointer به نام `poem:` دارد که به شعر واقعی
فارسی برمی‌گردد.

## وضعیت

- ✅ داده تأیید شد (۲۳۴ شاعر، ~۱۳۲٬۵۳۸ شعر، ۲٫۳ گیگابایت)
- ✅ کل پیکره تبدیل شد (۰ خطا)؛ جستجوی معنایی و دقیق فارسی فعال است
- ✅ **نسخهٔ v0.1.0 منتشر شد** — artifact پیکره `ganjoor-md-v0.1.0.tar.gz`
  (کاملِ فارسی: شعرها + زندگینامه‌ها + دسته‌ها + خلاصه‌های فارسی)
- ✅ MCP server، مهارت persian-poetry-mcp و Makefile آماده است
- ⏳ خلاصه‌های انگلیسی در حال تولید است (رایگان، حدود ۲ هفته) → **v0.2.0** که
  `summaries-en` هم به artifact اضافه می‌شود
- ⏳ بنیان‌گذار گنجور خودش پیشنهاد داده پروژه را معرفی کند؛ ارائهٔ ساده برای
  کاربران غیرفنی در راه است

## منبع و مجوز

جزئیات در [NOTICE.md](NOTICE.md). شعر کلاسیک فارسی مالکیت عمومی است؛ گردآوری و
خلاصه‌های هوش مصنوعی متعلق به پروژهٔ گنجور است. کد ما MIT است و خلاصه‌های
انگلیسی تولیدی‌مان هم MIT. بالادست (ganjoor-data) مجوزی اعلام نکرده — به منبع
احترام بگذارید. و از [گنجور](https://ganjoor.net) بابت این گنجینه سپاسگزار
باشید.
