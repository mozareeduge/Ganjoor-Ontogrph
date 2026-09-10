"""U07 discriminating documentation contract."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_u07_docs_have_governed_quickstart_and_migration_boundary() -> None:
    docs = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "CHANGELOG.md", "MIGRATION.md")
    ).lower()
    exact = "study new → inquire → field/refresh → review → walk → assessed-full operation → source return → finding → release"
    assert exact in docs
    commands = [
        "ontograph study new", "ontograph inquire <study> --hunch", "ontograph field build",
        "ontograph inquire <study> --refresh", "ontograph inquire <study> --review", "ontograph walk", "--mode assessed-full",
        "ontograph source show", "--type finding", "ontograph release",
    ]
    # Check the concrete command stages using their first occurrence in the
    # README quickstart; the exact route above covers the conceptual wording.
    quickstart = docs[: docs.index("## what the records mean")]
    positions = [quickstart.index(term) for term in commands]
    assert positions == sorted(positions)
    assert "agent prepares" in docs and "researcher supplies" in docs
    assert "sole active" in docs and "multiple" in docs
    assert "scaffold" not in docs



