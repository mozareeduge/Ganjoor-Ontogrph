"""Locks in the fixture's own hand-verified ground truth.

This test has NO dependency on the ontograph engine (which doesn't exist
yet at Phase 0) -- it only checks that the fixture's raw JSON, plus
canonical-study-assessments.json, matches the `_fixture_ground_truth`
block in manifest.json. Once the real engine exists (Phase 1+), its
census/mapping functions should be tested against this SAME
`_fixture_ground_truth` block rather than against a second, possibly-
drifted copy of these numbers -- import `GROUND_TRUTH` from here.

Rewritten after the external review (EXTERNAL_REVIEW.md, Findings 1-3):
this fixture now distinguishes anchor-level (naive substring), token-aware
(the false positive in poem 9107 excluded), and assessed-level (occurrence
assessment applied) results, because those three levels must NOT collapse
into one number -- that collapse is exactly the failure mode the whole
apparatus exists to prevent.

Run: pytest fixtures/mini-ganjoor/test_fixture_ground_truth.py -q
"""
import json
import glob
import collections
import pathlib

HERE = pathlib.Path(__file__).parent
MIRROR_FORMS = ["آینه", "آیینه"]
RUST = "زنگار"
HEART = "دل"
FALSE_POSITIVE_POEM = 9107  # 'آینه‌بند' -- shares the mirror substring, is not the word mirror
SAMPLE1_POEMS = {9101, 9102, 9103, 9104, 9105, 9106, 9107}

with open(HERE / "manifest.json", encoding="utf-8") as f:
    GROUND_TRUTH = json.load(f)["_fixture_ground_truth"]

with open(HERE / "canonical-study-assessments.json", encoding="utf-8") as f:
    ASSESSMENTS = json.load(f)["assessments"]


def _load_poems():
    poems = {}
    for fp in sorted(glob.glob(str(HERE / "poets/*/ghazal/p*.json"))):
        d = json.loads(pathlib.Path(fp).read_text(encoding="utf-8"))
        poems[d["Id"]] = d
    return poems


def _scan_anchor_level(poems):
    """Naive substring scan -- what an engine WITHOUT token-aware matching
    would produce. Deliberately includes the 9107 false positive."""
    mirror_hits = collections.Counter()
    poems_with_mirror, poems_with_rust = [], []
    mirror_couplets, rust_couplets = {}, {}
    for pid, d in poems.items():
        mc, rc = set(), set()
        for v in d["Verses"]:
            text, ci = v["Text"], v["CoupletIndex"]
            for form in MIRROR_FORMS:
                if form in text:
                    mirror_hits[form] += 1
                    mc.add(ci)
            if RUST in text:
                rc.add(ci)
        if mc:
            poems_with_mirror.append(pid)
            mirror_couplets[pid] = mc
        if rc:
            poems_with_rust.append(pid)
            rust_couplets[pid] = rc
    return mirror_hits, poems_with_mirror, poems_with_rust, mirror_couplets, rust_couplets


def test_poem_count():
    poems = _load_poems()
    assert len(poems) == GROUND_TRUTH["eligible_poems_total"] == 27


def test_anchor_level_matches_ground_truth():
    """A naive substring matcher's raw output -- includes the 9107 trap."""
    poems = _load_poems()
    mirror_hits, poems_with_mirror, poems_with_rust, _, _ = _scan_anchor_level(poems)
    gt = GROUND_TRUTH["anchor_level"]
    assert sum(mirror_hits.values()) == gt["mirror_anchor_hits_total"]
    assert dict(mirror_hits) == gt["mirror_anchor_hits_by_form"]
    assert sorted(poems_with_mirror) == sorted(gt["poems_with_mirror"])
    assert sorted(poems_with_rust) == sorted(gt["poems_with_rust"])
    assert FALSE_POSITIVE_POEM in poems_with_mirror, (
        "sanity check: the naive scan MUST trip on poem 9107's compound "
        "word, or the false-positive trap isn't actually set"
    )


def test_token_aware_level_excludes_false_positive():
    """What a spec-compliant (token/ZWNJ-aware, spec §58) matcher must
    produce: the same as anchor-level, minus the 9107 false positive.
    This test only encodes the EXPECTED correction -- the real tokenizer
    itself is Phase 1's job (ledger P1.1/P1.2); an engine implementation
    is correct only if ITS census matches token_aware_level, not
    anchor_level."""
    poems = _load_poems()
    mirror_hits, poems_with_mirror, _, _, _ = _scan_anchor_level(poems)
    gt = GROUND_TRUTH["token_aware_level"]
    corrected_total = sum(mirror_hits.values()) - 1  # minus the 9107 hit
    corrected_poems = sorted(p for p in poems_with_mirror if p != FALSE_POSITIVE_POEM)
    assert corrected_total == gt["mirror_hits_total"]
    assert corrected_poems == sorted(gt["poems_with_mirror"])
    assert gt["excluded_false_positive_poem"] == FALSE_POSITIVE_POEM


