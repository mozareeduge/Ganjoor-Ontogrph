"""Distribution checks for U08.

The smoke test builds a wheel, installs it into a fresh virtual environment,
and invokes its console script with the source checkout deliberately absent
from the child process's import path.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib
import venv
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_distribution_metadata_and_clean_wheel_smoke(tmp_path: Path) -> None:
    """The published artifact has complete metadata and works standalone."""
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert set(project["urls"]) >= {"Homepage", "Repository"}
    assert {"Programming Language :: Python :: 3"} <= set(
        project["classifiers"]
    )
    assert {dependency.split("=", 1)[0].split(">", 1)[0].split("<", 1)[0] for dependency in project["optional-dependencies"]["dev"]} >= {"pytest", "ruff", "build"}

    dist_dir = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
        cwd=PROJECT_ROOT,
        check=True,
    )
    wheel = next(dist_dir.glob("ontograph-*.whl"))
    sdist = next(dist_dir.glob("ontograph-*.tar.gz"))
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert any(name.endswith("/src/ontograph/cli.py") for name in names)
        assert any(name.endswith("/pyproject.toml") for name in names)
        assert any(name.endswith("/LICENSE") for name in names)
    with zipfile.ZipFile(wheel) as archive:
        assert any(name.startswith("ontograph/") for name in archive.namelist())
        entry_points = archive.read(next(name for name in archive.namelist() if name.endswith("entry_points.txt")))
        assert b"ontograph = ontograph.cli:main" in entry_points

    environment = tmp_path / "clean-venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = _venv_python(environment)
    subprocess.run([python, "-m", "pip", "install", str(wheel)], check=True)
    clean_env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
    clean_env["PATH"] = str(python.parent) + os.pathsep + clean_env["PATH"]
    completed = subprocess.run(
        [python, "-c", "import ontograph; import subprocess, sys; raise SystemExit(subprocess.call(['ontograph', '--help']))"],
        cwd=tmp_path,
        env=clean_env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
