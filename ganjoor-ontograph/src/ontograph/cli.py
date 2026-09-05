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
from ontograph.anchors import LexicalAnchor
from ontograph.census import (
    OccurrenceAssessment,
    accepted_poem_ids,
    ambiguous_only_poem_ids,
    assessed_full_prevalence,
    calibration_sample,
    open_context_ladder,
)
from ontograph.compare import MODE_ANCHOR, MODE_ASSESSED, InsufficientSupportError, compare_fields, lift, typed_coincidence
from ontograph.field import FieldCharter, ScopeSpec, all_poems, poet, scope_from_dict
from ontograph.index_cache import (
    census_from_index,
    get_or_build_index,
    records_from_index,
)
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


def _open_cached_index(args, ws: Path):
    """Ledger row P9.3: every corpus verb serves its records and census
    hits from the corpus-root-keyed index cache (P9.2, built once via the
    proven `corpus.build_index()`) instead of a full `scan_corpus()` +
    re-parse/re-tokenize per invocation. The connection is read-only; the
    caller closes it (`conn.close()`) before returning."""
    corpus_root = _resolve_corpus_root(args, ws)
    conn, _manifest, _cache_hit = get_or_build_index(corpus_root)
    records = records_from_index(conn)
    return conn, records


def _scope_allowed(ws: Path, records: list) -> set[int] | None:
    """Ledger row P9.4: `field/scope.json` — written by `field build` since
    P5.1 but never read again — becomes a real filter. When the study has
    a stored scope, the other verbs intersect their own query with it: the
    returned poem-id set is the study's field, and hits/populations
    outside it do not exist for this study (spec §7: constructing the
    Object-Field is the first methodological step, not a write-only
    artifact). No scope.json (studies built before any `field build`) →
    None, no filtering — P9.1's stored-corpus flow is unaffected."""
    path = ws / "field" / "scope.json"
    if not path.exists():
        return None
    scope = scope_from_dict(json.loads(path.read_text(encoding="utf-8")))
    return scope.resolve(records)


def _accepted_or_raise(ws: Path, object_address: str, hits) -> set[int]:
    assessments = _load_assessments(ws, object_address)
    if not assessments:
        raise CLIError(
            f"no assessments recorded for object {object_address!r} -- "
            f"run 'ontograph assess' first, or use --mode anchor"
        )
    return accepted_poem_ids(hits, assessments)


# --- verb implementations, each returning a plain JSON-serializable dict ---

def _study_status(args) -> dict:
    """Ledger row U01: report the study chain + the one legal next action."""
    from ontograph.status import assess_study_state
    ws = _require_workspace(args)
    return {"study_id": args.study_id, **assess_study_state(ws)}


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
    conn, records = _open_cached_index(args, ws)
    try:
        scope: ScopeSpec = poet(args.poet) if args.poet else all_poems()
        charter = FieldCharter(
            purpose=f"field for study {args.study_id}",
            corpus_snapshot=str(corpus_root),
            scope_spec=scope,
        )
        poem_ids = sorted(charter.poem_ids(records))
    finally:
        conn.close()
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


def _workspace_is_governed(ws: Path) -> bool:
    """W06 (Amendment §19.2): a workspace with inquiry history is GOVERNED —
    object promotion must cite a human review or confirmation receipt."""
    return (ws / "research" / "inquiry-catalogs.jsonl").exists()


