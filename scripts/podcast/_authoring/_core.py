"""_authoring/_core.py — Constants, AuthoringError, and LLM shellout helpers.

Extracted from _authoring.py (A4 split). Contains everything through
_assert_artifact so the per-phase modules can import from here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ._claude_runtime import (
    DEFAULT_MODEL_LABEL,
    call_diagnostics,
    dump_failed_call,
    log_claude_p,
    record_model_provenance,
)
from ._claude_runtime import (
    PURE_JSON_SYSTEM_PROMPT as PURE_JSON_SYSTEM_PROMPT,
)
from ._claude_runtime import (
    PURE_TEXT_SYSTEM_PROMPT as PURE_TEXT_SYSTEM_PROMPT,
)
from ._claude_runtime import (
    pure_json_call_options as pure_json_call_options,
)
from ._claude_runtime import (
    pure_text_call_options as pure_text_call_options,
)
from ._engine_fallback import (
    AUTHORING_ENGINE_ENV as AUTHORING_ENGINE_ENV,
)
from ._engine_fallback import (
    CODEX_FALLBACK_ENV as CODEX_FALLBACK_ENV,
)
from ._engine_fallback import (
    authoring_engine_mode as authoring_engine_mode,
)
from ._engine_fallback import (
    codex_allowed_as_fallback,
    forced_codex,
    looks_like_claude_unavailable,
    run_codex_authoring,
)
from ._engine_fallback import (
    codex_fallback_enabled as codex_fallback_enabled,
)
from ._routing import (
    ARABIC_SCHOLARLY_CATEGORIES as ARABIC_SCHOLARLY_CATEGORIES,
)
from ._routing import (
    FICTION_CONTENT_PROFILES as FICTION_CONTENT_PROFILES,
)
from ._routing import (
    SKIP_ENRICHMENT_CATEGORIES as SKIP_ENRICHMENT_CATEGORIES,
)
from ._routing import (
    SKIP_OCR_CATEGORIES as SKIP_OCR_CATEGORIES,
)
from ._routing import (
    SKIP_PHONETICS_CATEGORIES as SKIP_PHONETICS_CATEGORIES,
)
from ._routing import (
    _read_category as _read_category,
)
from ._routing import (
    _read_content_profile as _read_content_profile,
)

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

    def __init__(self, phase: str, message: str, manual_fallback: str = "", stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.phase = phase
        self.manual_fallback = manual_fallback
        self.stdout = stdout
        self.stderr = stderr


class AuthoringHalt(AuthoringError):
    """Raised when a phase completes its work but requires human review before the next phase.

    Unlike AuthoringError (failure), AuthoringHalt signals *successful* completion
    with a required human gate. The orchestrator maps this to phase_status="halted"
    rather than "failed", preserving the phase's completed work.
    """

    def __init__(self, phase: str, message: str, manual_fallback: str = ""):
        super().__init__(phase=phase, message=message, manual_fallback=manual_fallback)


# A phase is listed ONLY when its output is GATED (a bad window reverts to its
# base, or the result is a human-reviewed proposal — nothing ships on its own)
# so a weaker model costs a wasted window, never bad prose on the page. Every
# other phase, including judgment calls like chapter design (0d) and
# enrichment (0e), is absent on purpose and inherits the CLI's own default.
PHASE_MODEL_OVERRIDE: dict[str, str] = {
    "0book-fluency": "claude-sonnet-4-6",
    "0book-student-reader": "claude-sonnet-4-6",
    "compose-paste-fix": "claude-sonnet-4-6",
    "rearticulate": "claude-sonnet-4-6",
}

# ── Determinism contract (read before "make authoring deterministic") ──────────
# The `claude -p` CLI exposes NO temperature, top_p, or seed flag (verified
# against `claude --help`). Authoring therefore runs at the model's default
# sampling and a *fresh* generation of any artifact is genuinely non-deterministic
# — re-running produces different prose. The route is REPRODUCIBLE-BY-CHECKPOINT,
# not generation-deterministic: once an artifact exists on disk the phases skip
# re-authoring (skip-if-exists / framing-signature cache), so a re-run of a
# completed book is stable. Deleting an artifact or forcing a re-author re-enters
# the stochastic path and yields different bytes. Two consequences we make honest:
#   1. Model provenance is recorded per call (record_model_provenance) so a book
#      authored partly by the Sonnet timeout-fallback is visible, not silent.
#   2. Callers that re-enter the stochastic path log it loudly (per_chapter
#      framing cache-miss) so "reproducible only via checkpoints" is observable.
# Pinning sampling is impossible until the CLI grows the knob; do NOT claim the
# content route is byte-deterministic.


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
    tools: str | None = None,
    safe_mode: bool = False,
    no_chrome: bool = False,
    no_session_persistence: bool = False,
    system_prompt: str | None = None,
    effort: str | None = None,
) -> tuple[int, str, str]:
    """Run `claude -p "<prompt>"` synchronously. Return (rc, stdout, stderr)."""
    if forced_codex():
        return run_codex_authoring(
            prompt,
            cwd=cwd,
            timeout=timeout,
            book_dir=book_dir,
            phase=phase,
            step=step,
            system_prompt=system_prompt,
            reason="forced-codex",
        )

    # acceptEdits alone doesn't grant Write permission for new files in non-interactive
    # subprocess contexts — claude -p returns "Permission needed to write the file."
    # instead of writing. --allowedTools grants the specific tools each phase needs.
    _ALLOWED = "Write,Edit,MultiEdit,Read,Bash,Grep,Glob"
    argv: list[str] = [
        CLAUDE_CMD,
        "-p",
    ]
    if safe_mode:
        argv.append("--safe-mode")
    if no_chrome:
        argv.append("--no-chrome")
    if no_session_persistence:
        argv.append("--no-session-persistence")
    if effort is not None:
        argv.extend(["--effort", effort])
    argv.extend(
        [
            "--permission-mode",
            "acceptEdits",
        ]
    )
    if tools is None:
        argv.extend(["--allowedTools", _ALLOWED])
    else:
        argv.extend(["--tools", tools])
    if system_prompt is not None:
        argv.extend(["--system-prompt", system_prompt])
    argv.extend(["--output-format", "json"])
    _resolved_model_flag = model_flag or PHASE_MODEL_OVERRIDE.get(phase)
    if _resolved_model_flag:
        argv.extend(["--model", _resolved_model_flag])
    # A prompt passed as a positional argv element hits the OS's ARG_MAX
    # (1 MiB on macOS, shared with the environment) well before any phase-level
    # word-count ceiling does — surfaced by a 182k-word single-PDF volume of
    # uyoon-al-akhbaar, where 0book-design's whole-book TOC pass raised
    # `OSError: [Errno 7] Argument list too long`. `claude -p` reads the prompt
    # from stdin when no positional prompt is given (verified empirically), so
    # route large prompts there instead — argv is left untouched below the
    # threshold to avoid changing behavior for the thousands of calls already
    # proven to work that way.
    _STDIN_PROMPT_THRESHOLD = 200_000
    _prompt_via_stdin = len(prompt) > _STDIN_PROMPT_THRESHOLD
    if not _prompt_via_stdin:
        argv.append(prompt)
    # P0 COST POLICY (2026-06-04): `claude -p` MUST use the flat-rate Claude Max
    # subscription, NEVER the metered Anthropic API. Strip any API-key env from the
    # child so the Claude CLI authenticates via the Max / OAuth session. The paid
    # Anthropic API key is reserved for the SDK paths that structurally require it
    # (0b/0c windowed refinement) — "API only when needed".
    child_env = dict(os.environ)
    for _v in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        child_env.pop(_v, None)
    _t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=child_env,
            input=prompt if _prompt_via_stdin else None,
        )
        rc, raw_stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        _elapsed_ms = int((time.monotonic() - _t0) * 1000)
        _tokens_in = _tokens_out = None
        if book_dir is not None:
            try:
                from _cost_ledger import append_from_claude_p_stdout

                _row = append_from_claude_p_stdout(
                    book_dir,
                    phase=phase or "(unspecified)",
                    step=step or "(unspecified)",
                    model=_resolved_model_flag or model,
                    stdout=raw_stdout,
                )
                _tokens_in, _tokens_out = _row.input_tokens, _row.output_tokens
            except Exception as e:
                sys.stderr.write(f"[_run_claude_p] cost-ledger append failed: {e!r}\n")
                _row = None
            # `_row.model` is the CLI's own report of who actually answered;
            # the requested model is only the fallback for unparseable stdout.
            _effective_model = (_row.model if _row is not None else None) or _resolved_model_flag or model
            record_model_provenance(
                book_dir,
                phase=phase,
                step=step,
                model=_effective_model,
                fallback=_effective_model != DEFAULT_MODEL_LABEL,
            )
        try:
            from _cost_ledger import parse_text_from_json_stdout

            stdout = parse_text_from_json_stdout(raw_stdout)
        except Exception:
            stdout = raw_stdout

        # Timeline event. On a NON-ZERO rc the full prompt and both streams are
        # also dumped to a sidecar — before this, a failed call persisted nothing
        # at all while a successful one wrote two artifacts.
        _dump = (
            None if rc == 0 else dump_failed_call(book_dir, step=step, prompt=prompt, stdout=raw_stdout, stderr=stderr)
        )
        if codex_allowed_as_fallback() and looks_like_claude_unavailable(rc, raw_stdout, stderr):
            log_claude_p(
                "claude_p.codex_fallback",
                book_dir=book_dir,
                level="warning",
                phase=phase,
                step=step,
                model=_resolved_model_flag or model,
                rc=rc,
                prompt=prompt,
                stdout=raw_stdout,
                stderr=stderr,
                prompt_dump=_dump,
                msg="Claude primary unavailable; trying Codex fallback",
            )
            return run_codex_authoring(
                prompt,
                cwd=cwd,
                timeout=timeout,
                book_dir=book_dir,
                phase=phase,
                step=step,
                system_prompt=system_prompt,
                reason="claude-unavailable",
                claude_rc=rc,
                claude_stdout=raw_stdout,
                claude_stderr=stderr,
            )
        log_claude_p(
            "claude_p.call",
            book_dir=book_dir,
            level="info" if rc == 0 else "error",
            phase=phase,
            step=step,
            model=_resolved_model_flag or model,
            rc=rc,
            duration_ms=_elapsed_ms,
            tokens_in=_tokens_in,
            tokens_out=_tokens_out,
            **call_diagnostics(
                timeout=timeout,
                tools=tools,
                safe_mode=safe_mode,
                no_chrome=no_chrome,
                no_session_persistence=no_session_persistence,
                effort=effort,
                system_prompt=system_prompt,
            ),
            prompt=prompt,
            stdout=raw_stdout,
            stderr=stderr,
            prompt_dump=_dump,
            msg="" if rc == 0 else f"claude -p exited {rc}",
        )
        return rc, stdout, stderr
    except FileNotFoundError as e:
        if codex_allowed_as_fallback():
            log_claude_p(
                "claude_p.codex_fallback",
                book_dir=book_dir,
                level="warning",
                phase=phase,
                step=step,
                model=_resolved_model_flag or model,
                msg=f"`{CLAUDE_CMD}` not found; trying Codex fallback",
            )
            return run_codex_authoring(
                prompt,
                cwd=cwd,
                timeout=timeout,
                book_dir=book_dir,
                phase=phase,
                step=step,
                system_prompt=system_prompt,
                reason="claude-missing",
                claude_rc=127,
                claude_stderr=str(e),
            )
        log_claude_p(
            "claude_p.missing_binary",
            book_dir=book_dir,
            level="error",
            phase=phase,
            step=step,
            model=_resolved_model_flag or model,
            duration_ms=int((time.monotonic() - _t0) * 1000),
            **call_diagnostics(
                timeout=timeout,
                tools=tools,
                safe_mode=safe_mode,
                no_chrome=no_chrome,
                no_session_persistence=no_session_persistence,
                effort=effort,
                system_prompt=system_prompt,
            ),
            msg=f"`{CLAUDE_CMD}` not found on PATH",
        )
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
        # TimeoutExpired carries whatever the child had already written. That
        # partial output was previously discarded unread — it is often the only
        # evidence of WHY the call hung, so capture it before re-raising.
        _partial_out, _partial_err = getattr(e, "stdout", None), getattr(e, "stderr", None)
        _dump = dump_failed_call(book_dir, step=step, prompt=prompt, stdout=_partial_out, stderr=_partial_err)
        log_claude_p(
            "claude_p.timeout",
            book_dir=book_dir,
            level="error",
            phase=phase,
            step=step,
            model=_resolved_model_flag or model,
            rc=None,
            duration_ms=int((time.monotonic() - _t0) * 1000),
            **call_diagnostics(
                timeout=timeout,
                tools=tools,
                safe_mode=safe_mode,
                no_chrome=no_chrome,
                no_session_persistence=no_session_persistence,
                effort=effort,
                system_prompt=system_prompt,
            ),
            prompt=prompt,
            stdout=_partial_out,
            stderr=_partial_err,
            prompt_dump=_dump,
            msg=f"timed out after {timeout}s",
        )
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
    **run_options: Any,
) -> tuple[int, str, str]:
    """Timeout → single retry with fallback model → halt."""
    try:
        return _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase=phase,
            step=step,
            **run_options,
        )
    except AuthoringError as e:
        if "timed out after" not in str(e):
            raise

    bumped = int(timeout * fallback_timeout_multiplier)
    log(
        f"      [retry] {step}: first attempt timed out ({timeout}s); "
        f"retrying once with model={fallback_model}, timeout={bumped}s "
        f"— CONTENT-PROVENANCE DIVERGENCE: this artifact will be authored by "
        f"{fallback_model}, not {DEFAULT_MODEL_LABEL} (recorded in "
        f"_system/model-provenance.jsonl)"
    )
    try:
        return _run_claude_p(
            prompt,
            timeout=bumped,
            book_dir=book_dir,
            phase=phase,
            step=f"{step}-retry-sonnet",
            model=fallback_model,
            model_flag=fallback_model,
            **run_options,
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
