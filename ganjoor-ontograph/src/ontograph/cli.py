"""`ontograph` console script.

Spec §62 (CLI as reproducibility layer) and §78 (Claude Code invocation
pattern: every verb accepts --json, non-zero exit + stderr on failure,
never a silent empty-JSON success). Verb names deliberately avoid
`search`/`query` (spec §25 v2.3.0 disambiguation note -- those names belong
to the sibling persian-poetry-mcp skill's retrieval surface, not here).

Every verb prints one JSON object to stdout and exits 0 on success. With
`--json` the object is pretty-printed; without it, it is printed compact
on one line -- v0.1 has no separate prose renderer (that lives in the
conversational skill, Phase 6, per spec §41-43's progressive-disclosure
layer, not the deterministic CLI itself).

Every verb that reads Anchor Hits accepts `--mode anchor|assessed`
(default `anchor`) and says which mode it used in its own output. `assess`
records one `OccurrenceAssessment` at a time into the study's Occurrence
Ledger (`corpus/occurrence-ledger.jsonl`, spec §60's own workspace
layout); `--mode assessed` on `census`/`map recurrence`/`companions`/
`ablate`/`compare` reads that ledger and refuses (`CLIError`) rather than
silently falling back to anchor level if no assessments have been
recorded yet for the object(s) involved (spec §8.1, Appendix A: "Anchor
Hit != object occurrence" -- the exact collapse Finding 1 of the
external review was about, now guarded at the CLI surface too, not just
in `compare.py`/`ablation.py` themselves).

Implemented in ledger rows P5.1-P5.3, extended in Phase 8 (ledger row
P8.2's own testing surfaced the missing `assess` verb as the CLI's most
consequential real-corpus usability gap).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from ontograph.ablation import ablation_retention
from ontograph.anchors import LexicalAnchor, census as run_census
from ontograph.census import (
    OccurrenceAssessment,
    accepted_poem_ids,
    ambiguous_only_poem_ids,
    assessed_full_prevalence,
    calibration_sample,
    open_context_ladder,
)
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED, InsufficientSupportError, compare_fields, lift, typed_coincidence
from ontograph.field import FieldCharter, ScopeSpec, all_poems, poet, scan_corpus
from ontograph.metrics import spread
from ontograph.release import DATA_LICENSE_NOTICE, generate_release, release_as_git_tag
from ontograph.workspace import new_study, read_study_config


class CLIError(Exception):
    """Raised for a bad-input, missing-workspace, or malformed-field-spec
    condition (ledger row P5.3) -- `main()` catches this, prints the
    message to stderr, and returns a non-zero exit code. Never printed as
    a JSON success object."""


# --- shared helpers ---

def _workspace_path(args) -> Path:
    return Path(args.workspaces_dir) / args.study_id


def _require_workspace(args) -> Path:
    ws = _workspace_path(args)
    if not ws.is_dir():
        raise CLIError(f"study workspace not found: {ws} (run 'ontograph study new' first)")
    return ws


def _object_addresses_path(ws: Path) -> Path:
    return ws / "objects" / "object-addresses.jsonl"


def _load_object_entry(ws: Path, object_address: str) -> dict:
    path = _object_addresses_path(ws)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry["id"] == object_address:
                return entry
    raise CLIError(
        f"object address not registered: {object_address!r} "
        f"(run 'ontograph object add' first)"
    )


def _anchors_for(ws: Path, object_address: str) -> list[LexicalAnchor]:
    entry = _load_object_entry(ws, object_address)
    return [LexicalAnchor(object_address=object_address, form=f) for f in entry["anchors"]]


def _occurrence_ledger_path(ws: Path) -> Path:
    return ws / "corpus" / "occurrence-ledger.jsonl"


def _load_assessments(ws: Path, object_address: str) -> dict[int, str]:
    """poem_id -> decision, latest entry wins per poem (re-assessment is
    normal calibration practice, unlike the append-only EventRecord log)."""
    path = _occurrence_ledger_path(ws)
    assessments: dict[int, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry["object_address"] == object_address:
                assessments[entry["anchor_hit_poem_id"]] = entry["decision"]
    return assessments


def _resolve_corpus_root(args, ws: Path) -> str:
    """Ledger row P9.1: an explicit `--corpus-root` always overrides; absent
    that, fall back to what `study new --corpus-root` persisted for this
    study. Raises -- never silently proceeds with no corpus root at all."""
    if getattr(args, "corpus_root", None):
        return args.corpus_root
    stored = read_study_config(ws).get("corpus_root")
    if stored:
        return stored
    raise CLIError(
        "no --corpus-root given and this study has none stored -- "
        "pass --corpus-root explicitly, or re-run 'ontograph study new "
        "--corpus-root ...' to store one for next time"
    )


def _accepted_or_raise(ws: Path, object_address: str, hits) -> set[int]:
    assessments = _load_assessments(ws, object_address)
    if not assessments:
        raise CLIError(
            f"no assessments recorded for object {object_address!r} -- "
            f"run 'ontograph assess' first, or use --mode anchor"
        )
    return accepted_poem_ids(hits, assessments)


# --- verb implementations, each returning a plain JSON-serializable dict ---

def _study_new(args) -> dict:
    ws = _workspace_path(args)
    new_study(args.workspaces_dir, args.study_id, corpus_root=args.corpus_root)
    result = {"study_id": args.study_id, "workspace": str(ws)}
    if args.corpus_root:
        result["corpus_root"] = args.corpus_root
    return result


def _field_build(args) -> dict:
    ws = _require_workspace(args)
    if args.category:
        raise CLIError(
            "--category is not supported in v0.1 (ScopeSpec has no category "
            "leaf kind yet); use --poet or omit both for the full field"
        )
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    scope: ScopeSpec = poet(args.poet) if args.poet else all_poems()
    charter = FieldCharter(
        purpose=f"field for study {args.study_id}",
        corpus_snapshot=str(corpus_root),
        scope_spec=scope,
    )
    poem_ids = sorted(charter.poem_ids(records))
    (ws / "field" / "scope.json").write_text(
        json.dumps(asdict(scope), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ws / "field" / "charter.yml").write_text(
        "\n".join(
            [
                f"purpose: {charter.purpose}",
                f"corpus_snapshot: {charter.corpus_snapshot}",
                f"derived: {str(charter.derived).lower()}",
                f"version: {charter.version}",
                f"poem_count: {len(poem_ids)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {"study_id": args.study_id, "poem_count": len(poem_ids), "poem_ids": poem_ids}


def _object_add(args) -> dict:
    ws = _require_workspace(args)
    object_address = args.address or args.label
    if not args.anchor:
        raise CLIError("--anchor is required at least once (an object with no lexical anchor cannot be censused)")
    entry = {"id": object_address, "preferred_label": args.label, "anchors": args.anchor}
    path = _object_addresses_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"object_address": object_address, "label": args.label, "anchors": args.anchor}


def _assess(args) -> dict:
    ws = _require_workspace(args)
    if args.decision not in ("accepted", "rejected", "ambiguous"):
        raise CLIError("--decision must be one of accepted|rejected|ambiguous")
    assessment = OccurrenceAssessment(
        anchor_hit_poem_id=args.poem_id, object_address=args.object,
        decision=args.decision, rationale=args.rationale or "", assessor=args.assessor,
    )
    path = _occurrence_ledger_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(assessment), ensure_ascii=False) + "\n")
    return {
        "object_address": args.object, "poem_id": args.poem_id,
        "decision": args.decision, "assessor": args.assessor,
    }


def _calibrate(args) -> dict:
    ws = _require_workspace(args)
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    records_by_id = {r.poem_id: r for r in records}
    hits = run_census(records, _anchors_for(ws, args.object))
    sample = calibration_sample(hits, sample_size=args.sample, seed=args.seed)
    context = [open_context_ladder(h, records_by_id[h.poem_id].path) for h in sample]
    return {"object_address": args.object, "sample_size": len(sample), "context": context}


def _census(args) -> dict:
    ws = _require_workspace(args)
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    hits = run_census(records, _anchors_for(ws, args.object))
    if args.mode == "anchor":
        poems = sorted({h.poem_id for h in hits})
        return {"object_address": args.object, "mode": "anchor", "hit_count": len(hits), "poem_count": len(poems), "poems": poems}

    assessments = _load_assessments(ws, args.object)
    if not assessments:
        raise CLIError(
            f"no assessments recorded for object {args.object!r} -- "
            f"run 'ontograph assess' first, or use --mode anchor"
        )
    all_poem_ids = {r.poem_id for r in records}
    accepted = accepted_poem_ids(hits, assessments)
    ambiguous_only = ambiguous_only_poem_ids(hits, assessments)
    prevalence = assessed_full_prevalence(all_poem_ids, hits, assessments)
    return {
        "object_address": args.object, "mode": "assessed",
        "numerator": prevalence.numerator, "denominator": prevalence.denominator,
        "ambiguous_only_count": prevalence.ambiguous_only_count,
        "accepted_poems": sorted(accepted), "ambiguous_only_poems": sorted(ambiguous_only),
    }


def _map_recurrence(args) -> dict:
    if args.unit != "poem":
        raise CLIError(f"unsupported --unit {args.unit!r} in v0.1 (only 'poem' is implemented)")
    ws = _require_workspace(args)
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    hits = run_census(records, _anchors_for(ws, args.object))
    if args.mode == "anchor":
        poems_with_object = {h.poem_id for h in hits}
    else:
        poems_with_object = _accepted_or_raise(ws, args.object, hits)
    s = spread(poems_with_object, records)
    return {
        "object_address": args.object, "mode": args.mode, "unit": "poem",
        "distinct_poems": s.distinct_poems, "distinct_poets": s.distinct_poets,
        "total_poems": s.total_poems, "total_poets": s.total_poets,
    }


def _companions(args) -> dict:
    ws = _require_workspace(args)
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    hits_a = run_census(records, _anchors_for(ws, args.object))
    hits_b = run_census(records, _anchors_for(ws, args.with_))

    if args.mode == "anchor":
        result = typed_coincidence(hits_a, hits_b, mode=MODE_ANCHOR)
        poems_a = {h.poem_id for h in hits_a}
        poems_b = {h.poem_id for h in hits_b}
    else:
        accepted_a = _accepted_or_raise(ws, args.object, hits_a)
        accepted_b = _accepted_or_raise(ws, args.with_, hits_b)
        result = typed_coincidence(hits_a, hits_b, mode=MODE_ASSESSED, accepted_a=accepted_a, accepted_b=accepted_b)
        poems_a, poems_b = accepted_a, accepted_b

    out = {
        "object_address": args.object, "with": args.with_, "mode": args.mode, "scale": args.scale,
        "poem_scale": sorted(result.poem_scale),
        "couplet_scale": sorted(list(t) for t in result.couplet_scale),
    }
    try:
        lift_result = lift(poems_a, poems_b, field_size=len(records), minimum_support=args.min_support)
        out["lift"] = asdict(lift_result)
    except InsufficientSupportError as e:
        out["lift"] = None
        out["lift_note"] = str(e)
    return out


def _ablate(args) -> dict:
    ws = _require_workspace(args)
    if not args.remove.startswith("poet:"):
        raise CLIError("unsupported --remove spec in v0.1 (only 'poet:<slug>' is implemented)")
    if not args.rerun.startswith("relation:"):
        raise CLIError("unsupported --rerun spec in v0.1 (only 'relation:<addr-a>-<addr-b>' is implemented)")
    removed_slug = args.remove[len("poet:"):]
    addr_a, _, addr_b = args.rerun[len("relation:"):].partition("-")
    if not addr_a or not addr_b:
        raise CLIError("--rerun relation spec must be 'relation:<addr-a>-<addr-b>'")

    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    removed_poem_ids = {r.poem_id for r in records if r.poet_slug == removed_slug}
    hits_a = run_census(records, _anchors_for(ws, addr_a))
    hits_b = run_census(records, _anchors_for(ws, addr_b))

    if args.mode == "anchor":
        result = ablation_retention(hits_a, hits_b, MODE_ANCHOR, removed_poem_ids)
    else:
        accepted_a = _accepted_or_raise(ws, addr_a, hits_a)
        accepted_b = _accepted_or_raise(ws, addr_b, hits_b)
        result = ablation_retention(
            hits_a, hits_b, MODE_ASSESSED, removed_poem_ids,
            accepted_a=accepted_a, accepted_b=accepted_b,
        )
    return {"removed": args.remove, "relation": f"{addr_a}-{addr_b}", "mode": args.mode, **asdict(result)}


def _compare(args) -> dict:
    ws = _require_workspace(args)
    if len(args.fields) != 2:
        raise CLIError("--field must be given exactly twice: --field poet:X --field poet:Y")
    for f in args.fields:
        if not f.startswith("poet:"):
            raise CLIError("unsupported --field spec in v0.1 (only 'poet:<slug>' is implemented)")
    corpus_root = _resolve_corpus_root(args, ws)
    records = scan_corpus(corpus_root)
    hits = run_census(records, _anchors_for(ws, args.object))
    hit_poems = {h.poem_id for h in hits} if args.mode == "anchor" else _accepted_or_raise(ws, args.object, hits)
    field_a, field_b = args.fields
    slug_a, slug_b = field_a[len("poet:"):], field_b[len("poet:"):]
    poems_a = {r.poem_id for r in records if r.poet_slug == slug_a}
    poems_b = {r.poem_id for r in records if r.poet_slug == slug_b}
    result = compare_fields(hit_poems & poems_a, len(poems_a), hit_poems & poems_b, len(poems_b))
    return {"object_address": args.object, "mode": args.mode, "field_a": field_a, "field_b": field_b, **asdict(result)}


def _validate(args) -> dict:
    if not args.gates:
        raise CLIError("only --gates is implemented for 'validate' in v0.1")
    from dataclasses import asdict as _asdict
    from ontograph.validate import run_gates
    results = run_gates(args.repo_root, args.corpus_root, args.workspaces_dir)
    return {"gates": [_asdict(r) for r in results], "all_green": all(r.passed for r in results)}


def _release(args) -> dict:
    ws = _require_workspace(args)
    charter_path = ws / "field" / "charter.yml"
    field_charter = charter_path.read_text(encoding="utf-8") if charter_path.exists() else ""
    release = generate_release(
        ws, id=f"release-{args.version}", version=args.version,
        field_charter=field_charter, data_license_notice=DATA_LICENSE_NOTICE,
    )
    tag = release_as_git_tag(ws, args.version)
    return {"release_id": release.id, "version": release.version, "tag": tag}


# --- argument parsing ---

def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspaces-dir", default="ontograph-workspaces")
    common.add_argument("--json", action="store_true", help="pretty-print the result object")

    # Ledger row P9.1: --corpus-root is optional on every corpus-consuming
    # verb — an explicit flag overrides, otherwise the resolver falls back
    # to the root stored by `study new --corpus-root`, and raises a clean
    # CLIError when neither exists. `validate` consumes args.corpus_root
    # directly (run_gates), so an omitted root reaches it as None.
    with_corpus = argparse.ArgumentParser(add_help=False, parents=[common])
    with_corpus.add_argument("--corpus-root", required=False, default=None)

    parser = argparse.ArgumentParser(prog="ontograph", description="Deterministic Ganjoor Ontograph inquiry engine CLI.")
    top = parser.add_subparsers(dest="verb", required=True)

    study = top.add_parser("study").add_subparsers(dest="study_verb", required=True)
    p = study.add_parser("new", parents=[common]); p.add_argument("study_id")
    p.add_argument("--corpus-root", default=None)  # P9.1: optionally persist the corpus root for later verbs
    p.set_defaults(func=_study_new)

    field = top.add_parser("field").add_subparsers(dest="field_verb", required=True)
    p = field.add_parser("build", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--poet"); p.add_argument("--category"); p.set_defaults(func=_field_build)

    obj = top.add_parser("object").add_subparsers(dest="object_verb", required=True)
    p = obj.add_parser("add", parents=[common]); p.add_argument("study_id")
    p.add_argument("--label", required=True); p.add_argument("--address")
    p.add_argument("--anchor", action="append"); p.set_defaults(func=_object_add)

    p = top.add_parser("assess", parents=[common]); p.add_argument("study_id")
    p.add_argument("--object", required=True); p.add_argument("--poem-id", type=int, required=True)
    p.add_argument("--decision", required=True, choices=["accepted", "rejected", "ambiguous"])
    p.add_argument("--rationale", default=""); p.add_argument("--assessor", default="human")
    p.set_defaults(func=_assess)

    p = top.add_parser("calibrate", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True); p.add_argument("--sample", type=int, default=10)
    p.add_argument("--seed", type=int, default=0); p.set_defaults(func=_calibrate)

    p = top.add_parser("census", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True); p.add_argument("--mode", choices=["anchor", "assessed"], default="anchor")
    p.set_defaults(func=_census)

    map_ = top.add_parser("map").add_subparsers(dest="map_verb", required=True)
    p = map_.add_parser("recurrence", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True); p.add_argument("--unit", default="poem")
    p.add_argument("--mode", choices=["anchor", "assessed"], default="anchor")
    p.set_defaults(func=_map_recurrence)

    p = top.add_parser("companions", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True); p.add_argument("--with", dest="with_", required=True)
    p.add_argument("--scale", default="poem"); p.add_argument("--min-support", type=int, default=5)
    p.add_argument("--mode", choices=["anchor", "assessed"], default="anchor")
    p.set_defaults(func=_companions)

    p = top.add_parser("compare", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True)
    p.add_argument("--field", dest="fields", action="append", required=True)
    p.add_argument("--mode", choices=["anchor", "assessed"], default="anchor")
    p.set_defaults(func=_compare)

    p = top.add_parser("ablate", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--remove", required=True); p.add_argument("--rerun", required=True)
    p.add_argument("--mode", choices=["anchor", "assessed"], default="anchor")
    p.set_defaults(func=_ablate)

    p = top.add_parser("release", parents=[common]); p.add_argument("study_id")
    p.add_argument("--version", required=True); p.set_defaults(func=_release)

    p = top.add_parser("validate", parents=[with_corpus])
    p.add_argument("--gates", action="store_true"); p.add_argument("--repo-root", required=True)
    p.set_defaults(func=_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except CLIError as e:
        print(str(e), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
