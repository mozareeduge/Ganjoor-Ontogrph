"""Ledger row U03 (narrowed per Amendment §19.8): validated
ResearchSituation and Seed record schemas with append-only persistence
and a generic record route. NO `inquire` CLI yet (that is W02–W03).

Discriminating targets:

1. A valid ResearchSituation (schema_version, study_id, verbatim_hunch,
   normalized_display_hunch, language_observations, premature_decisions,
   status, actor) round-trips through append-only JSONL.
2. Invalid records are rejected BEFORE write: missing required field,
   bad status, empty hunch — no partial write ever lands.
3. Supersession: a situation may be superseded; the original stays.
4. Seeds validate (seed_id, situation_id, label, attributed_proposal,
   proposer, rationale) — attribution is mandatory (candidate-tier).
5. Records are stored candidate-tier: status can never be 'assessed' —
   an agent-authored record claiming assessed status is refused.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.records_v2 import (
    ResearchSituation,
    Seed,
    persist_situation,
    persist_seed,
    read_situations,
    read_seeds,
)


def _situation(**over) -> ResearchSituation:
    base = dict(
        study_id="s", verbatim_hunch="I keep noticing Rostam winning by cunning",
        normalized_display_hunch="I keep noticing Rostam winning by cunning",
        language_observations=["english"],
        premature_decisions=[], status="situational", actor="mz",
    )
    base.update(over)
    return ResearchSituation(**base)


def test_situation_round_trip(tmp_path: Path) -> None:
    sit = _situation()
    persist_situation(tmp_path, sit)
    loaded = read_situations(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].verbatim_hunch == sit.verbatim_hunch
    assert loaded[0].status == "situational"
    assert loaded[0].id.startswith("rs-")


def test_invalid_situation_refused_before_write(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        persist_situation(tmp_path, _situation(verbatim_hunch=""))
    with pytest.raises(ValueError):
        persist_situation(tmp_path, _situation(status="assessed"))
    with pytest.raises(ValueError):
        persist_situation(tmp_path, _situation(actor=""))
    assert read_situations(tmp_path) == [], "no partial write on refusal"


def test_situation_supersession_preserves_original(tmp_path: Path) -> None:
    first = _situation()
    persist_situation(tmp_path, first)
    second = _situation(status="superseded", supersedes=first.id)
    persist_situation(tmp_path, second)
    loaded = read_situations(tmp_path)
    assert len(loaded) == 2
    assert {s.status for s in loaded} == {"situational", "superseded"}


def test_seed_requires_attribution(tmp_path: Path) -> None:
    sit = _situation()
    persist_situation(tmp_path, sit)
    seed = Seed(
        seed_id="sd-1", situation_id=sit.id, label="cunning",
        attributed_proposal="Rostam's defeats of stronger foes via wit",
        proposer="agent:hermes", rationale="candidate-tier proposal",
    )
    persist_seed(tmp_path, seed)
    assert read_seeds(tmp_path)[0].label == "cunning"
    with pytest.raises(ValueError):
        Seed(
            seed_id="sd-2", situation_id=sit.id, label="x",
            attributed_proposal="y", proposer="", rationale="",
        )