def _object_add(args) -> dict:
    ws = _require_workspace(args)
    object_address = args.address or args.label
    if not args.anchor:
        raise CLIError("--anchor is required at least once (an object with no lexical anchor cannot be censused)")
    # W06 direct-route guard: governed workspaces require a human receipt
    if _workspace_is_governed(ws):
        review_id = getattr(args, "review_id", None)
        conf_file = getattr(args, "confirmation_file", None)
        if not review_id and not conf_file:
            raise CLIError(
                "governed workspace: direct object add requires --review-id <inquiry-review-id> "
                "or --confirmation-file <human confirmation json> (Amendment §19.2 — "
                "agent sessions cannot bypass human review)"
            )
        if conf_file:
            conf = json.loads(Path(conf_file).read_text(encoding="utf-8"))
            for f in ("human_actor", "receipt", "object_id", "rationale"):
                if not conf.get(f):
                    raise CLIError(f"confirmation file missing field: {f}")
            if conf.get("object_id") != object_address:
                raise CLIError(
                    f"confirmation file names object {conf.get('object_id')!r}, "
                    f"but this add targets {object_address!r}"
                )
    entry = {"id": object_address, "preferred_label": args.label, "anchors": args.anchor}
    if getattr(args, "review_id", None):
        entry["promoted_via_review"] = args.review_id
    if getattr(args, "confirmation_file", None):
        conf = json.loads(Path(args.confirmation_file).read_text(encoding="utf-8"))
        entry["human_confirmation"] = {"actor": conf["human_actor"], "receipt": conf["receipt"]}
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


from ontograph.walk import run_walk


def _walk(args) -> dict:
    ws = _require_workspace(args)
    corpus_root = _resolve_corpus_root(args, ws)
    return run_walk(
        ws=ws, study_id=args.study_id, object_address=args.object,
        corpus_root=corpus_root, sample_size=args.sample, seed=args.seed,
        script_path=args.script, assessor=args.assessor,
    )


def _calibrate(args) -> dict:
    ws = _require_workspace(args)
    conn, records = _open_cached_index(args, ws)
    try:
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            records = [r for r in records if r.poem_id in allowed]
        hits = census_from_index(conn, records, _anchors_for(ws, args.object))
        if allowed is not None:
            hits = [h for h in hits if h.poem_id in allowed]
        records_by_id = {r.poem_id: r for r in records}
        sample = calibration_sample(hits, sample_size=args.sample, seed=args.seed)
        context = [open_context_ladder(h, records_by_id[h.poem_id].path) for h in sample]
    finally:
        conn.close()
    return {"object_address": args.object, "sample_size": len(sample), "context": context}


def _census(args) -> dict:
    ws = _require_workspace(args)
    conn, records = _open_cached_index(args, ws)
    try:
        hits = census_from_index(conn, records, _anchors_for(ws, args.object))
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            records = [r for r in records if r.poem_id in allowed]
            hits = [h for h in hits if h.poem_id in allowed]
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
    finally:
        conn.close()
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
    conn, records = _open_cached_index(args, ws)
    try:
        hits = census_from_index(conn, records, _anchors_for(ws, args.object))
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            records = [r for r in records if r.poem_id in allowed]
            hits = [h for h in hits if h.poem_id in allowed]
        if args.mode == "anchor":
            poems_with_object = {h.poem_id for h in hits}
        else:
            poems_with_object = _accepted_or_raise(ws, args.object, hits)
        s = spread(poems_with_object, records)
    finally:
        conn.close()
    return {
        "object_address": args.object, "mode": args.mode, "unit": "poem",
        "distinct_poems": s.distinct_poems, "distinct_poets": s.distinct_poets,
        "total_poems": s.total_poems, "total_poets": s.total_poets,
    }


