"""Amendment 20 F08: contested Position Sets automatically mint Trace
candidates.

Discriminating target (Plans.md F08 DoD): constructing a contested
Position Set and running the relevant operation produces exactly one
Trace candidate referencing both positions and a resolvable source
return.
"""
from __future__ import annotations

from types import SimpleNamespace

from ontograph.assessors import AssessorObject, register_assessor
from ontograph.census import mint_contested_traces
from ontograph.positions import position_for
from ontograph.records import read_records

OBJ = "mirror"


def _ws(tmp_path):
    ws = tmp_path / "study"
    ws.mkdir()
    return ws


def _hit(hid, poem_id):
    return SimpleNamespace(id=hid, poem_id=poem_id)


def test_contested_hit_mints_exactly_one_trace(tmp_path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs", rationale="clear metaphor")
    position_for(ws, "ah1-1", OBJ, "as-agent", "does-not-occur", rationale="literal reading only")

    minted = mint_contested_traces(ws, [_hit("ah1-1", 9101)], OBJ)
    assert len(minted) == 1

    traces = read_records(ws, "trace")
    assert len(traces) == 1
    trace = traces[0]
    assert trace.status == "active"
    assert trace.initiating_encounters[0]["anchor_hit_id"] == "ah1-1"
    assert trace.initiating_encounters[0]["object_address"] == OBJ  # resolvable via source show
    assessor_ids = {d["assessor_object_id"] for d in trace.candidate_descriptions}
    assert assessor_ids == {"as-mz", "as-agent"}  # BOTH positions referenced
    stances = {d["stance"] for d in trace.candidate_descriptions}
    assert stances == {"occurs", "does-not-occur"}
    assert trace.next_discriminating_action  # never empty


def test_non_contested_hit_mints_nothing(tmp_path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")

    minted = mint_contested_traces(ws, [_hit("ah1-1", 9101)], OBJ)
    assert minted == []
    assert read_records(ws, "trace") == []


def test_minting_is_idempotent_across_repeated_runs(tmp_path) -> None:
    ws = _ws(tmp_path)
    register_assessor(ws, AssessorObject(id="as-mz", label="mz", assessor_type="human", apparatus="x", independence_class="human-mz"))
    register_assessor(ws, AssessorObject(id="as-agent", label="agent", assessor_type="agent", apparatus="x", independence_class="apparatus-x"))
    position_for(ws, "ah1-1", OBJ, "as-mz", "occurs")
    position_for(ws, "ah1-1", OBJ, "as-agent", "does-not-occur")

    first = mint_contested_traces(ws, [_hit("ah1-1", 9101)], OBJ)
    second = mint_contested_traces(ws, [_hit("ah1-1", 9101)], OBJ)
    assert len(first) == 1
    assert second == []  # already covered, not re-minted
    assert len(read_records(ws, "trace")) == 1  # not duplicated
