"""Amendment 20 F02: AssessorObject registry.

Discriminating targets (Plans.md F02 DoD):
1. Register 3 assessor objects, two sharing an independence_class.
2. The registry round-trips (write, reopen, list matches).
3. resolve_assessor() rejects an unregistered id.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.assessors import (
    AssessorObject,
    independence_classes_of,
    new_assessor_id,
    read_assessors,
    register_assessor,
    resolve_assessor,
)


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "study"
    ws.mkdir()
    return ws


def test_register_three_assessors_two_sharing_a_class(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    human = AssessorObject(
        id="as-mz", label="Mohammad Zare", assessor_type="human",
        apparatus="researcher, context ladder level 4",
        independence_class="human-mz",
    )
    agent_a = AssessorObject(
        id="as-triage-opus5-v1", label="Opus 5 triage v1", assessor_type="agent",
        apparatus="model=claude-opus-5; prompt=triage-v1; harness=claude-code",
        independence_class="apparatus-claude-opus5",
    )
    rule_from_agent_a = AssessorObject(
        id="as-rule-figurative-v1", label="figurative-context-stoplist v1",
        assessor_type="rule", apparatus="rule id=figurative-stoplist; version=1",
        independence_class="apparatus-claude-opus5",  # authored by agent_a -> shares its class
    )
    register_assessor(ws, human)
    register_assessor(ws, agent_a)
    register_assessor(ws, rule_from_agent_a)

    classes = independence_classes_of(ws, ["as-triage-opus5-v1", "as-rule-figurative-v1"])
    assert classes == {"apparatus-claude-opus5"}  # ONE class: they do not corroborate each other
    classes_incl_human = independence_classes_of(ws, ["as-mz", "as-triage-opus5-v1"])
    assert classes_incl_human == {"human-mz", "apparatus-claude-opus5"}


def test_registry_round_trips(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    a = AssessorObject(
        id="as-mz", label="Mohammad Zare", assessor_type="human",
        apparatus="researcher", independence_class="human-mz",
        conditions_of_validity="clean-git corpus only",
    )
    register_assessor(ws, a)

    reopened = read_assessors(ws)
    assert len(reopened) == 1
    assert reopened[0].id == "as-mz"
    assert reopened[0].conditions_of_validity == "clean-git corpus only"
    assert reopened[0].registered_at  # timestamp was stamped on write

    resolved = resolve_assessor(ws, "as-mz")
    assert resolved.label == "Mohammad Zare"


def test_resolve_unregistered_assessor_raises(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(
        id="as-mz", label="Mohammad Zare", assessor_type="human",
        apparatus="researcher", independence_class="human-mz",
    ))
    with pytest.raises(ValueError, match="not registered"):
        resolve_assessor(ws, "as-does-not-exist")


def test_duplicate_id_registration_refused(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    a = AssessorObject(
        id="as-mz", label="Mohammad Zare", assessor_type="human",
        apparatus="researcher", independence_class="human-mz",
    )
    register_assessor(ws, a)
    with pytest.raises(ValueError, match="already registered"):
        register_assessor(ws, a)


def test_assessor_requires_apparatus_and_independence_class() -> None:
    with pytest.raises(ValueError, match="apparatus"):
        AssessorObject(id="as-x", label="x", assessor_type="human", apparatus="", independence_class="c")
    with pytest.raises(ValueError, match="independence_class"):
        AssessorObject(id="as-x", label="x", assessor_type="human", apparatus="a", independence_class="")


def test_new_assessor_id_is_slugged_and_unique() -> None:
    id1 = new_assessor_id("Mohammad Zare")
    id2 = new_assessor_id("Mohammad Zare")
    assert id1.startswith("as-mohammad-zare-")
    assert id1 != id2  # distinct uuid suffix each call


def test_cli_assessor_add_and_list(tmp_path: Path, capsys) -> None:
    from ontograph.cli import main

    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "f02-cli"
    code = main(["study", "new", study_id, "--corpus-root", ".", "--workspaces-dir", ws_dir])
    assert code == 0

    code = main([
        "assessor", "add", study_id,
        "--id", "as-mz", "--label", "Mohammad Zare", "--type", "human",
        "--apparatus", "researcher", "--independence-class", "human-mz",
        "--workspaces-dir", ws_dir, "--json",
    ])
    captured = capsys.readouterr()
    assert code == 0, captured.err

    code = main(["assessor", "list", study_id, "--workspaces-dir", ws_dir, "--json"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    import json as _json
    result = _json.loads(captured.out)
    assert result["count"] == 1
    assert result["assessors"][0]["id"] == "as-mz"
