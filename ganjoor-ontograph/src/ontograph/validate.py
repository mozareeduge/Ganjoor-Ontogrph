"""Deterministic + epistemic contract tests, implementation gates.

Spec §65 (deterministic corpus tests), §66 (epistemic contract tests --
scenario tests that the system does NOT collapse anchor into occurrence,
co-incidence into causation, estimate into census, etc.), §69
(implementation gates 1-5), §70 (occurrence-assessment scalability gate).

Also home to the Appendix A "invariant audit" added per
EXTERNAL_REVIEW.md Finding 4 (ledger row P3.9, re-run again at P7.4): a
periodic re-check of the full Appendix A non-equivalence list against the
assembled engine, because a single ledger row's per-row "spec wins, flag
don't pick" discipline never by itself looks at the engine as a whole.
Gate 3 below re-runs it live via a real pytest subprocess, not a
reimplemented copy of its assertions.

Implemented in ledger rows P3.9, P7.1-P7.6.
"""
from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
from dataclasses import asdict as _asdict, dataclass, fields
from pathlib import Path

from ontograph.anchors import AnchorHit, LexicalAnchor, census as run_census
from ontograph.cli import main as cli_main
from ontograph.corpus import load_corpus_snapshot
from ontograph.field import scan_corpus
from ontograph.records import FindingRecord, ProfileRecord
from ontograph.release import DATA_LICENSE_NOTICE, generate_release, reconstruct_from_release
from ontograph.workspace import new_study


@dataclass(frozen=True)
class GateResult:
    gate: int
    name: str
    passed: bool
    detail: str


def _run_git_rev_parse(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check_gate_1_corpus_pin(corpus_root: str | Path) -> GateResult:
    """spec §69 gate 1: exact commit + manifest hash are recorded; a
    corpus root that isn't a git checkout is reported as unverifiable,
    not silently treated as pinned."""
    commit = _run_git_rev_parse(Path(corpus_root))
    snap = load_corpus_snapshot(corpus_root, commit=commit)
    passed = len(snap.manifest_sha256) == 64 and commit is not None and len(commit) == 40
    detail = f"commit={commit}, manifest_sha256={snap.manifest_sha256[:12]}..."
    if commit is None:
        detail += " (corpus_root is not a git checkout -- commit pin unverifiable)"
    return GateResult(gate=1, name="corpus pin", passed=passed, detail=detail)


def check_gate_2_lexical_object_separation() -> GateResult:
    """spec §69 gate 2: Anchor Hits and Occurrence Assessments stay
    separate in schema. Structural check: an `AnchorHit` that itself
    carried a decision/acceptance field would be exactly the collapse
    this gate exists to catch."""
    hit_fields = {f.name for f in fields(AnchorHit)}
    forbidden = {"decision", "accepted", "occurred", "is_occurrence", "assessed"}
    passed = not (hit_fields & forbidden)
    return GateResult(
        gate=2, name="lexical/object separation", passed=passed,
        detail=f"AnchorHit fields: {sorted(hit_fields)}",
    )


def check_gate_3_deterministic_engine(repo_root: str | Path) -> GateResult:
    """spec §69 gate 3: field construction, census, scale, comparison,
    ablation, and source-return pass fixture tests -- AND P3.9's
    Appendix A invariant audit is re-run live here (a real pytest
    subprocess against the current source tree), not trusted from
    whenever it last passed during development."""
    targets = [
        "fixtures/mini-ganjoor/test_fixture_ground_truth.py",
        "tests/test_field.py", "tests/test_anchors.py", "tests/test_compare.py",
        "tests/test_ablation.py", "tests/invariants/test_appendix_a.py",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *targets],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    passed = result.returncode == 0
    summary_lines = [l for l in result.stdout.strip().splitlines() if l]
    detail = summary_lines[-1] if summary_lines else result.stderr.strip()[-500:]
    return GateResult(gate=3, name="deterministic engine + Appendix A re-check", passed=passed, detail=detail)


def check_gate_4_runtime() -> GateResult:
    """spec §69 gate 4: the chosen agent interface can actually invoke
    Ontograph operations through the CLI (Part XIII settles, for Claude
    Code specifically, that no separate tool adapter is needed).

    `--help` is invoked with real stdout swallowed (`redirect_stdout`) --
    argparse's help action prints straight to the process's actual
    stdout even when called in-process, and this check must not leak
    that text into a caller's own `--json` output (e.g. `ontograph
    validate --gates --json` calling this gate as one step of its own
    result)."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cli_main(["--help"])
        in_process_ok = False  # unreachable in practice -- --help always calls sys.exit
    except SystemExit as e:
        in_process_ok = (e.code == 0)
    console_script = shutil.which("ontograph")
    return GateResult(
        gate=4, name="runtime (CLI invocation)", passed=in_process_ok,
        detail=f"in-process CLI ok={in_process_ok}, console script on PATH={console_script or 'not found'}",
    )


def check_gate_5_research_loop(workspace_dir: str | Path, corpus_root: str | Path) -> GateResult:
    """spec §69 gate 5 / ledger row P7.6: one end-to-end study replayed
    from Field Charter to Research Release, then independently
    reconstructed from the release package alone (see
    `release.reconstruct_from_release`'s own docstring for the v0.1
    embedding convention this depends on)."""
    ws = new_study(workspace_dir, "gate5-study")
    records = scan_corpus(corpus_root)
    mirror_anchors = [
        LexicalAnchor(object_address="mirror", form="آینه"),
        LexicalAnchor(object_address="mirror", form="آیینه"),
    ]
    mirror_hits = run_census(records, mirror_anchors)
    profile = ProfileRecord(
        id="p1", addressed_object_or_relation="mirror",
        source_or_witness="poem 9101", access_apparatus="original-text",
    )
    finding = FindingRecord(id="f1", pressure="gate5 check", observation="mirror recurs across the field")
    release = generate_release(
        ws, id="gate5-release", version="0.1.0", field_charter="gate5 field",
        data_license_notice=DATA_LICENSE_NOTICE, corpus_snapshot=str(corpus_root),
        object_addresses=[{"id": "mirror", "anchors": ["آینه", "آیینه"]}],
        load_bearing_profiles=[_asdict(profile)], findings=[_asdict(finding)],
    )
    reconstructed = reconstruct_from_release(Path(ws) / "releases" / "v0.1.0" / "release.json")
    passed = (
        reconstructed["object_hit_counts"].get("mirror") == len(mirror_hits)
        and reconstructed["profiles"] == [_asdict(profile)]
        and reconstructed["findings"] == [_asdict(finding)]
    )
    return GateResult(
        gate=5, name="research loop (end-to-end replay)", passed=passed,
        detail=f"reconstructed mirror hit_count={reconstructed['object_hit_counts'].get('mirror')} (live={len(mirror_hits)})",
    )


def run_gates(repo_root: str | Path, corpus_root: str | Path, workspace_dir: str | Path) -> list[GateResult]:
    return [
        check_gate_1_corpus_pin(corpus_root),
        check_gate_2_lexical_object_separation(),
        check_gate_3_deterministic_engine(repo_root),
        check_gate_4_runtime(),
        check_gate_5_research_loop(workspace_dir, corpus_root),
    ]
