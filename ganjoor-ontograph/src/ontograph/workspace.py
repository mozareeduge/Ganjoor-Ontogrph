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

import yaml

WORKSPACE_SUBDIRS = ("field", "objects", "corpus", "research", "mappings", "events", "releases")

# T01 (v0.1.1 trust repair): workspace schema versioning. Version 2 is the
# canonical schema stamped by new_study(); workspaces predating the key are
# read as legacy version 1 (their layout is exactly the v0.1 layout). This
# constant is what T03's migration detector keys on -- detection is by the
# missing key, never by filename (spec Amendment §15.1).
WORKSPACE_SCHEMA_VERSION = 2
WORKSPACE_SCHEMA_VERSION_LEGACY_DEFAULT = 1


def new_study(base_dir: str | Path, study_id: str, corpus_root: str | None = None) -> Path:
    """Create `base_dir/study_id/` with spec §60's subdirectory layout and
    initialize it as its own git repository with one commit, so
    `git -C <workspace> rev-parse HEAD` succeeds immediately (ledger row
    P1.7's Verify) rather than only after the first real study action.

    Ledger row P9.1: a study that records `corpus_root` here lets every
    later verb omit `--corpus-root` and still find the right corpus,
    instead of forcing every single CLI call to repeat it (a real,
    repeated friction point from the user's own test session)."""
    base_dir = Path(base_dir)
    workspace = base_dir / study_id
    if workspace.exists():
        raise FileExistsError(f"study workspace already exists: {workspace}")

    workspace.mkdir(parents=True)
    for sub in WORKSPACE_SUBDIRS:
        (workspace / sub).mkdir()
    config: dict = {"schema_version": WORKSPACE_SCHEMA_VERSION, "study_id": study_id}
    if corpus_root:
        config["corpus_root"] = str(corpus_root)
    (workspace / "study.yml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
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


def read_study_config(workspace: str | Path) -> dict:
    """Read `study.yml`, returning `{}` for a workspace that predates this
    file or has an empty one (never raising -- an absent stored corpus_root
    is a normal, expected case, not a workspace-corruption error)."""
    path = Path(workspace) / "study.yml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def workspace_schema_version(workspace: str | Path) -> int:
    """Return the workspace's study.yml `schema_version` (T01).

    A workspace whose study.yml lacks the key is a pre-T01 legacy
    workspace: report `WORKSPACE_SCHEMA_VERSION_LEGACY_DEFAULT` (1) rather
    than raising -- absent version is a normal state for v0.1 workspaces,
    never corruption. Explicit stored versions pass through unchanged so a
    future version bump can be detected and refused with a message instead
    of silently misread."""
    config = read_study_config(workspace)
    version = config.get("schema_version")
    if version is None:
        return WORKSPACE_SCHEMA_VERSION_LEGACY_DEFAULT
    if not isinstance(version, int) or version < 1:
        raise ValueError(f"invalid study.yml schema_version: {version!r}")
    return version
