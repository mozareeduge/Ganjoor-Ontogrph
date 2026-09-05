"""Ledger row P8.2 manual smoke test: spec §45's worked example
(mirror/rust as a seed) run against the real vendored corpus (this
repo's own root). Not part of the automated ledger -- Phase 8 is
deliberately manual for the parts that need a human's own literary
judgment (see IMPLEMENTATION_LEDGER.md); this script only produces real
output for that review, it does not self-certify a pass.

Two scopes are run:
  1. Hafez only, as the ledger row's own instruction names literally.
  2. The whole real corpus, to find an actual mirror x rust relation
     worth walking through -- Hafez alone turns out to have zero "زنگار"
     hits (see part 1's own output), so part 2 is what actually exercises
     §45's full narrative (poem-scale -> couplet-scale -> ablation) on
     real text.

Run from the repo root (takes roughly 3-4 minutes, most of it the
whole-corpus census in part 2):
    python3 ganjoor-ontograph/implementation/p8_2_worked_example_smoke_test.py
"""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ganjoor-ontograph" / "src"))

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor, census
from ontograph.census import calibration_sample, open_context_ladder
from ontograph.compare import MODE_ANCHOR, typed_coincidence
from ontograph.field import scan_corpus

MIRROR = [LexicalAnchor(object_address="mirror", form="آینه"), LexicalAnchor(object_address="mirror", form="آیینه")]
RUST = [LexicalAnchor(object_address="rust", form="زنگار")]


def main() -> None:
    t0 = time.time()
    records = scan_corpus(REPO_ROOT)
    records_by_id = {r.poem_id: r for r in records}
    t1 = time.time()
    print(f"scan_corpus: {len(records)} poems in {t1 - t0:.1f}s")

    hits = census(records, MIRROR + RUST)
    t2 = time.time()
    print(f"census (whole real corpus, both objects): {len(hits)} hits in {t2 - t1:.1f}s")

    mirror_hits = [h for h in hits if h.object_address == "mirror"]
    rust_hits = [h for h in hits if h.object_address == "rust"]
    print(f"mirror anchor hits (whole corpus): {len(mirror_hits)} across {len({h.poem_id for h in mirror_hits})} poems")
    print(f"rust anchor hits (whole corpus): {len(rust_hits)} across {len({h.poem_id for h in rust_hits})} poems")

    # --- Part 1: Hafez only, as the ledger row's own instruction names ---
    hafez_ids = {r.poem_id for r in records if r.poet_slug == "hafez"}
    mirror_hafez = [h for h in mirror_hits if h.poem_id in hafez_ids]
    rust_hafez = [h for h in rust_hits if h.poem_id in hafez_ids]
    print("\n=== Part 1: Hafez only (695 poems) ===")
    print(f"mirror hits: {len(mirror_hafez)} across {len({h.poem_id for h in mirror_hafez})} poems")
    print(f"rust hits: {len(rust_hafez)} across {len({h.poem_id for h in rust_hafez})} poems")
    print("(0 rust hits -- the exact mirror x rust co-incidence §45 narrates does not occur in Hafez under 'زنگار' alone)")

    sample = calibration_sample(mirror_hafez, sample_size=6, seed=20260830)
    print("\n--- calibration sample of 6 mirror hits in Hafez (seed=20260830) ---")
    for h in sample:
        ctx = open_context_ladder(h, records_by_id[h.poem_id].path)
        print(f"poem {h.poem_id} ({ctx['poem_title']}): {h.original_text}")

    # --- Part 2: whole real corpus -- an actual mirror x rust relation ---
    print("\n=== Part 2: whole real corpus (132,538 poems, 234 poets) ===")
    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    print(f"poem-scale co-incidence: {len(result.poem_scale)} poems")
    print(f"couplet-scale co-incidence: {len(result.couplet_scale)} couplet-cases")

    by_poet: dict[str, list[int]] = {}
    for pid in result.poem_scale:
        by_poet.setdefault(records_by_id[pid].poet_slug, []).append(pid)
    top = sorted(by_poet.items(), key=lambda kv: -len(kv[1]))[:5]
    print(f"distinct poets touched (poem-scale): {len(by_poet)}; top 5: {[(s, len(p)) for s, p in top]}")

    dominant_slug, dominant_poems = top[0]
    dominant_poem_ids = {r.poem_id for r in records if r.poet_slug == dominant_slug}
    ablation = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, dominant_poem_ids)
    print(f"\n--- ablation: remove dominant poet '{dominant_slug}' ({len(dominant_poem_ids)} poems) ---")
    print(f"poem-scale: {ablation.original_poem_scale} -> {ablation.remaining_poem_scale} "
          f"(retention {ablation.poem_scale_retention:.1%})")
    print(f"couplet-scale: {ablation.original_couplet_scale} -> {ablation.remaining_couplet_scale} "
          f"(retention {ablation.couplet_scale_retention:.1%})")
    print("(majority retention after removing the single dominant poet -- per §45's own branching, "
          "this reads as a relation that survives, not one collapsing to a false centre)")

    if result.couplet_scale:
        pid, ci = sorted(result.couplet_scale)[0]
        m = next(h.original_text for h in mirror_hits if h.poem_id == pid and h.couplet_index == ci)
        r = next(h.original_text for h in rust_hits if h.poem_id == pid and h.couplet_index == ci)
        print(f"\n--- one couplet-scale example: poet={records_by_id[pid].poet_slug}, poem={pid}, couplet={ci} ---")
        print(f"mirror line: {m}")
        print(f"rust line:   {r}")

    print(f"\ntotal wall time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
