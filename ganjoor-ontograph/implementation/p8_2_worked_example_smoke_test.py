"""Ledger row P8.2 manual smoke test: spec §45's worked example
(mirror/rust as a seed, scoped to Hafez) run against the real vendored
corpus (this repo's own root). Not part of the automated ledger --
Phase 8 is deliberately manual (see IMPLEMENTATION_LEDGER.md). Produces
real output for a human to read against §45's narrative; it does not
self-certify a pass.

Run from the repo root:
    python3 ganjoor-ontograph/implementation/p8_2_worked_example_smoke_test.py
"""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ganjoor-ontograph" / "src"))

from ontograph.anchors import LexicalAnchor, census
from ontograph.census import calibration_sample, open_context_ladder
from ontograph.compare import MODE_ANCHOR, typed_coincidence
from ontograph.field import scan_corpus

MIRROR = [LexicalAnchor(object_address="mirror", form="آینه"), LexicalAnchor(object_address="mirror", form="آیینه")]
RUST = [LexicalAnchor(object_address="rust", form="زنگار")]


def main() -> None:
    t0 = time.time()
    records = scan_corpus(REPO_ROOT)
    t1 = time.time()
    print(f"scan_corpus: {len(records)} poems in {t1 - t0:.1f}s")

    hits = census(records, MIRROR + RUST)
    t2 = time.time()
    print(f"census (whole real corpus, both objects): {len(hits)} hits in {t2 - t1:.1f}s")

    mirror_hits_all = [h for h in hits if h.object_address == "mirror"]
    rust_hits_all = [h for h in hits if h.object_address == "rust"]
    print(f"mirror anchor hits (whole corpus): {len(mirror_hits_all)} across {len({h.poem_id for h in mirror_hits_all})} poems")
    print(f"rust anchor hits (whole corpus): {len(rust_hits_all)} across {len({h.poem_id for h in rust_hits_all})} poems")

    hafez_ids = {r.poem_id for r in records if r.poet_slug == "hafez"}
    mirror_hafez = [h for h in mirror_hits_all if h.poem_id in hafez_ids]
    rust_hafez = [h for h in rust_hits_all if h.poem_id in hafez_ids]
    print("\n--- Hafez scope (695 poems) ---")
    print(f"mirror hits in Hafez: {len(mirror_hafez)} across {len({h.poem_id for h in mirror_hafez})} poems")
    print(f"rust hits in Hafez: {len(rust_hafez)} across {len({h.poem_id for h in rust_hafez})} poems")

    sample = calibration_sample(mirror_hafez, sample_size=6, seed=20260830)
    records_by_id = {r.poem_id: r for r in records}
    print("\n--- calibration sample of 6 mirror hits in Hafez (seed=20260830) ---")
    for h in sample:
        ctx = open_context_ladder(h, records_by_id[h.poem_id].path)
        print(f"poem {h.poem_id} ({ctx['poem_title']}): {h.original_text}")

    result = typed_coincidence(mirror_hafez, rust_hafez, mode=MODE_ANCHOR)
    print("\n--- mirror x rust anchor-level co-incidence, Hafez only ---")
    print(f"poem-scale: {sorted(result.poem_scale)}")
    print(f"couplet-scale: {sorted(result.couplet_scale)}")

    if result.poem_scale:
        print("\n--- source verses for poem-scale co-incidence poems ---")
        for pid in sorted(result.poem_scale):
            m = next(h.original_text for h in mirror_hafez if h.poem_id == pid)
            r = next(h.original_text for h in rust_hafez if h.poem_id == pid)
            print(f"poem {pid}:\n  mirror: {m}\n  rust:   {r}")

    print(f"\ntotal wall time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
