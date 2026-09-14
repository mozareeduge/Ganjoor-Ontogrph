"""Tests for ontograph.release (ledger rows P4.4-P4.5)."""
import json

import pytest

from ontograph.release import (
    DATA_LICENSE_NOTICE,
    MissingLicenseNoticeError,
    generate_release,
    release_as_git_tag,
)
from ontograph.workspace import _run_git, new_study


@pytest.fixture()
def workspace(tmp_path):
    return new_study(tmp_path, "test-study")


# --- P4.4 ---

def test_release_refuses_to_generate_with_empty_license_notice(workspace):
    with pytest.raises(MissingLicenseNoticeError):
        generate_release(workspace, id="rel-1", version="0.1.0", field_charter="charter-1", data_license_notice="")
    with pytest.raises(MissingLicenseNoticeError):
        generate_release(workspace, id="rel-1", version="0.1.0", field_charter="charter-1", data_license_notice="   ")


def test_generated_release_contains_licensing_chain_verbatim(workspace):
    release = generate_release(
        workspace, id="rel-1", version="0.1.0", field_charter="charter-1",
        data_license_notice=DATA_LICENSE_NOTICE,
    )
    assert release.data_license_notice == DATA_LICENSE_NOTICE
    assert "public domain" in DATA_LICENSE_NOTICE
    assert "Ganjoor's own work" in DATA_LICENSE_NOTICE
    assert "MIT-licensed by the fork" in DATA_LICENSE_NOTICE

    release_json = json.loads((workspace / "releases" / "v0.1.0" / "release.json").read_text(encoding="utf-8"))
    assert release_json["data_license_notice"] == DATA_LICENSE_NOTICE
    release_md = (workspace / "releases" / "v0.1.0" / "RELEASE.md").read_text(encoding="utf-8")
    assert DATA_LICENSE_NOTICE in release_md


# --- P4.5 ---

def test_release_as_git_tag_creates_matching_tag(workspace):
    generate_release(
        workspace, id="rel-1", version="0.1.0", field_charter="charter-1",
        data_license_notice=DATA_LICENSE_NOTICE,
    )
    tag = release_as_git_tag(workspace, "0.1.0")
    assert tag == "v0.1.0"
    tags = _run_git(workspace, ["tag", "--list"])
    assert "v0.1.0" in tags.splitlines()
    tagged_commit = _run_git(workspace, ["rev-list", "-n", "1", "v0.1.0"])
    head = _run_git(workspace, ["rev-parse", "HEAD"])
    assert tagged_commit == head
