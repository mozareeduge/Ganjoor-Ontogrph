#!/usr/bin/env python3
"""Generate the mini-ganjoor fixture corpus with known ground truth.

This is FABRICATED synthetic text, not real Ganjoor content — it exists
only to give the deterministic engine (spec Part IX) a corpus small enough
to reason about by hand and a "true distribution" fixed in advance (spec
Part XI §67: "crafted miniature corpora where the true distribution is
known"). Do not treat any line here as real Persian poetry.

Schema is a best-effort match to the real ganjoor-data JSON, verified
against a live poem at `poets/hafez/ghazal/sh1.json` in
erfanbashar1/persian-poetry-ai-agent-plugin on 2026-08-27 for the Poem/
Section/Verse fields. Poet.json and _cat.json fields beyond Id/Name/
Nickname/Description and Id/Title/Path/ChildCategories/Poems are NOT
independently verified against the real schema and should be treated as
plausible approximations only — do not build engine logic that depends on
an unverified field here without checking it against a real fixture first.

Run: python3 generate_fixture.py
Writes the poets/, index/, and manifest.json under this directory.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

MIRROR = "آینه"
MIRROR_VARIANT = "آیینه"
RUST = "زنگار"
HEART = "دل"  # second, larger-N fixture object (~40 hits) for the estimated-mode gate

def section(verses: list[tuple[str, str]], poem_format="Ghazal"):
    """verses: list of (right_hemistich, left_hemistich) per couplet.

    PlainText is DERIVED from the verses (a plain-text rendering of the
    same couplets), matching real Ganjoor semantics where the section's
    plain text is the same source text as the Verses array, not an
    independent paraphrase — see the fork's own skill docs on the «متن
    ساده» field. Any anchor census must therefore count each occurrence
    once at the verse level; counting PlainText and Verses separately
    would double-count every hit in this fixture (and, if unnoticed,
    would double-count in the real corpus too).
    """
    v = []
    order = 1
    plain_lines = []
    for ci, (right, left) in enumerate(verses):
        v.append({"VOrder": order, "Position": "Right", "Text": right,
                   "CoupletIndex": ci, "SectionIndex1": 0})
        order += 1
        v.append({"VOrder": order, "Position": "Left", "Text": left,
                   "CoupletIndex": ci, "SectionIndex1": 0})
        order += 1
        plain_lines.append(f"{right} / {left}")
    plain_text = "\n".join(plain_lines)
    sec = {
        "Index": 0, "Number": 1, "SectionType": "WholePoem", "VerseType": "First",
        "RhymeLetters": "ها", "PlainText": plain_text,
        "HtmlText": f"<div class='b'>{plain_text}</div>",
        "PoemFormat": poem_format, "CoupletsCount": len(verses),
    }
    return sec, v

def poem(poem_id, cat_id, title, verses, summary):
    sec, v = section(verses)
    return {
        "Id": poem_id, "CatId": cat_id, "Title": title,
        "FullTitle": title, "FullUrl": f"/fixture/{poem_id}",
        "RhymeLetters": "ها", "SourceName": "mini-ganjoor-fixture",
        "SourceUrlSlug": "fixture", "PoemSummary": summary,
        "Metre": {"Id": 1, "Rhythm": "فعولن فعولن فعولن فعل (fixture metre)"},
        "Sections": [sec], "Verses": v,
    }

POETS = {}
POEMS = {}

# --- Poet 1: two tight mirror-rust cases, one broad-only, one spelling
#     variant, one figurative/ambiguous case. This poet is the ablation
#     "dominant source" for the tight-scale relation. ---
POETS["sample1"] = {"Id": 9001, "Name": "شاعر آزمایشی یک", "Nickname": "آزمایشی۱",
                     "Description": "Fabricated fixture poet, not a real historical figure.",
                     "BirthYearInLHijri": 705, "DeathYearInLHijri": 780, "ValidBirthDate": True, "ValidDeathDate": True}

POEMS[9101] = poem(9101, 1, "غزل آزمایشی ۱-۱",
    [(f"{MIRROR} در دست من است امشب", f"{RUST} بر آن نشسته پنهان"),
     ("باد سحری وزید آرام", "بر رخ ما و بر رخ ایوان")],
    "Tight case: mirror and rust share the first couplet.")

POEMS[9102] = poem(9102, 1, "غزل آزمایشی ۱-۲",
    [(f"{MIRROR} به دیوار کهن آویزان", "روزی روشن نشان می‌داد"),
     ("سال‌ها بگذشت و خاموش شد", "دیگر پیدا نبود آن تابان"),
     ("در پستوی خانه چیزی بود", f"{RUST} به زیر زمین در انبان")],
    "Broad-only case: mirror and rust appear in the same poem but different couplets.")

POEMS[9103] = poem(9103, 1, "غزل آزمایشی ۱-۳",
    [(f"{MIRROR} تنها بر طاقچه نشسته", "کسی به او نگاه نمی‌کند")],
    "Mirror alone, no rust — contributes to prevalence only.")

POEMS[9104] = poem(9104, 1, "غزل آزمایشی ۱-۴",
    [(f"{MIRROR_VARIANT} کهنه در صندوق خانه", "خاک بر او نشسته آرام")],
    "Spelling-variant anchor test (آیینه instead of آینه); no rust present.")

POEMS[9105] = poem(9105, 1, "غزل آزمایشی ۱-۵",
    [(f"{MIRROR} {HEART} من شکسته از غم", "نه از شیشه، که از اندوه")],
    "Figurative/ambiguous case: 'mirror of the heart', not a literal object — "
    "intended calibration test for the ambiguous Occurrence Assessment. Also "
    "contributes one incidental HEART hit (see the HEART ground truth note).")

POEMS[9106] = poem(9106, 1, "غزل آزمایشی ۱-۶",
    [(f"{MIRROR} در خاطره شکست و رفت", f"{RUST} روی قاب کهنه نشست")],
    "Divergence case for Finding 1 of the external review (EXTERNAL_REVIEW.md): "
    "mirror and rust are lexically present in the SAME couplet, but the mirror "
    "use ('mirror of memory') is figurative and must be assessed REJECTED, "
    "while the rust use is literal ('rust settled on the old frame') and must "
    "be assessed ACCEPTED. This makes anchor-level mirror-rust co-incidence "
    "diverge from assessed-level co-incidence: an engine that computes "
    "co-incidence from raw anchors instead of assessed occurrences will count "
    "this poem/couplet; a correct engine will not.")

POEMS[9107] = poem(9107, 1, "غزل آزمایشی ۱-۷",
    [(f"{MIRROR}‌بند نو بر دیوار بستند", "کاری خوش از دست هنرمند")],
    "Substring-false-positive case for Finding 3 of the external review: "
    f"contains the compound word '{MIRROR}‌بند' (mirror-frame-maker/binder, "
    "joined by ZWNJ) which SHARES the literal substring 'آینه' but is a "
    "different token, not an occurrence of the word 'mirror'. A naive "
    "substring matcher over-counts this as a mirror anchor hit; a token/"
    "ZWNJ-aware matcher (spec §58) must not. This poem must NOT appear in "
    "poems_with_mirror.")

# --- Poet 2: one tight case (minority contributor), rest unrelated filler.
#     Ablating poet 1 should leave this poet's tight case surviving, so the
#     relation is concentrated (retention > 0%) rather than eliminated
#     entirely — a more realistic ablation fixture than a 0% collapse. ---
POETS["sample2"] = {"Id": 9002, "Name": "شاعر آزمایشی دو", "Nickname": "آزمایشی۲",
                     "Description": "Fabricated fixture poet, not a real historical figure.",
                     "BirthYearInLHijri": 750, "DeathYearInLHijri": 820, "ValidBirthDate": True, "ValidDeathDate": True}

POEMS[9201] = poem(9201, 2, "غزل آزمایشی ۲-۱",
    [(f"{MIRROR} و {RUST} در یک نفس", "با هم به دست باد سپردیم")],
    "Tight case from the minority poet: mirror and rust in the same couplet.")

POEMS[9202] = poem(9202, 2, "غزل آزمایشی ۲-۲",
    [("باغ بهاری پر از گل سرخ", "بلبل به شاخه نغمه می‌خواند")],
    "Unrelated filler poem (control unit for the denominator).")

POEMS[9203] = poem(9203, 2, "غزل آزمایشی ۲-۳",
    [("کوه بلند و رود روان", "در دامنه چادر زدیم")],
    "Unrelated filler poem (control unit for the denominator).")

POEMS[9204] = poem(9204, 2, "غزل آزمایشی ۲-۴",
    [("مرغ سحر آواز خواند", "بر شاخه‌ی بید کهنسال")],
    "Unrelated filler poem (control unit for the denominator).")

POEMS[9205] = poem(9205, 2, "غزل آزمایشی ۲-۵",
    [("شمع فروزان تا سحر", "قصه‌ای با کس نگفت")],
    "Unrelated filler poem (control unit for the denominator). Deliberately "
    "kept free of HEART/دل — see the note on 9105 about not letting the "
    "second fixture object leak into unrelated filler poems by accident.")

# --- Poet 3: zero incidence of either anchor. Purely denominator padding,
#     and a check that a poet with no hits is still counted as eligible
#     units contributing zero, not silently dropped from the field. ---
POETS["sample3"] = {"Id": 9003, "Name": "شاعر آزمایشی سه", "Nickname": "آزمایشی۳",
                     "Description": "Fabricated fixture poet, not a real historical figure.",
                     "BirthYearInLHijri": 850, "DeathYearInLHijri": 910, "ValidBirthDate": True, "ValidDeathDate": True}

for i, text in enumerate([
    "باران بهاری بر بام",
    "کاروان در دشت خاموش",
    "ستاره‌ای بر آسمان شب",
    "درخت کهن در باد",
    "چشمه‌ای میان کوه",
], start=1):
    pid = 9300 + i
    POEMS[pid] = poem(pid, 3, f"غزل آزمایشی ۳-{i}",
        [(text, "بی هیچ نشانی از این‌ها یافت نمی‌شود")],
        "Control poem, no anchors present (mirror, rust, or HEART), poet 3 "
        "has zero incidence of every tracked object.")

# --- Poet 4: a single, deliberately larger fixture object (HEART/دل, ~40
#     Anchor Hits) so `estimated`-mode incidence (spec §27.2, §70) can be
#     tested at a genuine <100% sampling fraction against a known census,
#     per Finding 2 of the external review (EXTERNAL_REVIEW.md) — a 6-hit
#     object cannot meaningfully falsify an estimator or a Wilson interval.
#     Every poem has exactly 2 couplets (4 verses), each verse contains
#     HEART exactly once, so each poem contributes exactly 4 hits and the
#     per-poem/per-couplet incidence is trivial to hand-verify. ---
POETS["sample4"] = {"Id": 9004, "Name": "شاعر آزمایشی چهار", "Nickname": "آزمایشی۴",
                     "Description": "Fabricated fixture poet, not a real historical figure. "
                                     "Exists to give the HEART object a realistic hit count.",
                     "BirthYearInLHijri": 600, "DeathYearInLHijri": 655, "ValidBirthDate": True, "ValidDeathDate": True}

# Every verse below contains exactly one HEART token and no other tracked
# object (mirror/rust) — deliberately uniform so the per-poem count (4) and
# the field total (40) are trivial to hand-verify, not just script-verify.
_HEART_COUPLET_PAIRS = [
    ("{H} من آرام گرفت امشب", "{H} تو کجا آرام گیرد"),
    ("در سینه {H} تنگ من است", "بیرون ز {H} راهی نیست"),
    ("{H} شکسته باز نشست", "{H} دیگر باز برخاست"),
    ("هر {H} به راه خویش رفت", "هیچ {H} به مقصد نرسید"),
    ("{H} پیر چه گوید", "{H} جوان چه شنود"),
    ("{H} من در بند تو ماند", "{H} تو آزاد چو باد"),
    ("یک {H} به دریا زد", "یک {H} به صحرا زد"),
    ("{H} گفت سخنی", "{H} شنید خبری"),
    ("{H} خاموش نشست", "{H} گویا برخاست"),
    ("{H} در آب ننگریست", "{H} در باد فرونرفت"),
]

for i, (right_t, left_t) in enumerate(_HEART_COUPLET_PAIRS, start=1):
    pid = 9400 + i
    right1, left1 = right_t.format(H=HEART), left_t.format(H=HEART)
    right2, left2 = f"{HEART} دیگر بار بازگشت", f"{HEART} دیگر بار برفت"
    POEMS[pid] = poem(pid, 4, f"غزل آزمایشی ۴-{i}",
        [(right1, left1), (right2, left2)],
        "HEART-frequency fixture poem (Finding 2 of the external review) — "
        "not thematically connected to the mirror/rust study. Exactly one "
        "HEART token per verse, 4 verses, so this poem contributes exactly "
        "4 HEART hits.")

POET_SLUGS = {"sample1": 9001, "sample2": 9002, "sample3": 9003, "sample4": 9004}
POET_POEM_IDS = {
    "sample1": [9101, 9102, 9103, 9104, 9105, 9106, 9107],
    "sample2": [9201, 9202, 9203, 9204, 9205],
    "sample3": [9301, 9302, 9303, 9304, 9305],
    "sample4": [9400 + i for i in range(1, len(_HEART_COUPLET_PAIRS) + 1)],
}

# Canonical OccurrenceAssessment decisions for the mirror-rust study fixture.
# This is deliberately a SEPARATE data structure from the corpus JSON above —
# per spec Part VIII, an Occurrence Assessment is a study/research record, not
# part of the documentary corpus, and must never be baked into corpus JSON as
# if Ganjoor itself asserted it. Phase 2 (P2.2) tests load this file and
# apply it; Phase 3 tests (P3.3, P3.6, P3.8) compute assessed-mode results
# from anchor hits + these decisions and compare against
# `_fixture_ground_truth`'s assessed-level fields.
CANONICAL_ASSESSMENTS = {
    "mirror": {
        "9101": "accepted", "9102": "accepted", "9103": "accepted",
        "9104": "accepted", "9105": "ambiguous", "9106": "rejected",
        "9201": "accepted",
        # 9107 is deliberately absent: under a correct token/ZWNJ-aware
        # matcher it never produces a mirror Anchor Hit in the first place
        # (see poem 9107's summary), so there is nothing to assess. An
        # engine that DOES produce an anchor hit there (naive substring
        # match) has already failed upstream of assessment.
    },
    "rust": {
        "9101": "accepted", "9102": "accepted", "9106": "accepted",
        "9201": "accepted",
    },
}
_ASSESSMENT_RATIONALE = {
    ("mirror", "9101"): "literal reflective surface in the scene",
    ("mirror", "9102"): "literal reflective surface in the scene",
    ("mirror", "9103"): "literal reflective surface in the scene",
    ("mirror", "9104"): "literal reflective surface (spelling-variant anchor)",
    ("mirror", "9105"): "unclear whether literal or figurative ('mirror of the heart')",
    ("mirror", "9106"): "figurative ('mirror of memory') -- not a literal object",
    ("mirror", "9201"): "literal reflective surface in the scene",
    ("rust", "9101"): "literal material rust in the scene",
    ("rust", "9102"): "literal material rust in the scene",
    ("rust", "9106"): "literal material rust ('rust settled on the old frame')",
    ("rust", "9201"): "literal material rust in the scene",
}

def write():
    for slug, pdata in POETS.items():
        poet_dir = ROOT / "poets" / slug
        (poet_dir / "ghazal").mkdir(parents=True, exist_ok=True)
        (poet_dir / "poet.json").write_text(
            json.dumps(pdata, ensure_ascii=False, indent=2), encoding="utf-8")
        cat = {
            "Id": POET_SLUGS[slug], "PoetId": POET_SLUGS[slug],
            "Title": "غزلیات آزمایشی", "Path": f"/{slug}/ghazal",
            "ChildCategories": [], "Poems": POET_POEM_IDS[slug],
        }
        (poet_dir / "ghazal" / "_cat.json").write_text(
            json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
        for pid in POET_POEM_IDS[slug]:
            (poet_dir / "ghazal" / f"p{pid}.json").write_text(
                json.dumps(POEMS[pid], ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "SchemaVersion": 1,
        "GeneratedAtUtc": "2026-08-27T00:00:00Z",
        "PoetsCount": len(POETS),
        "PoemsCount": len(POEMS),
        "IdIndexShardSize": 2000,
        "UrlTemplates": {
            "Poet": "poets/{poetSlug}/poet.json",
            "Category": "poets/{poetSlug}/{catPath}/_cat.json",
            "Poem": "poets/{poetSlug}/{catPath}/{poemSlug}.json",
        },
        "Poets": [{"Id": POET_SLUGS[s], "Nickname": POETS[s]["Nickname"],
                    "FullUrl": f"/{s}"} for s in POETS],
        "_fixture_ground_truth": {
            "note": "Every number below was computed by an INDEPENDENT "
                    "verification script (not by this generator's own "
                    "bookkeeping), run against the actual written JSON "
                    "files, before being pasted in here -- the same "
                    "discipline used for the original v1 fixture. See "
                    "EXTERNAL_REVIEW.md (Findings 1-3) for why the anchor/"
                    "assessed/token-aware distinctions below exist; they "
                    "did not exist in the pre-review fixture. The engine's "
                    "own results must match these exactly on this fixture, "
                    "or the fixture/engine disagreement is a bug to "
                    "root-cause, not a fixture to quietly edit.",
            "eligible_poems_total": len(POEMS),

            "anchor_level": {
                "note": "Raw lexical matches under NAIVE substring semantics "
                        "-- deliberately includes the poem-9107 false "
                        "positive, so a naive-substring engine and a "
                        "token-aware engine produce DIFFERENT numbers here. "
                        "See token_aware_level for the corrected numbers.",
                "mirror_anchor_hits_total": 8,
                "mirror_anchor_hits_by_form": {"آینه": 7, "آیینه": 1},
                "rust_anchor_hits_total": 4,
                "poems_with_mirror": [9101, 9102, 9103, 9104, 9105, 9106, 9107, 9201],
                "poems_with_rust": [9101, 9102, 9106, 9201],
                "poem_scale_mirror_rust_coincidence": [9101, 9102, 9106, 9201],
                "couplet_scale_mirror_rust_coincidence": [
                    "9101 couplet 0", "9106 couplet 0", "9201 couplet 0"
                ],
            },

            "token_aware_level": {
                "note": "Same as anchor_level but with the poem-9107 "
                        "substring false positive correctly excluded "
                        "('آینه‌بند' is a different token, not the word "
                        "mirror, spec §58). A spec-compliant matcher must "
                        "produce THESE numbers for lexical/anchor census "
                        "(§27.1), not the anchor_level numbers above.",
                "mirror_hits_total": 7,
                "poems_with_mirror": [9101, 9102, 9103, 9104, 9105, 9106, 9201],
                "excluded_false_positive_poem": 9107,
            },

            "assessed_level": {
                "note": "Computed from token_aware_level Anchor Hits plus "
                        "canonical-study-assessments.json. This is what "
                        "spec §27.2/§28.1 require a typed co-incidence "
                        "matrix, scale profile, and ablation to actually "
                        "use -- never raw anchors.",
                "accepted_mirror_poems": [9101, 9102, 9103, 9104, 9201],
                "ambiguous_mirror_poems": [9105],
                "rejected_mirror_poems": [9106],
                "accepted_rust_poems": [9101, 9102, 9106, 9201],
                "mirror_prevalence_poem_scale": "5/27",
                "poem_scale_mirror_rust_coincidence": [9101, 9102, 9201],
                "couplet_scale_mirror_rust_coincidence": [
                    "9101 couplet 0 (mirror Right, rust Left, both accepted)",
                    "9201 couplet 0 (mirror and rust both in the Right hemistich, both accepted)"
                ],
            },

            "divergence_note": "poem 9106 is the deliberate Finding-1 "
                "divergence case: it IS anchor-level and token-aware-level "
                "mirror-rust co-incidence, but is NOT assessed-level "
                "co-incidence, because its mirror hit is assessed rejected "
                "(figurative 'mirror of memory') while its rust hit is "
                "accepted (literal). An engine using raw/token-aware "
                "anchors instead of assessed occurrences for co-incidence "
                "will report 4 poems / 3 couplet-cases; a correct engine "
                "reports 3 poems / 2 couplet-cases.",

            "couplet_scale_broad_only_case": "9102 (mirror in couplet 0, rust in couplet 2 -- same poem, never the same couplet)",

            "ablation_remove_sample1": {
                "note": "sample1 = poems 9101-9107. Both anchor-level and "
                        "assessed-level retention are given because they "
                        "differ (another place a cheating engine diverges "
                        "from a correct one).",
                "anchor_poem_scale_retention": "1/4 poems remain (9201 only)",
                "assessed_poem_scale_retention": "1/3 poems remain (9201 only)",
                "anchor_couplet_scale_retention": "1/3 couplet-cases remain (9201 only)",
                "assessed_couplet_scale_retention": "1/2 couplet-cases remain (9201 only)",
            },

            "ambiguous_occurrence_assessment_case": "poem 9105 (figurative 'mirror of the heart' -- also the one place HEART leaks outside sample4, see heart_object below)",
            "rejected_occurrence_assessment_case": "poem 9106 (figurative 'mirror of memory' -- the Finding-1 divergence case)",
            "anchor_normalization_case": "poem 9104 (آیینه spelling variant, no rust present)",
            "substring_false_positive_case": "poem 9107 ('آینه‌بند', a ZWNJ-joined compound sharing the 'آینه' substring but not the word mirror -- Finding 3 of the external review)",
            "zero_incidence_control_poet": "sample3 (all 5 poems, 0 mirror, 0 rust, 0 heart)",

            "heart_object": {
                "note": "Second, larger fixture object (Finding 2 of the "
                        "external review) so estimated-mode incidence can "
                        "be tested at a genuine <100% sampling fraction. "
                        "sample4 (poems 9401-9410) contributes exactly 4 "
                        "hits per poem, 40 total; poem 9105 incidentally "
                        "contributes 1 more from the mirror/heart figurative "
                        "line, for a field-wide total of 41. Estimation "
                        "tests (P2.4/P7.5) should sample from the full "
                        "41-hit population, not just the clean 40-hit "
                        "sample4 subset, since a real study field would not "
                        "artificially exclude the incidental hit either.",
                "sample4_hits": 40,
                "sample4_poems": [9401, 9402, 9403, 9404, 9405, 9406, 9407, 9408, 9409, 9410],
                "incidental_hit_outside_sample4": "poem 9105 (1 hit)",
                "field_total_hits": 41,
                "field_total_poems_with_heart": 11,
            },
        },
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    (ROOT / "canonical-study-assessments.json").write_text(
        json.dumps({
            "note": "Canonical OccurrenceAssessment decisions for the "
                    "mirror-rust study fixture. See CANONICAL_ASSESSMENTS "
                    "in generate_fixture.py for the source of truth and "
                    "rationale.",
            "assessments": CANONICAL_ASSESSMENTS,
            "rationale": {f"{obj}:{pid}": r for (obj, pid), r in _ASSESSMENT_RATIONALE.items()},
        }, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    write()
    print("Wrote fixture corpus under", ROOT)
