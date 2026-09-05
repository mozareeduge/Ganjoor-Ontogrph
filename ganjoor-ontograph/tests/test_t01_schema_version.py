"""Ledger row T01: schema constants and backward-compatible readers.

Discriminating target (spec Amendment §19, T01 row): a workspace written
by the current v0.1 code (no `schema_version` in study.yml) must keep
loading unchanged, while NEW study creation stamps
`schema_version: 2` and the reader exposes `workspace_schema_version()`
with a documented default. A reader that just demanded the key would
break every existing workspace; a writer that never stamps the version
would make T03's migration detection impossible. This test fails against
the pre-T01 code on both branches.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ontograph.workspace import WORKSPACE_SCHEMA_VERSION, new_study, read_study_config, workspace_schema_version


def test_new_study_stamps_schema_version_2(tmp_path: Path) -> None:
    ws = new_study(tmp_path, "t01-stamped")
    config = yaml.safe_load((ws / "study.yml").read_text(encoding="utf-8"))
    assert config["schema_version"] == 2, "new workspaces must stamp schema_version 2"


def test_reader_exposes_version_with_legacy_default(tmp_path: Path) -> None:
    ws = new_study(tmp_path, "t01-stamped-b")
    assert workspace_schema_version(ws) == 2

    # legacy workspace: strip the key the way pre-T01 code wrote study.yml
    config = read_study_config(ws)
    del config["schema_version"]
    (ws / "study.yml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    assert workspace_schema_version(ws) == WORKSPACE_SCHEMA_VERSION_LEGACY_DEFAULT
    assert WORKSPACE_SCHEMA_VERSION == 2


from ontograph.workspace import WORKSPACE_SCHEMA_VERSION_LEGACY_DEFAULT  # noqa: E402
