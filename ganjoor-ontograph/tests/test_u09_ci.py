"""Static contract for the U09 cross-platform CI workflow."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = PROJECT_ROOT.parent / ".github" / "workflows" / "ontograph-ci.yml"


def test_ci_workflow_covers_gate_f_distribution_matrix() -> None:
    """CI is isolated, read-only, and exercises every Gate F command class."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "contents: read" in workflow
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert '"3.10"' in workflow
    assert '"3.12"' in workflow
    assert 'python -m pip install ".[dev]"' in workflow
    assert "python -m build" in workflow
    assert "tests/test_u08_packaging.py -q" in workflow
    assert "tests/test_release_reconstruction.py -q" in workflow
    assert "python -m pytest -q" in workflow
    assert "python -m ruff check tests/test_u09_ci.py" in workflow
    assert "python -m ruff format --check tests/test_u09_ci.py" in workflow
    assert "secrets." not in workflow