def _companions(args) -> dict:
    ws = _require_workspace(args)
    conn, records = _open_cached_index(args, ws)
    try:
        hits_a = census_from_index(conn, records, _anchors_for(ws, args.object))
        hits_b = census_from_index(conn, records, _anchors_for(ws, args.with_))
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            records = [r for r in records if r.poem_id in allowed]
            hits_a = [h for h in hits_a if h.poem_id in allowed]
            hits_b = [h for h in hits_b if h.poem_id in allowed]

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
    finally:
        conn.close()
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

    conn, records = _open_cached_index(args, ws)
    try:
        removed_poem_ids = {r.poem_id for r in records if r.poet_slug == removed_slug}
        hits_a = census_from_index(conn, records, _anchors_for(ws, addr_a))
        hits_b = census_from_index(conn, records, _anchors_for(ws, addr_b))
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            removed_poem_ids &= allowed
            records = [r for r in records if r.poem_id in allowed]
            hits_a = [h for h in hits_a if h.poem_id in allowed]
            hits_b = [h for h in hits_b if h.poem_id in allowed]

        if args.mode == "anchor":
            result = ablation_retention(hits_a, hits_b, MODE_ANCHOR, removed_poem_ids)
        else:
            accepted_a = _accepted_or_raise(ws, addr_a, hits_a)
            accepted_b = _accepted_or_raise(ws, addr_b, hits_b)
            result = ablation_retention(
                hits_a, hits_b, MODE_ASSESSED, removed_poem_ids,
                accepted_a=accepted_a, accepted_b=accepted_b,
            )
    finally:
        conn.close()
    return {"removed": args.remove, "relation": f"{addr_a}-{addr_b}", "mode": args.mode, **asdict(result)}


def _compare(args) -> dict:
    ws = _require_workspace(args)
    if len(args.fields) != 2:
        raise CLIError("--field must be given exactly twice: --field poet:X --field poet:Y")
    for f in args.fields:
        if not f.startswith("poet:"):
            raise CLIError("unsupported --field spec in v0.1 (only 'poet:<slug>' is implemented)")
    conn, records = _open_cached_index(args, ws)
    try:
        hits = census_from_index(conn, records, _anchors_for(ws, args.object))
        allowed = _scope_allowed(ws, records)
        if allowed is not None:
            records = [r for r in records if r.poem_id in allowed]
            hits = [h for h in hits if h.poem_id in allowed]
        hit_poems = {h.poem_id for h in hits} if args.mode == "anchor" else _accepted_or_raise(ws, args.object, hits)
        field_a, field_b = args.fields
        slug_a, slug_b = field_a[len("poet:"):], field_b[len("poet:"):]
        poems_a = {r.poem_id for r in records if r.poet_slug == slug_a}
        poems_b = {r.poem_id for r in records if r.poet_slug == slug_b}
        result = compare_fields(hit_poems & poems_a, len(poems_a), hit_poems & poems_b, len(poems_b))
    finally:
        conn.close()
    return {"object_address": args.object, "mode": args.mode, "field_a": field_a, "field_b": field_b, **asdict(result)}


def _validate(args) -> dict:
    if not args.gates:
        raise CLIError("only --gates is implemented for 'validate' in v0.1")
    from dataclasses import asdict as _asdict
    from ontograph.validate import run_gates
    results = run_gates(args.repo_root, args.corpus_root, args.workspaces_dir)
    return {"gates": [_asdict(r) for r in results], "all_green": all(r.passed for r in results)}


def _inquire(args) -> dict:
    """W03/W04B: `inquire` — create (hunch+proposals) or --refresh
    (corpus-verify an existing catalog, appending a superseding one).
    Amendment §19.4: create/refresh are mutually exclusive; both persist
    atomically; both emit the exact next command."""
    import json as _json

    from ontograph.workspace import read_study_config

    ws = _require_workspace(args)
    config = read_study_config(ws)

    if args.refresh_catalog_id:
        return _inquire_refresh(ws, config, args)
    if getattr(args, "review", None):
        return _inquire_review_cli(ws, config, args)
    if not args.hunch or not args.actor:
        raise CLIError("inquire requires --hunch and --actor (or --refresh <catalog-id>)")
    return _inquire_create(ws, config, args)


