"""P2.4 phase runner — Wave-B registry wiring validation."""
from __future__ import annotations

import py_compile
from pathlib import Path

from ._base import PhaseResult

PHASE_ID = "P2.4"
DESCRIPTION = "Wave-B phase wiring complete and validated"

REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE_INIT = REPO_ROOT / "scripts" / "podcast" / "phases" / "__init__.py"
RUN_WAVE = REPO_ROOT / "scripts" / "podcast" / "run_wave.py"


def _registry_wired(repo_root: Path) -> bool:
    init_file = repo_root / "scripts" / "podcast" / "phases" / "__init__.py"
    if not init_file.exists():
        return False
    text = init_file.read_text(encoding="utf-8")
    return (
        "p2_3" in text
        and "p2_4_wave2" in text
        and "2: [" in text
    )


def _runner_compiles(repo_root: Path) -> bool:
    run_wave = repo_root / "scripts" / "podcast" / "run_wave.py"
    try:
        py_compile.compile(str(run_wave), doraise=True)
    except Exception:
        return False
    return True


def is_done(repo_root: Path | None = None) -> bool:
    if repo_root is None:
        repo_root = REPO_ROOT
    return _registry_wired(repo_root) and _runner_compiles(repo_root)


def execute(repo_root: Path | None = None) -> PhaseResult:
    if repo_root is None:
        repo_root = REPO_ROOT
    if not _registry_wired(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="Wave-B registry wiring missing (p2_3/p2_4_wave2).",
            evidence_paths=[str(PHASE_INIT)],
        )
    if not _runner_compiles(repo_root):
        return PhaseResult(
            phase_id=PHASE_ID,
            status="halted",
            message="run_wave.py does not compile after Wave-B wiring.",
            evidence_paths=[str(PHASE_INIT), str(RUN_WAVE)],
        )
    return PhaseResult(
        phase_id=PHASE_ID,
        status="done",
        message="Wave-B registry wired and run_wave runner compiles cleanly.",
        rows_marked=[PHASE_ID],
        evidence_paths=[str(PHASE_INIT), str(RUN_WAVE)],
    )
