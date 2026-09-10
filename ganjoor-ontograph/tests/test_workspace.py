"""Tests for ontograph.workspace (ledger row P1.7)."""
import subprocess
import tempfile
from pathlib import Path

from ontograph.workspace import WORKSPACE_SUBDIRS, new_study, workspace_head


def test_new_study_is_a_git_repo_with_a_head():
    with tempfile.TemporaryDirectory() as tmp:
        ws = new_study(tmp, "mirror-study")
        head = workspace_head(ws)
        assert len(head) == 40  # a real commit SHA, not empty


def test_new_study_creates_spec_subdirs():
    with tempfile.TemporaryDirectory() as tmp:
        ws = new_study(tmp, "mirror-study")
        for sub in WORKSPACE_SUBDIRS:
            assert (ws / sub).is_dir()


def test_new_study_refuses_to_clobber_existing_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        new_study(tmp, "mirror-study")
        try:
            new_study(tmp, "mirror-study")
            assert False, "expected FileExistsError"
        except FileExistsError:
            pass


def test_git_log_shows_the_creation_commit():
    with tempfile.TemporaryDirectory() as tmp:
        ws = new_study(tmp, "mirror-study")
        log = subprocess.run(
            ["git", "-C", str(ws), "log", "--oneline"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "mirror-study" in log
