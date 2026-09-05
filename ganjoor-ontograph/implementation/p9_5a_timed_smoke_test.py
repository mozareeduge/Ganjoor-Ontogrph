"""Ledger row P9.5-A timed real-corpus smoke: the P8.2 worked example
(spec §45, mirror/rust) re-run through the P9.2/P9.3 cached-index
pipeline, with wall times, to confirm materially faster than P8.2's
recorded numbers (`field build` 1m21s; single-word census timed out at
2min) while matching P8.2's findings (poem-scale co-incidence 378,
couplet-scale 310, dominant poet saeb, majority retention after
ablation).

Run:  ganjoor-ontograph/.venv/Scripts/python implementation/p9_5a_timed_smoke_test.py
"""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ganjoor-ontograph" / "src"))

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor
from ontograph.compare import MODE_ANCHOR, typed_coincidence
from ontograph.index_cache import (
    census_from_index,
    get_or_build_index,
    records_from_index,
)

CORPUS_ROOT = REPO_ROOT
MIRROR = [LexicalAnchor(object_address="mirror", form="آینه"),
          LexicalAnchor(object_address="mirror", form="آیینه")]
RUST = [LexicalAnchor(object_address="rust", form="زنگار")]


def main() -> None:
    t0 = time.time()
    conn1, build_manifest, cache_hit = get_or_build_index(CORPUS_ROOT)
    t1 = time.time()
    print(f"open index (cache_hit={cache_hit}): {t1 - t0:.2f}s "
          f"(a False here is the one-time cold build, paid once)")
    print(f"build_manifest: {build_manifest}")

    records = records_from_index(conn1)
    t2 = time.time()
    print(f"records_from_index: {len(records)} poems in {t2 - t1:.2f}s")

    hits = census_from_index(conn1, records, MIRROR + RUST)
    t3 = time.time()
    conn1.close()
    print(f"WARM census (whole real corpus, both objects): {len(hits)} hits in {t3 - t2:.2f}s")

    mirror_hits = [h for h in hits if h.object_address == "mirror"]
    rust_hits = [h for h in hits if h.object_address == "rust"]
    print(f"mirror anchor hits: {len(mirror_hits)} across {len({h.poem_id for h in mirror_hits})} poems")
    print(f"rust anchor hits: {len(rust_hits)} across {len({h.poem_id for h in rust_hits})} poems")

    result = typed_coincidence(mirror_hits, rust_hits, mode=MODE_ANCHOR)
    t4 = time.time()
    print(f"poem-scale co-incidence: {len(result.poem_scale)} poems "
          f"(P8.2 ground truth: 378)")
    print(f"couplet-scale co-incidence: {len(result.couplet_scale)} couplet-cases "
          f"(P8.2 ground truth: 310)")

    records_by_id = {r.poem_id: r for r in records}
    by_poet: dict[str, list[int]] = {}
    for pid in result.poem_scale:
        by_poet.setdefault(records_by_id[pid].poet_slug, []).append(pid)
    top = sorted(by_poet.items(), key=lambda kv: -len(kv[1]))[:5]
    print(f"distinct poets touched (poem-scale): {len(by_poet)} (P8.2: 84); "
          f"top 5: {[(s, len(p)) for s, p in top]}")

    dominant_slug, dominant_poems = top[0]
    dominant_poem_ids = {r.poem_id for r in records if r.poet_slug == dominant_slug}
    ablation = ablation_retention(mirror_hits, rust_hits, MODE_ANCHOR, dominant_poem_ids)
    print(f"ablation: remove '{dominant_slug}' ({len(dominant_poem_ids)} poems): "
          f"{ablation.original_poem_scale} -> {ablation.remaining_poem_scale} "
          f"({ablation.poem_scale_retention:.1%} poem-scale), "
          f"{ablation.original_couplet_scale} -> {ablation.remaining_couplet_scale} "
          f"({ablation.couplet_scale_retention:.1%} couplet-scale)")

    print(f"\ntotal wall time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
