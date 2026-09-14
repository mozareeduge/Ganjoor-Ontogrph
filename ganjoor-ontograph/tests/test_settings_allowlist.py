"""Tests for the Claude Code permissioning posture (ledger row P6.2, spec
§79): corpus-mutating/release-creating verbs are named explicitly in
`.claude/settings.json`'s allowlist, and no blanket Bash grant stands in
for them."""
import json
import pathlib

SETTINGS_PATH = pathlib.Path(__file__).parent.parent.parent / ".claude" / "settings.json"

REQUIRED_VERB_PREFIXES = [
    "ontograph field build",
    "ontograph object add",
    "ontograph calibrate",
    "ontograph release",
]


def _load_allowlist():
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return data["permissions"]["allow"]


def test_settings_file_exists_and_parses():
    assert SETTINGS_PATH.is_file()
    _load_allowlist()  # raises if malformed


def test_required_verbs_are_named_explicitly():
    allow = _load_allowlist()
    for verb in REQUIRED_VERB_PREFIXES:
        assert any(verb in rule for rule in allow), f"missing allowlist entry for {verb!r}"


def test_no_blanket_bash_grant():
    allow = _load_allowlist()
    blanket_patterns = {"Bash", "Bash(*)", "Bash(ontograph:*)", "Bash(ontograph *)"}
    assert not (set(allow) & blanket_patterns)
    for rule in allow:
        assert rule.startswith("Bash(ontograph ")  # every entry names a specific verb, not the bare binary
