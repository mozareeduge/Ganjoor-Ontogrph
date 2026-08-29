"""Study workspace management.

Spec §60: each study receives an isolated workspace under
`ontograph-workspaces/<study-id>/` (charter/, objects/, corpus/, research/,
mappings/, events/, releases/). Per the v2.3.0 addition to §60, each
workspace SHOULD itself be a git repository, with each release a tagged
commit -- reusing the same commit-pin discipline the corpus layer already
imposes on itself (spec §56), applied reflexively to the research layer.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE_SUBDIRS = ("field", "objects", "corpus", "research", "mappings", "events", "releases")


def new_study(base_dir: str | Path, study_id: str) -> Path:
    """Create `base_dir/study_id/` with spec §60's subdirectory layout and
    initialize it as its own git repository with one commit, so
    `git -C <workspace> rev-parse HEAD` succeeds immediately (ledger row
    P1.7's Verify) rather than only after the first real study action."""
    base_dir = Path(base_dir)
    workspace = base_dir / study_id
    if workspace.exists():
        raise FileExistsError(f"study workspace already exists: {workspace}")

    workspace.mkdir(parents=True)
    for sub in WORKSPACE_SUBDIRS:
        (workspace / sub).mkdir()
    (workspace / "study.yml").write_text(f"study_id: {study_id}\n", encoding="utf-8")
    (workspace / "events" / "events.jsonl").write_text("", encoding="utf-8")

    _run_git(workspace, ["init", "--quiet"])
    _run_git(workspace, ["add", "-A"])
    _run_git(
        workspace,
        [
            "-c", "user.email=ontograph@localhost",
            "-c", "user.name=ontograph",
            "commit", "--quiet", "-m", f"ontograph study new {study_id}",
        ],
    )
    return workspace


def _run_git(workspace: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def workspace_head(workspace: str | Path) -> str:
    return _run_git(Path(workspace), ["rev-parse", "HEAD"])
