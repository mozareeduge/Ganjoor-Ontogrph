"""ResearchRelease generation.

Spec §55 (ResearchRelease schema) and §56/v2.3.0 (data-licensing
carry-forward: a release must embed the corpus's licensing chain verbatim
-- public-domain poem texts; the Ganjoor compilation and Persian AI
summaries used under Ganjoor's own attribution convention; MIT
fork-generated English summaries where used). A release refuses to
generate with an empty `data_license_notice` (ledger row P4.4's Verify).

Also responsible for the release-as-git-tag convention (spec §60/v2.3.0,
ledger row P4.5), tying `workspace.py`'s git-backed workspace to an actual
tagged commit per release.

**v0.1 embedding convention (ledger row P7.6, spec §69 gate 5).** Spec
§55 names `object_addresses`/`load_bearing_profiles`/`findings` as
release fields but does not fix what their list elements contain.
Object Address/Lexical Anchor are not yet formal JSONL-backed records
(P4.1's scope was Trace/Relation-Object/Profile/Experiment/Finding only;
`object add`'s CLI storage, P5.1, is a flat ad hoc structure) -- so for
this release to be reconstructable "from `release.json` alone" (spec
§69 gate 5) without re-reading the live workspace, `object_addresses`
entries here are `{"id":.., "anchors":[...]}` dicts, and
`load_bearing_profiles`/`findings` entries are the full serialized
record dicts (`dataclasses.asdict`), not bare id strings. This is a
concrete, documented choice within what spec §55 actually specifies, not
a silent deviation from it -- see `reconstruct_from_release()` below,
which depends on it.

Implemented in ledger rows P4.4, P4.5, and P7.6.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field as dc_field
from pathlib import Path

from ontograph.anchors import LexicalAnchor, census as run_census
from ontograph.field import scan_corpus
from ontograph.workspace import _run_git

# spec §55, verbatim from the licensing-chain sentence a release must
# carry forward -- never paraphrased, since paraphrase could silently
# drop an attribution term the upstream sources require in practice.
DATA_LICENSE_NOTICE = (
    "the classical poem texts are public domain; the Ganjoor compilation, "
    "structure, and Persian AI summaries are Ganjoor's own work under no "
    "declared open license, redistributed here under the attribution "
    "convention Ganjoor itself documents; any fork-generated English "
    "summary is MIT-licensed by the fork."
)


class MissingLicenseNoticeError(ValueError):
    """Raised by `generate_release()` when `data_license_notice` is empty
    or blank -- spec §55: a release that omits it is not exportable as a
    scholarly artifact."""


@dataclass(frozen=True)
class ResearchRelease:
    id: str
    version: str
    field_charter: str
    data_license_notice: str
    object_addresses: list = dc_field(default_factory=list)
    load_bearing_profiles: list = dc_field(default_factory=list)
    active_relation_objects: list = dc_field(default_factory=list)
    mapping_objects: list = dc_field(default_factory=list)
    experiments: list = dc_field(default_factory=list)
    findings: list = dc_field(default_factory=list)
    claims: list = dc_field(default_factory=list)
    residue: list = dc_field(default_factory=list)
    reductions: list = dc_field(default_factory=list)
    reopening_conditions: list = dc_field(default_factory=list)
    event_log_ref: str = ""
    software_environment: str = ""
    corpus_snapshot: str = ""


def generate_release(
    workspace: str | Path, id: str, version: str, field_charter: str,
    data_license_notice: str, **kwargs,
) -> ResearchRelease:
    """spec §55: builds a `ResearchRelease` and writes it under
    `releases/vX.Y.Z/` in the study workspace (`release.json` plus a
    human-readable `RELEASE.md` that surfaces the license notice
    directly). Refuses (raises `MissingLicenseNoticeError`) rather than
    generating a release with an empty `data_license_notice`."""
    if not data_license_notice or not data_license_notice.strip():
        raise MissingLicenseNoticeError(
            "data_license_notice is required and must not be empty (spec §55)"
        )
    release = ResearchRelease(
        id=id, version=version, field_charter=field_charter,
        data_license_notice=data_license_notice, **kwargs,
    )
    release_dir = Path(workspace) / "releases" / f"v{version}"
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "release.json").write_text(
        json.dumps(asdict(release), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (release_dir / "RELEASE.md").write_text(
        f"# Release v{version}\n\n## Data license notice\n\n{data_license_notice}\n",
        encoding="utf-8",
    )
    return release


def release_as_git_tag(workspace: str | Path, version: str) -> str:
    """spec §60 v2.3.0: `ontograph release` creates a git tag in the study
    workspace matching the release version. Call after `generate_release()`
    has written `releases/vX.Y.Z/` -- this commits those files and tags
    the resulting commit `vX.Y.Z`."""
    workspace = Path(workspace)
    _run_git(workspace, ["add", "-A"])
    _run_git(
        workspace,
        [
            "-c", "user.email=ontograph@localhost",
            "-c", "user.name=ontograph",
            "commit", "--quiet", "-m", f"ontograph release v{version}",
        ],
    )
    tag = f"v{version}"
    _run_git(workspace, ["tag", tag])
    return tag


def reconstruct_from_release(release_json_path: str | Path) -> dict:
    """spec §69 gate 5 / ledger row P7.6: rebuild study state from
    `release.json` alone -- no read of the live workspace's
    `objects/object-addresses.jsonl` or `research/*.jsonl` files. Uses
    only the release's own embedded `object_addresses` (id+anchors) and
    `corpus_snapshot` (a corpus root path) to recompute each object's
    Anchor Hit count from scratch, and returns the embedded
    `load_bearing_profiles`/`findings` exactly as the release carries
    them (they are already the full record, not a reference)."""
    release = json.loads(Path(release_json_path).read_text(encoding="utf-8"))
    records = scan_corpus(release["corpus_snapshot"])
    object_hit_counts = {}
    for entry in release["object_addresses"]:
        anchors = [LexicalAnchor(object_address=entry["id"], form=f) for f in entry["anchors"]]
        object_hit_counts[entry["id"]] = len(run_census(records, anchors))
    return {
        "object_hit_counts": object_hit_counts,
        "profiles": release["load_bearing_profiles"],
        "findings": release["findings"],
    }
