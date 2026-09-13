"""Amendment 20 F05: ResolutionPolicy + resolve()/policy_ablation()/
contested_share().

Discriminating targets (Plans.md F05 DoD, and the F14 "divergence
fixture" this file doubles as the source of): two assessors positioning
the SAME hits with DIFFERING stances, such that concordance,
named-assessor(A), and named-assessor(B) produce THREE DIFFERENT
numbers. If they do not diverge, the fixture proves nothing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontograph.assessors import AssessorObject, register_assessor
from ontograph.positions import active_positions, position_for
from ontograph.resolution import ResolutionPolicy, declare_policy, new_policy_id, policy_ablation, resolve

OBJ = "mirror"


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "study"
    ws.mkdir()
    return ws


def _register(ws, aid, itype, iclass):
    register_assessor(ws, AssessorObject(id=aid, label=aid, assessor_type=itype, apparatus="x", independence_class=iclass))


def _two_assessor_divergence_fixture(ws: Path):
    """6 hits, deliberately asymmetric so A's occurs-count, B's
    occurs-count, and their concordance occurs-count are three DIFFERENT
    numbers (4, 2, 1) rather than three policies coincidentally landing on
    the same figure. A symmetric fixture (e.g. A unanimous "occurs")
    proves nothing, because concordance degenerates to exactly B's count
    whenever A never disagrees -- this shape avoids that."""
    _register(ws, "as-a", "human", "human-a")
    _register(ws, "as-b", "agent", "apparatus-b")
    hits = ["ah1-1", "ah1-2", "ah1-3", "ah1-4", "ah1-5", "ah1-6"]
    stances = {
        "ah1-1": ("occurs", "occurs"),            # concordant occurs
        "ah1-2": ("occurs", "does-not-occur"),    # contested
        "ah1-3": ("occurs", "does-not-occur"),    # contested
        "ah1-4": ("occurs", "does-not-occur"),    # contested
        "ah1-5": ("does-not-occur", "occurs"),    # contested
        "ah1-6": ("does-not-occur", "does-not-occur"),  # concordant does-not-occur
    }
    for hit_id, (a_stance, b_stance) in stances.items():
        position_for(ws, hit_id, OBJ, "as-a", a_stance)
        position_for(ws, hit_id, OBJ, "as-b", b_stance)
    return hits


def test_divergence_fixture_yields_three_different_numbers(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = _two_assessor_divergence_fixture(ws)

    concordance = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance")
    named_a = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="named-assessor", assessor_object_id="as-a")
    named_b = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="named-assessor", assessor_object_id="as-b")

    def occurs_count(policy):
        count = 0
        all_positions = _all_positions(ws)
        for hit_id in hits:
            active = active_positions(all_positions, hit_id, OBJ)
            if resolve(ws, active, policy) == "occurs":
                count += 1
        return count

    n_concordance = occurs_count(concordance)
    n_a = occurs_count(named_a)
    n_b = occurs_count(named_b)

    assert n_a == 4  # A says occurs on hits 1,2,3,4
    assert n_b == 2  # B says occurs on hits 1,5
    assert n_concordance == 1  # unanimous "occurs" only on hit 1
    assert len({n_concordance, n_a, n_b}) == 3  # three DIFFERENT numbers -- the fixture discriminates


def _all_positions(ws):
    from ontograph.positions import read_positions

    return read_positions(ws)


def test_concordance_contested_hit_excluded_by_default(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _two_assessor_divergence_fixture(ws)
    policy = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance")
    active = active_positions(_all_positions(ws), "ah1-3", OBJ)
    assert resolve(ws, active, policy) is None  # excluded-and-reported (default)


def test_concordance_contested_hit_counted_as_undecidable_when_declared(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _two_assessor_divergence_fixture(ws)
    policy = ResolutionPolicy(
        id=new_policy_id(), object_address_id=OBJ, kind="concordance",
        contested_handling="counted-as-undecidable",
    )
    active = active_positions(_all_positions(ws), "ah1-3", OBJ)
    assert resolve(ws, active, policy) == "undecidable"


def test_kind_none_never_resolves(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _two_assessor_divergence_fixture(ws)
    policy = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="none")
    for hit_id in ["ah1-1", "ah1-2", "ah1-3"]:
        active = active_positions(_all_positions(ws), hit_id, OBJ)
        assert resolve(ws, active, policy) is None


def test_min_weight_for_inclusion_excludes_low_weight_non_human(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-mz", "human", "human-mz")
    _register(ws, "as-agent", "agent", "apparatus-x")
    position_for(ws, "ah1-1", OBJ, "as-mz", "does-not-occur")
    position_for(ws, "ah1-1", OBJ, "as-agent", "occurs", weight=0.3)  # below the floor

    policy = ResolutionPolicy(
        id=new_policy_id(), object_address_id=OBJ, kind="named-assessor",
        assessor_object_id="as-agent", min_weight_for_inclusion=0.6,
    )
    active = active_positions(_all_positions(ws), "ah1-1", OBJ)
    # the agent's low-weight position is excluded from THIS policy's resolution
    assert resolve(ws, active, policy) is None

    # a human position is NEVER excluded by min_weight_for_inclusion, regardless of weight
    policy_human = ResolutionPolicy(
        id=new_policy_id(), object_address_id=OBJ, kind="named-assessor",
        assessor_object_id="as-mz", min_weight_for_inclusion=0.99,
    )
    assert resolve(ws, active, policy_human) == "does-not-occur"


def test_undeclared_contestation_threshold_behaves_as_zero() -> None:
    p = ResolutionPolicy(id="rp1-x", object_address_id="*", kind="concordance")
    assert p.contestation_threshold is None  # caller (claims.py, F10) treats None as 0.0


def test_weighted_requires_justification() -> None:
    with pytest.raises(ValueError, match="justification"):
        ResolutionPolicy(
            id="rp1-x", object_address_id="*", kind="weighted",
            weights={"as-a": 1.0},
        )


def test_weighted_tie_resolves_to_none(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _register(ws, "as-a", "human", "human-a")
    _register(ws, "as-b", "agent", "apparatus-b")
    position_for(ws, "ah1-1", OBJ, "as-a", "occurs")
    position_for(ws, "ah1-1", OBJ, "as-b", "does-not-occur")
    policy = ResolutionPolicy(
        id=new_policy_id(), object_address_id=OBJ, kind="weighted",
        weights={"as-a": 1.0, "as-b": 1.0}, justification="equal trust, declared for this study",
    )
    active = active_positions(_all_positions(ws), "ah1-1", OBJ)
    assert resolve(ws, active, policy) is None  # exact tie: no legitimate winner


def test_policy_ablation_reports_declared_and_alternatives(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    hits = _two_assessor_divergence_fixture(ws)
    named_a = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="named-assessor", assessor_object_id="as-a")
    concordance = ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="concordance")
    result = policy_ablation(ws, hits, OBJ, declared=named_a, alternatives=[concordance])
    assert result["declared"]["occurs"] == 4
    assert result["alternatives"][0]["occurs"] == 1
    assert result["declared"]["occurs"] != result["alternatives"][0]["occurs"]


def test_active_policy_for_prefers_specific_over_study_default(tmp_path: Path) -> None:
    from ontograph.resolution import active_policy_for

    ws = _ws(tmp_path)
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id="*", kind="concordance"))
    declare_policy(ws, ResolutionPolicy(id=new_policy_id(), object_address_id=OBJ, kind="named-assessor", assessor_object_id="as-a"))
    active = active_policy_for(ws, OBJ)
    assert active.kind == "named-assessor"
    other = active_policy_for(ws, "some-other-object")
    assert other.kind == "concordance"  # falls back to study default


def test_active_policy_for_none_when_nothing_declared(tmp_path: Path) -> None:
    from ontograph.resolution import active_policy_for

    ws = _ws(tmp_path)
    assert active_policy_for(ws, OBJ) is None


def test_cli_policy_declare_and_list(tmp_path: Path, capsys) -> None:
    from ontograph.cli import main

    ws_dir = str(tmp_path / "ontograph-workspaces")
    study_id = "f05-cli"
    assert main(["study", "new", study_id, "--corpus-root", ".", "--workspaces-dir", ws_dir]) == 0

    code = main([
        "policy", "declare", study_id, "--kind", "concordance",
        "--contestation-threshold", "0.1",
        "--workspaces-dir", ws_dir, "--json",
    ])
    captured = capsys.readouterr()
    assert code == 0, captured.err

    code = main(["policy", "list", study_id, "--workspaces-dir", ws_dir, "--json"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    import json as _json
    result = _json.loads(captured.out)
    assert result["count"] == 1
    assert result["policies"][0]["kind"] == "concordance"
    assert result["policies"][0]["contestation_threshold"] == 0.1
