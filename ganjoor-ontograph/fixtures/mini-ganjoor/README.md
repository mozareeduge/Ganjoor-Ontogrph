# mini-ganjoor fixture corpus

Fabricated, schema-accurate synthetic corpus for automated tests. **Not
real Persian poetry and not real Ganjoor content** — every line was
written for this fixture and should never be quoted as if it were.

Revised after an independent external review (`../../EXTERNAL_REVIEW.md`)
found that the original (v1) version of this fixture let anchor-level and
assessed-level results collapse into the same numbers everywhere — meaning
an engine that skipped occurrence assessment entirely could pass every
relation-level test. v2 below fixes that.

- 4 poets, 27 poems total.
- `sample1` (7 poems, `9101`–`9107`) carries most of the mirror/rust signal:
  1 tight couplet-scale case (`9101`), 1 broad-poem-only case (`9102`), 1
  mirror-alone case (`9103`), 1 spelling-variant case (`9104`), 1
  ambiguous case (`9105`, "mirror of the heart"), and — new in v2 — 1
  **divergence case** (`9106`: mirror and rust share a couplet lexically,
  but the mirror use is figurative and assessed *rejected*, so this couplet
  counts toward anchor-level co-incidence but NOT assessed-level
  co-incidence) and 1 **substring-false-positive case** (`9107`: contains
  the compound word `آینه‌بند`, which shares the `آینه` substring but is a
  different token — a naive substring matcher over-counts it, a
  token/ZWNJ-aware matcher must not).
- `sample2` (5 poems) carries one minority tight case (`9201`) plus four
  unrelated filler poems — this is what makes the ablation fixture
  meaningful: removing `sample1` should reduce, not eliminate, the
  tight-scale relation, and the reduction ratio itself now differs between
  anchor-level and assessed-level ablation (see `manifest.json`).
- `sample3` (5 poems) has zero incidence of mirror, rust, *or* the HEART
  object below — pure denominator padding and a check that a
  zero-incidence poet stays in the eligible-unit count rather than being
  dropped.
- `sample4` (10 poems, `9401`–`9410`, new in v2) exists only to give a
  second fixture object, HEART (`دل`), a realistic hit count (40, exactly 4
  per poem) — a 6-hit object can't meaningfully test `estimated`-mode
  incidence at a genuine sampling fraction below 100%. One more HEART hit
  appears incidentally in `9105`'s figurative "mirror of the heart" line
  (field-wide total: 41 hits, 11 poems).
- `canonical-study-assessments.json` (new in v2) holds the Occurrence
  Assessment decisions (`accepted`/`rejected`/`ambiguous`) the fixture
  "study" applies to mirror and rust hits — deliberately a separate file
  from the corpus JSON, matching spec Part VIII's separation of documentary
  source from study record.

Regenerate with `python3 generate_fixture.py` (deterministic; re-running it
produces byte-identical output). **If you edit the generator, re-derive
`_fixture_ground_truth` in `manifest.json` with an *independent*
verification script — never by hand-editing numbers, and never by trusting
the generator's own bookkeeping** (this is what actually caught two
accidental `دل` leaks and a miscounted template during v2's construction).
A script equivalent to the one used to produce the current numbers:

```bash
python3 - <<'PYEOF'
import json, glob, collections
MIRROR_FORMS, RUST, HEART = ["آینه", "آیینه"], "زنگار", "دل"
mirror_hits, poems_with_mirror, poems_with_rust, couplet_tight = collections.Counter(), [], [], []
for f in sorted(glob.glob("poets/*/ghazal/p*.json")):
    d = json.load(open(f, encoding="utf-8")); pid = d["Id"]
    mc, rc = set(), set()
    for v in d["Verses"]:
        for form in MIRROR_FORMS:
            if form in v["Text"]: mirror_hits[form] += 1; mc.add(v["CoupletIndex"])
        if RUST in v["Text"]: rc.add(v["CoupletIndex"])
    if mc: poems_with_mirror.append(pid)
    if rc: poems_with_rust.append(pid)
    if mc & rc: couplet_tight.append((pid, sorted(mc & rc)))
print("mirror (anchor level, includes 9107 false positive):", dict(mirror_hits))
print("poem-scale anchor co-inc:", sorted(set(poems_with_mirror) & set(poems_with_rust)))
print("couplet-scale anchor:", couplet_tight)
PYEOF
```

Then apply `canonical-study-assessments.json` on top to get assessed-level
numbers — see `test_fixture_ground_truth.py` for the full worked
computation (anchor, token-aware, and assessed levels, plus ablation at
each level).

This fixture is the ground truth for spec §67 Tests A–F (Phase 7 of
`../../implementation/BUILD_PLAN.md`):

| Test (§67) | Fixture case |
|---|---|
| A — concentrated frequency | mirror is concentrated in `sample1` (5/7 assessed-accepted poem hits) |
| B — scale collapse | poem 9102: co-occurs at poem scale, never at couplet scale |
| C — lexical ambiguity | poem 9105: figurative "mirror of the heart" (ambiguous) |
| D — ablation false centre | removing `sample1` drops assessed couplet-scale co-incidence from 2 to 1 (anchor-scale: 3 to 1 — the two ratios differ, by design) |
| E — local close-reading insight | poem 9201's tight case survives `sample1` removal |
| F — research-made mediation | not covered here; needs a Relation-Object fixture built in Phase 4 |

Two cases added in v2, outside the original §67 lettering, cover findings
from the external review directly:

| Review finding | Fixture case |
|---|---|
| Finding 1 — anchor/assessed co-incidence must diverge | poem 9106: rejected mirror hit + accepted rust hit, same couplet |
| Finding 3 — substring vs. token-boundary matching must diverge | poem 9107: `آینه‌بند` (compound, ZWNJ-joined) |