def _inquire_review_cli(ws, config, args) -> dict:
    """W06: the REVIEW form — apply a decisions file through W05's
    atomic promotion service, report promoted/rejected/deferred, and
    emit the next walk command for each promoted object."""
    from ontograph.inquiry_review import apply_review_decisions

    rpath = Path(args.review)
    if not rpath.exists():
        raise CLIError(f"decisions file not found: {args.review}")
    try:
        decisions = json.loads(rpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        import yaml

        decisions = yaml.safe_load(rpath.read_text(encoding="utf-8"))
    if not isinstance(decisions, list):
        raise CLIError("decisions file must be a list of {candidate_id, decision, rationale}")
    situation = getattr(args, "situation", None)
    if not situation:
        raise CLIError("--situation is required for --review")
    actor = getattr(args, "review_actor", None)
    if not actor:
        raise CLIError("--review-actor is required for --review (must be the human reviewer)")
    receipt = getattr(args, "receipt", None)
    if not receipt:
        raise CLIError("--receipt is required for --review")

    result = apply_review_decisions(ws, _catalog_for(ws, situation), situation,
                                    actor, receipt, decisions)
    result["next_walk_command"] = (
        f"ontograph walk <study> --object {result['promoted'][0]}"
        if result["promoted"] else None
    )
    return result


def _catalog_for(ws: Path, situation_id: str) -> str:
    """Resolve the active catalog for a situation: the latest non-superseded
    one. Refusal when none exists (never guessed)."""
    from ontograph.inquiry import read_catalogs

    catalogs = [c for c in read_catalogs(ws) if c.situation_id == situation_id]
    if not catalogs:
        raise CLIError(f"no catalog found for situation {situation_id!r}")
    superseded = {c.supersedes for c in catalogs if c.supersedes}
    live = [c for c in catalogs if c.id not in superseded]
    return live[-1].id


def _inquire_refresh(ws, config, args) -> dict:
    """W04B: verify an existing catalog's lexical candidates against the
    pinned corpus and append a SUPERSEDING catalog with real support
    statuses + located evidence. The original is never rewritten."""
    import sqlite3

    from ontograph.corpus import corpus_snapshot, build_index
    from ontograph.inquiry import (
        CandidateEvidenceRef, InquiryCandidate, InquiryCatalog,
        persist_catalog, read_catalogs,
    )

    root = config.get("corpus_root")
    if not root:
        raise CLIError("study has no stored corpus_root (study new --corpus-root)")
    catalogs = read_catalogs(ws)
    original = next((c for c in catalogs if c.id == args.refresh_catalog_id), None)
    if original is None:
        raise CLIError(f"unknown catalog id: {args.refresh_catalog_id}")

    snap = corpus_snapshot(root)
    if original.corpus_snapshot_id != snap.snapshot_id:
        raise CLIError(
            f"catalog {original.id} was built against snapshot "
            f"{original.corpus_snapshot_id}; corpus is now {snap.snapshot_id} — "
            "stale receipts are never silently refreshed against a different corpus"
        )

    db = Path(root) / "ontograph-support-idx.sqlite"
    if not db.exists():
        build_index(root, db)
    conn = sqlite3.connect(db)
    try:
        from ontograph.inquiry_support import compute_support

        new_candidates = []
        for c in original.candidates:
            if c.kind in ("non-object-note",):
                new_candidates.append(c)  # not-applicable kind passes through
                continue
            if not _is_persian_form(c.form):
                new_candidates.append(InquiryCandidate(
                    candidate_id=c.candidate_id, kind=c.kind, form=c.form,
                    proposer_type=c.proposer_type, proposer_id=c.proposer_id,
                    rationale=c.rationale, support_status="not-applicable",
                ))
                continue
            mode = "phrase" if " " in c.form else "exact"
            support = compute_support(conn, Path(root), snap.snapshot_id,
                                      form=c.form, match_mode=mode)
            new_candidates.append(InquiryCandidate(
                candidate_id=c.candidate_id, kind=c.kind, form=c.form,
                proposer_type=c.proposer_type, proposer_id=c.proposer_id,
                rationale=c.rationale,
                support_status=support["support_status"],
                hit_count=support["hit_count"],
                poem_count=support["poem_count"],
                poet_count=support["poet_count"],
                evidence=[CandidateEvidenceRef(**e) for e in support["evidence"]],
            ))
    finally:
        conn.close()

    superseding = InquiryCatalog(
        study_id=original.study_id, situation_id=original.situation_id,
        corpus_snapshot_id=snap.snapshot_id, field_id=original.field_id,
        scope_spec=original.scope_spec, parameters=original.parameters,
        limitations=original.limitations, candidates=new_candidates,
        supersedes=original.id,
    )
    persist_catalog(ws, superseding)

    supported = [c for c in new_candidates if c.support_status == "supported"]
    return {
        "catalog_id": superseding.id,
        "supersedes": original.id,
        "verified": len(supported),
        "unsupported": sum(1 for c in new_candidates if c.support_status == "unsupported"),
        "review_template": {
            "schema_version": "1.0",
            "catalog_id": superseding.id,
            "decisions": [
                {"candidate_id": c.candidate_id, "decision": "", "rationale": ""}
                for c in new_candidates if c.support_status == "supported"
            ],
        },
        "next_command": (
            f"ontograph inquire <study> --review <decisions.json> "
            f"(human review of catalog {superseding.id})"
        ),
    }


def _is_persian_form(form: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in form)


def _inquire_create(ws, config, args) -> dict:
    """W03: the CREATE form — one ResearchSituation + one candidate
    InquiryCatalog, atomically, with review template + next command."""
    import json as _json

    from ontograph.corpus import corpus_snapshot
    from ontograph.inquiry import InquiryCatalog, persist_catalog
    from ontograph.inquiry_parse import parse_hunch, parse_proposal
    from ontograph.records_v2 import ResearchSituation, persist_situation

    parsed = parse_hunch(args.hunch, persian_forms=list(args.persian_form or []))
    proposal_dicts: list[dict] = []
    for raw in args.proposal or []:
        try:
            proposal_dicts.append(_json.loads(raw))
        except _json.JSONDecodeError as e:
            raise CLIError(f"invalid --proposal JSON: {e}")
    if args.file:
        fpath = Path(args.file)
        if not fpath.exists():
            raise CLIError(f"proposals file not found: {args.file}")
        text = fpath.read_text(encoding="utf-8")
        try:
            loaded = _json.loads(text)
        except _json.JSONDecodeError:
            import yaml

            loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            loaded = [loaded]
        if not isinstance(loaded, list):
            raise CLIError("proposals file must be a list or single proposal")
        proposal_dicts.extend(loaded)

    # parse + validate ALL proposals BEFORE any write (atomicity)
    try:
        candidates = [parse_proposal(p) for p in proposal_dicts]
        situation = ResearchSituation(
            study_id=config.get("study_id", ws.name),
            verbatim_hunch=parsed["verbatim_hunch"],
            normalized_display_hunch=parsed["normalized_display_hunch"],
            language_observations=parsed["language_observations"],
            premature_decisions=[],
            status="situational",
            actor=args.actor,
        )
        snap = corpus_snapshot(config.get("corpus_root", ".")) if config.get("corpus_root") else None
        # W03: supplied --persian-form values become lexical-anchor
        # candidates attributed to the researcher (candidate-tier,
        # unsupported until W04B verifies them against the corpus)
        from ontograph.inquiry import InquiryCandidate as _IC

        for form in parsed["persian_forms"]:
            candidates.append(_IC(
                candidate_id=f"cand-{abs(hash(form)) % 10**12:012d}",
                kind="lexical-anchor", form=form,
                proposer_type="human", proposer_id=args.actor,
                rationale="supplied with the hunch via --persian-form",
                support_status="unsupported",
            ))
        catalog = InquiryCatalog(
            study_id=situation.study_id,
            situation_id=situation.id,
            corpus_snapshot_id=snap.snapshot_id if snap else "cs1-none",
            field_id="field-unbuilt",
            scope_spec={"kind": "all"},
            parameters={"parser": "w02", "probes": []},
            limitations=["raw retrieval order only", "candidates are unverified proposals"],
            candidates=candidates,
        )
    except ValueError as e:
        raise CLIError(str(e))  # nothing written: validation precedes persistence

    persist_situation(ws, situation)
    persist_catalog(ws, catalog)

    needs_vocab = parsed["needs_vocabulary"]
    next_command = (
        "ontograph inquire <study> --file <proposals.yaml> (supply attributed Persian candidates)"
        if needs_vocab
        else f"ontograph inquire {ws.name} --refresh pending (W04 wires corpus verification)"
    )
    return {
        "situation_id": situation.id,
        "catalog_id": catalog.id,
        "candidates": [c.candidate_id for c in candidates],
        "needs_vocabulary": needs_vocab,
        "vocabulary_hint": "supplied attributed candidates" if needs_vocab else None,
        "review_template": {
            "schema_version": "1.0",
            "catalog_id": catalog.id,
            "decisions": [
                {"candidate_id": c.candidate_id, "decision": "", "rationale": ""}
                for c in candidates
            ],
        },
        "next_command": next_command,
    }


def _release(args) -> dict:
    ws = _require_workspace(args)
    charter_path = ws / "field" / "charter.yml"
    field_charter = charter_path.read_text(encoding="utf-8") if charter_path.exists() else ""
    release = generate_release(
        ws, id=f"release-{args.version}", version=args.version,
        field_charter=field_charter, data_license_notice=DATA_LICENSE_NOTICE,
    )
    tag = release_as_git_tag(ws, args.version)
    # Ledger row P9.8: every release renders report.md + report.html by
    # default (the researcher's binding format decision); other formats
    # only on explicit request, so none are offered here.
    from ontograph.report import render_release_reports

    rendered = render_release_reports(ws, args.version)
    return {"release_id": release.id, "version": release.version, "tag": tag,
            "report_markdown": rendered["markdown"], "report_html": rendered["html"]}


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
    p = study.add_parser("status", parents=[common]); p.add_argument("study_id")
    p.set_defaults(func=_study_status)

    field = top.add_parser("field").add_subparsers(dest="field_verb", required=True)
    p = field.add_parser("build", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--poet"); p.add_argument("--category"); p.set_defaults(func=_field_build)

    obj = top.add_parser("object").add_subparsers(dest="object_verb", required=True)
    p = obj.add_parser("add", parents=[common]); p.add_argument("study_id")
    p.add_argument("--address"); p.add_argument("--label", required=True)
    p.add_argument("--anchor", action="append"); p.set_defaults(func=_object_add)
    p.add_argument("--review-id")  # W06: citation of a human inquiry review
    p.add_argument("--confirmation-file")  # W06: direct human confirmation receipt

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

    # Ledger row P9.5: the guided calibration/assessment flow. Scripted
    # (--script JSON) or interactive TTY; never a silent non-interactive run.
    p = top.add_parser("walk", parents=[with_corpus]); p.add_argument("study_id")
    p.add_argument("--object", required=True)
    p.add_argument("--sample", type=int, default=30)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--script"); p.add_argument("--assessor", default="human")
    p.set_defaults(func=_walk)

    p = top.add_parser("validate", parents=[with_corpus])
    p.add_argument("--gates", action="store_true"); p.add_argument("--repo-root", required=True)
    p.set_defaults(func=_validate)

    # W03: inquiry intake — create form (Amendment §19.4)
    inq = top.add_parser("inquire", parents=[common])
    inq.add_argument("study_id")
    inq.add_argument("--hunch")
    inq.add_argument("--actor")
    inq.add_argument("--file")  # optional proposals file (YAML/JSON list)
    inq.add_argument("--proposal", action="append", default=[])  # inline JSON proposals
    inq.add_argument("--persian-form", action="append", default=[])
    inq.add_argument("--refresh", dest="refresh_catalog_id")  # W04B: verify an existing catalog
    inq.add_argument("--review")  # W06: decisions file for human review
    inq.add_argument("--situation")  # W06: situation for --review
    inq.add_argument("--review-actor")  # W06: human reviewer id
    inq.add_argument("--receipt")  # W06: human confirmation receipt id
    inq.set_defaults(func=_inquire)

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
