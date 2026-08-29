"""Trace / Relation-Object / Profile / Experiment / Finding record CRUD,
and the append-only EventRecord log.

Spec §50 (`TraceRecord`), §51 (`EventRecord` -- the workspace event log is
normative, append-only), §52 (`ProfileRecord`, `ExperimentRecord`),
§54 (`RelationObject`), §55 (`FindingRecord`). JSONL-backed under the
workspace layout `workspace.py` already creates (spec §60):
`research/traces.jsonl`, `research/relations.jsonl`,
`research/profiles.jsonl`, `research/experiments.jsonl`,
`research/findings.jsonl`, `events/events.jsonl`.

Scope note (Finding 5 of the external review, also in
IMPLEMENTATION_LEDGER.md P4.1): this row is Trace/Relation-Object/Profile/
Experiment/Finding only. Fourfold Diagnostic and Bridge Record CRUD are
deliberately NOT built here -- spec §12/§73's own restraint ("fourfold
only when load-bearing") applies to the build too, not just to research
practice.

Implemented in ledger rows P4.1 (record CRUD), P4.2 (AI-summary Profile
provenance requirement), P4.3 (append-only event log).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field as dc_field
from pathlib import Path

RESEARCH_FILENAMES = {
    "trace": "traces.jsonl",
    "relation": "relations.jsonl",
    "profile": "profiles.jsonl",
    "experiment": "experiments.jsonl",
    "finding": "findings.jsonl",
}


def research_path(workspace: str | Path, record_type: str) -> Path:
    return Path(workspace) / "research" / RESEARCH_FILENAMES[record_type]


def _append_jsonl(path: Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def _read_jsonl(path: Path, cls):
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(cls(**json.loads(line)))
    return records


# --- P4.1: Trace, Relation-Object, Profile, Experiment, Finding ---

@dataclass(frozen=True)
class TraceRecord:
    id: str
    initiating_encounters: list = dc_field(default_factory=list)
    initiating_mapping_objects: list = dc_field(default_factory=list)
    what_appeared: str = ""
    candidate_descriptions: list = dc_field(default_factory=list)
    next_discriminating_action: str = ""
    status: str = "active"  # active|narrowed|split|residue|promoted
    created_by: str = ""


@dataclass(frozen=True)
class RelationObject:
    id: str
    participants: list = dc_field(default_factory=list)
    initiating_trace_ids: list = dc_field(default_factory=list)
    profile_ids: list = dc_field(default_factory=list)
    mapping_object_ids: list = dc_field(default_factory=list)
    candidate_descriptions: list = dc_field(default_factory=list)
    direction: str | None = None
    evidence_routes: list = dc_field(default_factory=list)
    counter_evidence: list = dc_field(default_factory=list)
    experiment_ids: list = dc_field(default_factory=list)
    use_status: str = ""
    claim_permission: str = ""
    history: list = dc_field(default_factory=list)
    residue: bool = False


class MissingSummarizerProvenanceError(ValueError):
    """Raised by ProfileRecord construction (spec §40, §52 v2.3.0): an
    ai-summary Profile without a recorded model/prompt version is not
    reproducible even when the underlying corpus snapshot is pinned."""


@dataclass(frozen=True)
class ProfileRecord:
    id: str
    addressed_object_or_relation: str
    source_or_witness: str
    access_apparatus: str
    access_condition: str = ""
    transformation_history: list = dc_field(default_factory=list)
    available_qualities: list = dc_field(default_factory=list)
    access_limits: list = dc_field(default_factory=list)
    authority_scope: str = ""
    uncertainty: str = ""
    field_version: str = ""
    summarizer_model_version: str | None = None
    summarizer_prompt_version: str | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.access_apparatus == "ai-summary" and (
            not self.summarizer_model_version or not self.summarizer_prompt_version
        ):
            raise MissingSummarizerProvenanceError(
                "access_apparatus='ai-summary' requires both "
                "summarizer_model_version and summarizer_prompt_version"
            )


@dataclass(frozen=True)
class ExperimentRecord:
    id: str
    research_pressure: str = ""
    baseline_profile_ids: list = dc_field(default_factory=list)
    changed_condition: str = ""
    held_conditions: list = dc_field(default_factory=list)
    expected_discrimination: str = ""
    operation_spec: str = ""
    result_profile_ids: list = dc_field(default_factory=list)
    result_mapping_ids: list = dc_field(default_factory=list)
    findings: list = dc_field(default_factory=list)
    status: str = ""


@dataclass(frozen=True)
class FindingRecord:
    id: str
    pressure: str = ""
    operation_or_construction: str = ""
    encounter_created: str = ""
    observation: str = ""
    consequence: str = ""
    limits: str = ""
    supporting_profiles: list = dc_field(default_factory=list)
    supporting_mapping_objects: list = dc_field(default_factory=list)


RECORD_CLASSES = {
    "trace": TraceRecord,
    "relation": RelationObject,
    "profile": ProfileRecord,
    "experiment": ExperimentRecord,
    "finding": FindingRecord,
}


def write_record(workspace: str | Path, record_type: str, record) -> None:
    _append_jsonl(research_path(workspace, record_type), record)


def read_records(workspace: str | Path, record_type: str) -> list:
    return _read_jsonl(research_path(workspace, record_type), RECORD_CLASSES[record_type])


# --- P4.3: append-only EventRecord log (spec §51) ---

@dataclass(frozen=True)
class EventRecord:
    id: str
    study_id: str
    event_type: str
    actor_type: str = "human"  # human|agent|engine|import
    actor_id: str = ""
    target_type: str = ""
    target_ids: list = dc_field(default_factory=list)
    input_record_ids: list = dc_field(default_factory=list)
    output_record_ids: list = dc_field(default_factory=list)
    parent_event_ids: list = dc_field(default_factory=list)
    branch_id: str = ""
    operation_spec_id: str = ""
    rationale: str = ""
    created_at: str = ""


class EventLogMutationError(ValueError):
    """Raised by `mutate_event`/`delete_event` -- the event log is
    append-only (spec §51): an event may point to records that later
    become superseded, split, merged, or residual, but it is not deleted
    or rewritten for that reason."""


def _events_path(workspace: str | Path) -> Path:
    return Path(workspace) / "events" / "events.jsonl"


def append_event(workspace: str | Path, record: EventRecord) -> None:
    _append_jsonl(_events_path(workspace), record)


def read_events(workspace: str | Path) -> list[EventRecord]:
    """Returns the event sequence in append order -- replaying a study's
    research-state transitions is reading this list in order, per spec
    §51; no separate derived-state machine exists in v0.1."""
    return _read_jsonl(_events_path(workspace), EventRecord)


def mutate_event(*_args, **_kwargs) -> None:
    raise EventLogMutationError("the event log is append-only; events cannot be mutated")


def delete_event(*_args, **_kwargs) -> None:
    raise EventLogMutationError("the event log is append-only; events cannot be deleted")