def test_assessed_level_diverges_from_anchor_level():
    """The central regression test for Finding 1 of the external review:
    assessed-level co-incidence must be STRICTLY SMALLER than anchor-level
    co-incidence, because poem 9106's mirror hit is rejected. A engine
    that computes co-incidence from raw/token-aware anchors instead of
    assessed occurrences will fail this test by matching anchor numbers
    instead of assessed ones."""
    poems = _load_poems()
    _, poems_with_mirror, poems_with_rust, mirror_couplets, rust_couplets = _scan_anchor_level(poems)

    accepted_mirror = sorted(int(p) for p, dec in ASSESSMENTS["mirror"].items() if dec == "accepted")
    accepted_rust = sorted(int(p) for p, dec in ASSESSMENTS["rust"].items() if dec == "accepted")
    assessed_gt = GROUND_TRUTH["assessed_level"]
    assert accepted_mirror == sorted(assessed_gt["accepted_mirror_poems"])
    assert accepted_rust == sorted(assessed_gt["accepted_rust_poems"])

    anchor_coincidence = sorted(set(poems_with_mirror) & set(poems_with_rust))
    assessed_coincidence = sorted(set(accepted_mirror) & set(accepted_rust))
    assert assessed_coincidence == sorted(assessed_gt["poem_scale_mirror_rust_coincidence"])
    assert anchor_coincidence == sorted(GROUND_TRUTH["anchor_level"]["poem_scale_mirror_rust_coincidence"])

    # the actual regression guard: these must NOT be equal
    assert len(assessed_coincidence) < len(anchor_coincidence), (
        "assessed-level co-incidence must be strictly smaller than "
        "anchor-level co-incidence (poem 9106's mirror hit is rejected) -- "
        "if these are equal, the divergence fixture case has been lost"
    )
    assert 9106 in anchor_coincidence and 9106 not in assessed_coincidence

    # couplet scale: same divergence, one level down
    anchor_couplet = sorted(
        (pid, c) for pid in set(poems_with_mirror) & set(poems_with_rust)
        for c in mirror_couplets[pid] & rust_couplets[pid]
    )
    assessed_couplet = sorted(
        (pid, c) for pid in set(accepted_mirror) & set(accepted_rust)
        for c in mirror_couplets.get(pid, set()) & rust_couplets.get(pid, set())
    )
    assert len(assessed_couplet) < len(anchor_couplet)
    assert (9106, 0) in anchor_couplet and (9106, 0) not in assessed_couplet


def test_ablation_anchor_vs_assessed_retention_differ():
    """Removing sample1 (poems 9101-9107) should leave different retention
    ratios depending on whether ablation is computed from anchor-level or
    assessed-level co-incidence -- another place the two must not collapse."""
    poems = _load_poems()
    _, poems_with_mirror, poems_with_rust, mirror_couplets, rust_couplets = _scan_anchor_level(poems)
    accepted_mirror = {int(p) for p, dec in ASSESSMENTS["mirror"].items() if dec == "accepted"}
    accepted_rust = {int(p) for p, dec in ASSESSMENTS["rust"].items() if dec == "accepted"}

    anchor_coincidence = set(poems_with_mirror) & set(poems_with_rust)
    assessed_coincidence = accepted_mirror & accepted_rust

    anchor_remaining = anchor_coincidence - SAMPLE1_POEMS
    assessed_remaining = assessed_coincidence - SAMPLE1_POEMS

    ablation_gt = GROUND_TRUTH["ablation_remove_sample1"]
    assert f"{len(anchor_remaining)}/{len(anchor_coincidence)} poems remain (9201 only)" == ablation_gt["anchor_poem_scale_retention"]
    assert f"{len(assessed_remaining)}/{len(assessed_coincidence)} poems remain (9201 only)" == ablation_gt["assessed_poem_scale_retention"]
    assert anchor_remaining == assessed_remaining == {9201}


def test_zero_incidence_control_poet_has_no_hits():
    for fp in sorted(glob.glob(str(HERE / "poets/sample3/ghazal/p*.json"))):
        d = json.loads(pathlib.Path(fp).read_text(encoding="utf-8"))
        for v in d["Verses"]:
            for token in MIRROR_FORMS + [RUST, HEART]:
                assert token not in v["Text"], f"{fp} unexpectedly contains {token!r}"


def test_heart_object_ground_truth():
    """The larger (~40-hit) fixture object added for Finding 2 -- makes
    estimated-mode incidence testable at a genuine <100% sampling
    fraction. Verified independently of the generator's own bookkeeping."""
    poems = _load_poems()
    heart_gt = GROUND_TRUTH["heart_object"]
    sample4_ids = set(range(9401, 9411))
    per_poem = {}
    total = 0
    poems_with_heart = []
    for pid, d in poems.items():
        count = sum(1 for v in d["Verses"] if HEART in v["Text"])
        if count:
            poems_with_heart.append(pid)
            total += count
        if pid in sample4_ids:
            per_poem[pid] = count

    assert sorted(per_poem) == sorted(heart_gt["sample4_poems"])
    assert all(c == 4 for c in per_poem.values()), per_poem
    assert sum(per_poem.values()) == heart_gt["sample4_hits"] == 40
    assert total == heart_gt["field_total_hits"] == 41
    assert len(poems_with_heart) == heart_gt["field_total_poems_with_heart"] == 11
    incidental = [p for p in poems_with_heart if p not in sample4_ids]
    assert incidental == [9105]
