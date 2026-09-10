"""End-to-end replay test (ledger row P7.6, spec §69 gate 5): run one
full study from Field Charter to Research Release on the fixture, then
independently reconstruct its state from the release package alone, and
assert it matches the live workspace -- not just internal consistency
between numbers computed in the same test function.
"""
import json
import pathlib
from dataclasses import asdict

from ontograph.anchors import LexicalAnchor, census
from ontograph.field import FieldCharter, all_poems, scan_corpus
from ontograph.records import FindingRecord, ProfileRecord, read_records, write_record
from ontograph.release import DATA_LICENSE_NOTICE, generate_release, reconstruct_from_release
from ontograph.workspace import new_study

FIXTURE_ROOT = pathlib.Path(__file__).parent.parent / "fixtures" / "mini-ganjoor"


def test_end_to_end_replay_field_charter_to_release_and_back(tmp_path):
    # 1. Field Charter, against the live fixture corpus
    ws = new_study(tmp_path, "e2e-study")
    records = scan_corpus(FIXTURE_ROOT)
    charter = FieldCharter(purpose="e2e replay", corpus_snapshot=str(FIXTURE_ROOT), scope_spec=all_poems())
    poem_count = charter.poem_count(records)
    assert poem_count == 27

    # 2. Object Address + census, written into the live workspace
    mirror_anchors = [
        LexicalAnchor(object_address="mirror", form="آینه"),
        LexicalAnchor(object_address="mirror", form="آیینه"),
    ]
    mirror_hits = census(records, mirror_anchors)
    assert len(mirror_hits) == 7

    # 3. Profile + Finding, written into the LIVE workspace's own research/*.jsonl
    profile = ProfileRecord(
        id="e2e-profile-1", addressed_object_or_relation="mirror",
        source_or_witness="poem 9101", access_apparatus="original-text",
    )
    finding = FindingRecord(
        id="e2e-finding-1", pressure="does mirror recur across the fixture field?",
        observation="mirror has 7 anchor hits across 7 poems", limits="anchor level only, not assessed",
    )
    write_record(ws, "profile", profile)
    write_record(ws, "finding", finding)

    # 4. Research Release, embedding the object address + full record content
    #    (see release.py's own docstring for why: v0.1's embedding convention)
    release = generate_release(
        ws, id="e2e-release", version="0.1.0", field_charter="e2e field: all 27 poems",
        data_license_notice=DATA_LICENSE_NOTICE, corpus_snapshot=str(FIXTURE_ROOT),
        object_addresses=[{"id": "mirror", "anchors": ["آینه", "آیینه"]}],
        load_bearing_profiles=[asdict(profile)], findings=[asdict(finding)],
    )
    tag_dir = ws / "releases" / "v0.1.0"
    assert (tag_dir / "release.json").exists() and (tag_dir / "RELEASE.md").exists()

    # 5. Independent reconstruction from release.json ALONE (no read of
    #    objects/object-addresses.jsonl or research/*.jsonl)
    reconstructed = reconstruct_from_release(tag_dir / "release.json")

    # 6. Assert the reconstruction matches the LIVE workspace's own state,
    #    read independently -- not just the values already held in this
    #    test function's local variables
    live_profiles = [asdict(p) for p in read_records(ws, "profile")]
    live_findings = [asdict(f) for f in read_records(ws, "finding")]
    assert reconstructed["profiles"] == live_profiles
    assert reconstructed["findings"] == live_findings
    assert reconstructed["object_hit_counts"]["mirror"] == len(mirror_hits)

    # and the release.json on disk is what reconstruct_from_release actually read
    on_disk = json.loads((tag_dir / "release.json").read_text(encoding="utf-8"))
    assert on_disk["load_bearing_profiles"] == live_profiles
    assert on_disk["findings"] == live_findings
    assert on_disk["data_license_notice"] == DATA_LICENSE_NOTICE
