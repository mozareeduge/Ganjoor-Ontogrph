"""Tests for ontograph.records (ledger rows P4.1-P4.3)."""
import pathlib

import pytest

from ontograph.records import (
    EventLogMutationError,
    EventRecord,
    ExperimentRecord,
    FindingRecord,
    MissingSummarizerProvenanceError,
    ProfileRecord,
    RelationObject,
    TraceRecord,
    append_event,
    delete_event,
    mutate_event,
    read_events,
    read_records,
    write_record,
)
from ontograph.workspace import new_study


@pytest.fixture()
def workspace(tmp_path):
    return new_study(tmp_path, "test-study")


# --- P4.1: round-trip write/read for one instance of each record type ---

def test_trace_record_round_trips(workspace):
    record = TraceRecord(
        id="trace-1", initiating_encounters=["enc-1"], what_appeared="a mirror-rust pairing",
        candidate_descriptions=["literal", "figurative"], status="active", created_by="human",
    )
    write_record(workspace, "trace", record)
    assert read_records(workspace, "trace") == [record]


def test_relation_object_round_trips(workspace):
    record = RelationObject(
        id="rel-1", participants=["mirror", "rust"], initiating_trace_ids=["trace-1"],
        direction=None, use_status="candidate", claim_permission="none",
    )
    write_record(workspace, "relation", record)
    assert read_records(workspace, "relation") == [record]


def test_profile_record_round_trips(workspace):
    record = ProfileRecord(
        id="profile-1", addressed_object_or_relation="mirror",
        source_or_witness="poem 9101", access_apparatus="original-text",
        field_version="v1",
    )
    write_record(workspace, "profile", record)
    assert read_records(workspace, "profile") == [record]


def test_experiment_record_round_trips(workspace):
    record = ExperimentRecord(
        id="exp-1", research_pressure="does removing sample1 change the co-incidence?",
        changed_condition="ablate sample1", status="complete",
    )
    write_record(workspace, "experiment", record)
    assert read_records(workspace, "experiment") == [record]


def test_finding_record_round_trips(workspace):
    record = FindingRecord(
        id="finding-1", pressure="ablation", observation="retention differs by level",
        limits="fixture-only, not generalized",
    )
    write_record(workspace, "finding", record)
    assert read_records(workspace, "finding") == [record]


# --- P4.2: AI-summary Profile provenance requirement ---

def test_ai_summary_profile_without_provenance_raises():
    with pytest.raises(MissingSummarizerProvenanceError):
        ProfileRecord(
            id="profile-2", addressed_object_or_relation="mirror",
            source_or_witness="poem 9101", access_apparatus="ai-summary",
        )


def test_ai_summary_profile_with_provenance_succeeds():
    record = ProfileRecord(
        id="profile-3", addressed_object_or_relation="mirror",
        source_or_witness="poem 9101", access_apparatus="ai-summary",
        summarizer_model_version="claude-x", summarizer_prompt_version="v1",
    )
    assert record.summarizer_model_version == "claude-x"


def test_non_ai_summary_profile_does_not_require_provenance():
    record = ProfileRecord(
        id="profile-4", addressed_object_or_relation="mirror",
        source_or_witness="poem 9101", access_apparatus="original-text",
    )
    assert record.summarizer_model_version is None


# --- P4.3: append-only EventRecord log ---

def test_events_append_and_replay_in_order(workspace):
    e1 = EventRecord(id="ev-1", study_id="test-study", event_type="field-revision")
    e2 = EventRecord(id="ev-2", study_id="test-study", event_type="anchor-approval", parent_event_ids=["ev-1"])
    e3 = EventRecord(id="ev-3", study_id="test-study", event_type="occurrence-assessment", parent_event_ids=["ev-2"])
    append_event(workspace, e1)
    append_event(workspace, e2)
    append_event(workspace, e3)
    replayed = read_events(workspace)
    assert [e.id for e in replayed] == ["ev-1", "ev-2", "ev-3"]
    assert replayed == [e1, e2, e3]


def test_mutating_or_deleting_a_past_event_raises():
    with pytest.raises(EventLogMutationError):
        mutate_event()
    with pytest.raises(EventLogMutationError):
        delete_event()
