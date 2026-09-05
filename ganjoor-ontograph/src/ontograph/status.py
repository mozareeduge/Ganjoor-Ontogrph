"""Ledger row U01 (Amendment 19.8/19.9): study status and legal next actions.

Reads STORED workspace state only -- situations, live catalogs, reviews,
objects, occurrence ledger, operations, findings -- never the corpus index,
so it stays fast on the real corpus. Coverage questions belong to
census --mode assessed (T06 enforcement); status reports the
situation to catalog/review to object to operation to finding to release
chain and the one legal next action per the 19.9 decision table.
First match wins; every branch names its suggestion and the move it refuses.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_jsonl(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _live_catalogs(catalogs):
    superseded = {c.get('supersedes') for c in catalogs if c.get('supersedes')}
    return [c for c in catalogs if c.get('id') not in superseded]


def assess_study_state(ws):
    """Return state/suggestion/forbidden/chain for a study workspace."""
    ws = Path(ws)
    situations = _read_jsonl(ws / 'research' / 'research-situations.jsonl')
    catalogs = _read_jsonl(ws / 'research' / 'inquiry-catalogs.jsonl')
    reviews = _read_jsonl(ws / 'research' / 'inquiry-reviews.jsonl')
    objects = _read_jsonl(ws / 'objects' / 'object-addresses.jsonl')
    assessments = _read_jsonl(ws / 'corpus' / 'occurrence-ledger.jsonl')
    operations = _read_jsonl(ws / 'corpus' / 'operations.jsonl')
    findings = _read_jsonl(ws / 'research' / 'findings.jsonl')

    active = [s for s in situations if s.get('status') == 'situational']
    if active:
        sid = active[-1].get('id')
        live = _live_catalogs([c for c in catalogs if c.get('situation_id') == sid])
    else:
        live = []

    chain = {
        'situations': len(active),
        'live_catalogs': len(live),
        'reviews': len(reviews),
        'objects': len(objects),
        'assessed_objects': len({a.get('object_address') for a in assessments}),
        'operations': len(operations),
        'findings': len(findings),
    }

    governed_ops = [o for o in operations if o.get('situation_id')]
    if operations and not governed_ops and not findings:
        return {
            'state': 'legacy-unframed',
            'suggestion': ("operations predate governed inquiry -- run "
                           "'ontograph inquire <study> --hunch ...' and rerun them "
                           "inside the governed flow"),
            'forbidden': 'higher-record/release support',
            'chain': chain,
        }
    if not active:
        return {
            'state': 'no-situation',
            'suggestion': ("no research situation on record -- run "
                           "'ontograph inquire <study> --hunch ...' to open one"),
            'forbidden': 'field/object promotion or analysis',
            'chain': chain,
        }
    if not live:
        return {
            'state': 'intake-incomplete',
            'suggestion': ("situation recorded but no live catalog -- re-run "
                           "'ontograph inquire <study> --hunch ...' to complete intake"),
            'forbidden': 'field/object promotion or analysis',
            'chain': chain,
        }
    live_ids = {c.get('id') for c in live}
    live_cands = [cd for c in live for cd in (c.get('candidates') or [])]
    ordinary = [cd for cd in live_cands
                if cd.get('kind') in ('seed-object', 'lexical-anchor', 'lexical-neighbor')]
    if not any(cd.get('form') for cd in live_cands):
        return {
            'state': 'no-vocabulary',
            'suggestion': ("no Persian forms on record -- supply attributed candidates "
                           "via 'ontograph inquire <study> --file <proposals.yaml>'; "
                           "the runtime never translates on its own"),
            'forbidden': 'invented translation',
            'chain': chain,
        }
    if ordinary and all(c.get('supersedes') is None for c in live):
        return {
            'state': 'unverified-candidates',
            'suggestion': ("candidates never verified against the corpus -- run "
                           "'ontograph inquire <study> --refresh <catalog-id>' first"),
            'forbidden': 'promotion',
            'chain': chain,
        }
    if any(r.get('catalog_id') not in live_ids for r in reviews):
        return {
            'state': 'stale-review',
            'suggestion': ("decisions point at a superseded catalog -- run "
                           "'ontograph inquire <study> --refresh <catalog-id>' and re-review"),
            'forbidden': 'promotion',
            'chain': chain,
        }
    reviewed = {r.get('candidate_id') for r in reviews
                if r.get('catalog_id') in live_ids}
    if ordinary and any(cd.get('candidate_id') not in reviewed for cd in ordinary):
        return {
            'state': 'pending-review',
            'suggestion': ("candidates await human review -- run "
                           "'ontograph inquire <study> --review <decisions.json>'"),
            'forbidden': 'agent/automatic promotion',
            'chain': chain,
        }
    if objects and not governed_ops:
        return {
            'state': 'assess-objects',
            'suggestion': ("walk the object: 'ontograph walk <study> --object <addr> "
                           "--sample 30' (or rule/estimate); an anchor census first "
                           "reveals hits versus a lexical negative to revise or preserve"),
            'forbidden': 'assessed-full/catalog cell',
            'chain': chain,
        }
    if governed_ops and not findings:
        return {
            'state': 'operation-no-finding',
            'suggestion': ("return each consequential result to its source passages "
                           "(U02 source show), then inspect/retain a Finding or Trace; "
                           "the renderer never argues for you"),
            'forbidden': 'automatic argument',
            'chain': chain,
        }
    if findings:
        return {
            'state': 'releaseable',
            'suggestion': ("release the current state ('ontograph release <study> "
                           "--version ...'), continue, or reopen -- a release stays revisable"),
            'forbidden': 'finality claim',
            'chain': chain,
        }
    return {
        'state': 'no-situation',
        'suggestion': "run 'ontograph inquire <study> --hunch ...' to open a situation",
        'forbidden': 'field/object promotion or analysis',
        'chain': chain,
    }
