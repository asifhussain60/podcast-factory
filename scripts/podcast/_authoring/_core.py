"""_authoring/_core.py — Constants, AuthoringError, and LLM shellout helpers.

Extracted from _authoring.py (A4 split). Contains everything through
_assert_artifact so the per-phase modules can import from here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Ensure scripts/podcast/ is importable from within the package directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_TIMEOUT = 1800
FRAMING_TIMEOUT = 1500
CHALLENGER_TIMEOUT = 1500
FIXER_TIMEOUT = 600
TRAINER_TIMEOUT = 1800

PHASE_0B_WINDOW_WORDS = 3000
PHASE_0B_OVERLAP_WORDS = 120
PHASE_0B_WINDOW_TIMEOUT = 600
PHASE_0C_WINDOW_WORDS = 8000
PHASE_0C_OVERLAP_WORDS = 60
PHASE_0C_WINDOW_TIMEOUT = 600

PHASE_0D_TOC_TIMEOUT = 600
PHASE_0D_SC_TIMEOUT = 1800
PHASE_0E_CHAPTER_TIMEOUT = 900

PHASE_0D_SC_TIMEOUT_MIN = 900
PHASE_0D_SC_TIMEOUT_MAX = 3600
PHASE_0D_SC_TIMEOUT_RATE = 0.4
PHASE_0D_SC_TIMEOUT_BASELINE = 600


def _compute_sc_timeout(words: int) -> int:
    """Word-count-aware per-source-chapter timeout in seconds."""
    import math
    raw = math.ceil(words * PHASE_0D_SC_TIMEOUT_RATE + PHASE_0D_SC_TIMEOUT_BASELINE)
    return max(PHASE_0D_SC_TIMEOUT_MIN, min(PHASE_0D_SC_TIMEOUT_MAX, raw))


CLAUDE_CMD = "claude"


class AuthoringError(RuntimeError):
    """Raised when an LLM-authoring shellout fails to produce its declared artifact."""

    def __init__(self, phase: str, message: str, manual_fallback: str = "",
                 stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.phase = phase
        self.manual_fallback = manual_fallback
        self.stdout = stdout
        self.stderr = stderr


DEFAULT_MODEL_LABEL = "claude-opus-4-7"


def _run_claude_p(
    prompt: str,
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    book_dir: Path | None = None,
    phase: str = "",
    step: str = "",
    model: str = DEFAULT_MODEL_LABEL,
    model_flag: str | None = None,
) -> tuple[int, str, str]:
    """Run `claude -p "<prompt>"` synchronously. Return (rc, stdout, stderr)."""
    argv: list[str] = [
        CLAUDE_CMD, "-p", "--permission-mode", "acceptEdits",
        "--output-format", "json",
    ]
    if model_flag:
        argv.extend(["--model", model_flag])
    argv.append(prompt)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        rc, raw_stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        if book_dir is not None:
            try:
                from _cost_ledger import append_from_claude_p_stdout
                append_from_claude_p_stdout(
                    book_dir,
                    phase=phase or "(unspecified)",
                    step=step or "(unspecified)",
                    model=model_flag or model,
                    stdout=raw_stdout,
                )
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"[_run_claude_p] cost-ledger append failed: {e!r}\n")
        try:
            from _cost_ledger import parse_text_from_json_stdout
            stdout = parse_text_from_json_stdout(raw_stdout)
        except Exception:
            stdout = raw_stdout
        return rc, stdout, stderr
    except FileNotFoundError as e:
        raise AuthoringError(
            phase="(shellout)",
            message=(
                f"`{CLAUDE_CMD}` not found on PATH. Install Claude Code CLI "
                f"(https://docs.claude.com/en/docs/claude-code/quickstart) or "
                f"add the binary to PATH."
            ),
            manual_fallback="Drive the phase via conversational /podcast skill.",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise AuthoringError(
            phase="(shellout)",
            message=f"LLM call timed out after {timeout}s.",
            manual_fallback="Resume manually via /podcast and `--resume` the orchestrator.",
        ) from e


def _run_claude_p_with_retry(
    prompt: str,
    *,
    timeout: int,
    book_dir: Path,
    phase: str,
    step: str,
    log=print,
    fallback_model: str = "claude-sonnet-4-6",
    fallback_timeout_multiplier: float = 1.5,
) -> tuple[int, str, str]:
    """Timeout → single retry with fallback model → halt."""
    try:
        return _run_claude_p(
            prompt, timeout=timeout,
            book_dir=book_dir, phase=phase, step=step,
        )
    except AuthoringError as e:
        if "timed out after" not in str(e):
            raise

    bumped = int(timeout * fallback_timeout_multiplier)
    log(f"      [retry] {step}: first attempt timed out ({timeout}s); "
        f"retrying once with model={fallback_model}, timeout={bumped}s")
    try:
        return _run_claude_p(
            prompt, timeout=bumped,
            book_dir=book_dir, phase=phase, step=f"{step}-retry-sonnet",
            model=fallback_model, model_flag=fallback_model,
        )
    except AuthoringError as e:
        if "timed out after" not in str(e):
            raise
        raise AuthoringError(
            phase=phase,
            message=(
                f"{step}: BOTH attempts timed out. Default model exceeded {timeout}s; "
                f"fallback {fallback_model} exceeded {bumped}s. No third auto-retry — "
                f"halt-and-surface per the 2026-05-24 timeout strategy."
            ),
            manual_fallback=(
                "Options to decide before re-launching:\n"
                "  (a) Force a split: re-run --resume --retry-phase 0d with "
                "--unit-mode section so the long source chapter becomes 2-3 "
                "smaller episodes.\n"
                "  (b) Manually author this source chapter's contract using "
                "the conversational /podcast skill against the input slice at "
                "_chunks/0d/sc-NNN.in.md, then drop sc-NNN.done.\n"
                "  (c) Bump the per-SC timeout cap (PHASE_0D_SC_TIMEOUT_MAX) "
                "if the chapter is genuinely an outlier — but ONLY if you "
                "expect the cost to be worth it."
            ),
        ) from e


def _assert_artifact(
    phase: str,
    path: Path,
    rc: int,
    stdout: str,
    stderr: str,
    manual_fallback: str,
) -> None:
    """Common post-shellout success check: artifact exists and is non-empty."""
    if rc != 0:
        raise AuthoringError(
            phase=phase,
            message=f"claude -p exited rc={rc} for Phase {phase}.",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )
    if not path.exists():
        raise AuthoringError(
            phase=phase,
            message=f"Phase {phase} did not produce expected artifact: {path}",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )
    if path.stat().st_size == 0:
        raise AuthoringError(
            phase=phase,
            message=f"Phase {phase} produced empty artifact: {path}",
            manual_fallback=manual_fallback,
            stdout=stdout,
            stderr=stderr,
        )
