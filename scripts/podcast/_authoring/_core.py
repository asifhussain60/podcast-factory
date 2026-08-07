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

# ─── Content-category routing ─────────────────────────────────────────────────
# Single source of truth for which categories follow the Islamic/Arabic scholarly
# pipeline vs. which need alternative paths. Add new categories here as they
# are introduced; never hard-code category strings in phase modules.

# All categories whose content is Islamic/Arabic scholarly. These run the full
# pipeline: OCR→translate, Phase 0b (scholarly refinement), Phase 0c (Arabic
# phonetics), Phase 0d (scholarly chapter design), Phase 0e (7-tier Islamic
# enrichment), Islamic framing prompt, Islamic challenger rules.
ARABIC_SCHOLARLY_CATEGORIES: frozenset[str] = frozenset(
    {
        "books",
        "letters",
        "lectures",
        "articles",
        "asbaaq",
        "documents",
        "interviews",
    }
)

# Categories that skip Phase 0c (Arabic phonetics) entirely — no Arabic terms
# to extract, no _phonetics.md output needed.
SKIP_PHONETICS_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
        "explainers",
    }
)

# Categories that skip Phase 0e (enrichment) — source material is already
# authoritative (product docs, official technical docs) and outside enrichment
# would introduce inaccuracy.
SKIP_ENRICHMENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
    }
)

# Categories that skip Phase 0a (OCR + Azure translation) — source text is
# already in English (scraped web content, synthesized markdown, pre-written docs).
SKIP_OCR_CATEGORIES: frozenset[str] = frozenset(
    {
        "sites",
        "explainers",
    }
)

# content_profile values that trigger the fiction sidecar augmenter in Phase 0e.
# The sidecar augmenter NEVER modifies chapter prose — it writes a companion
# glossary/aside file only. The category field may say "books" for a fiction
# book (intake default); content_profile is the authoritative signal here.
FICTION_CONTENT_PROFILES: frozenset[str] = frozenset({"fiction"})


def _read_category(book_dir: "Path") -> str:
    """Read the content category for a book, with graceful fallbacks.

    Resolution order (first non-empty wins):
      1. _system/orchestrator-state.json  → "category" field
      2. _system/meta.yml                 → "category:" line
      3. Default: "books" (Islamic/scholarly path)

    The default of "books" guarantees that existing Islamic content that
    pre-dates category stamping continues to use the correct path.
    """
    import json as _json

    state_path = book_dir / "_system" / "orchestrator-state.json"
    if state_path.exists():
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
            cat = state.get("category", "").strip()
            if cat:
                return cat.lower()
        except Exception:
            pass

    meta_path = book_dir / "_system" / "meta.yml"
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("category:"):
                cat = line.split(":", 1)[1].strip().strip('"').strip("'")
                if cat:
                    return cat.lower()

    return "books"


def _read_content_profile(book_dir: "Path") -> str:
    """Read the content_profile for a book (distinct from category).

    Resolution order:
      1. _system/orchestrator-state.json → "content_profile" field
      2. _system/series-config.yaml      → "content_profile:" key
      3. Default: "" (empty — caller treats as "not fiction")

    content_profile is the engine-policy / augmentation routing key.
    category is the pipeline routing key. They can differ (e.g., a fiction
    book may have category="books" from intake but content_profile="fiction").
    content_profile wins for Phase 0e routing decisions.
    """
    import json as _json

    state_path = book_dir / "_system" / "orchestrator-state.json"
    if state_path.exists():
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
            prof = state.get("content_profile", "").strip()
            if prof:
                return prof.lower()
        except Exception:
            pass

    cfg_path = book_dir / "_system" / "series-config.yaml"
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("content_profile:"):
                prof = line.split(":", 1)[1].strip().strip('"').strip("'")
                if prof:
                    return prof.lower()

    return ""


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


DEFAULT_MODEL_LABEL = "claude-opus-4-8"


# ── Phase-declared model overrides (Asif, 2026-08-07) ───────────────────────
# A phase is listed ONLY when its output is GATED (a bad window reverts to its
# base, or the result is a human-reviewed proposal — nothing ships on its own)
# so a weaker model costs a wasted window, never bad prose on the page. Every
# other phase, including judgment calls like chapter design (0d) and
# enrichment (0e), is absent on purpose and inherits the CLI's own default.
PHASE_MODEL_OVERRIDE: dict[str, str] = {
    "0book-fluency": "claude-sonnet-4-6",
    "0book-student-reader": "claude-sonnet-4-6",
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


def record_model_provenance(
    book_dir: "Path | None", *, phase: str, step: str, model: str, fallback: bool = False
) -> None:
    """Append one row to _system/model-provenance.jsonl naming the model that
    authored this call. A row whose model != DEFAULT_MODEL_LABEL (or fallback=True)
    is a content-provenance divergence — surfaced so mixed-model books are visible.
    Best-effort: never raises into the authoring path."""
    if book_dir is None:
        return
    try:
        import json as _json

        sysdir = Path(book_dir) / "_system"
        sysdir.mkdir(parents=True, exist_ok=True)
        row = {
            "phase": phase or "(unspecified)",
            "step": step or "(unspecified)",
            "model": model,
            "fallback": bool(fallback),
            "divergence": bool(fallback or model != DEFAULT_MODEL_LABEL),
        }
        with (sysdir / "model-provenance.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(row) + "\n")
    except Exception as e:
        sys.stderr.write(f"[record_model_provenance] skipped: {e!r}\n")


def _dump_failed_call(
    book_dir: Path | None,
    *,
    step: str,
    prompt: str,
    stdout: Any,
    stderr: Any,
) -> str | None:
    """On a FAILED call only, write the full prompt + both streams to a sidecar.

    Hash-only logging is right for the success path and useless for the failure
    path — you cannot diff a prompt you no longer have. Bounded excerpts go in
    the timeline; the complete evidence goes here, and only when it is needed.
    Returns a repo-relative-ish path string, or None.
    """
    try:
        from _progress import current_run_id, init_run_log, run_log_path

        if not current_run_id():
            init_run_log(book_dir)
        base = run_log_path()
        if base is None:
            return None
        safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (step or "call"))[:60]
        stamp = time.strftime("%H%M%S", time.gmtime())
        p = Path(base).parent / f"{Path(base).stem}.{safe}-{stamp}.failure.txt"

        def _txt(v: Any) -> str:
            if v is None:
                return "(none)"
            if isinstance(v, bytes):
                return v.decode("utf-8", "replace")
            return str(v)

        p.write_text(
            "\n".join(
                [
                    f"step:   {step}",
                    f"run_id: {current_run_id()}",
                    "",
                    "===== PROMPT =====",
                    prompt,
                    "",
                    "===== STDOUT =====",
                    _txt(stdout),
                    "",
                    "===== STDERR =====",
                    _txt(stderr),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return str(p)
    except Exception as e:
        sys.stderr.write(f"[_dump_failed_call] skipped: {e!r}\n")
        return None


def _log_claude_p(
    event: str,
    *,
    book_dir: Path | None,
    prompt: str | None = None,
    stdout: Any = None,
    stderr: Any = None,
    **fields: Any,
) -> None:
    """Emit one claude_p.* timeline event. NEVER raises into the pipeline."""
    try:
        import hashlib

        from _progress import log_event, tail

        if prompt is not None:
            fields["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8", "replace")).hexdigest()[:16]
            fields["prompt_chars"] = len(prompt)
        if stdout is not None:
            fields["stdout_tail"] = tail(stdout)
        if stderr is not None:
            fields["stderr_tail"] = tail(stderr)
        log_event(event, book_dir=book_dir, **fields)
    except Exception as e:
        sys.stderr.write(f"[_log_claude_p] dropped {event!r}: {e!r}\n")


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
    # acceptEdits alone doesn't grant Write permission for new files in non-interactive
    # subprocess contexts — claude -p returns "Permission needed to write the file."
    # instead of writing. --allowedTools grants the specific tools each phase needs.
    _ALLOWED = "Write,Edit,MultiEdit,Read,Bash,Grep,Glob"
    argv: list[str] = [
        CLAUDE_CMD,
        "-p",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        _ALLOWED,
        "--output-format",
        "json",
    ]
    _resolved_model_flag = model_flag or PHASE_MODEL_OVERRIDE.get(phase)
    if _resolved_model_flag:
        argv.extend(["--model", _resolved_model_flag])
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
            None if rc == 0 else _dump_failed_call(book_dir, step=step, prompt=prompt, stdout=raw_stdout, stderr=stderr)
        )
        _log_claude_p(
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
            prompt=prompt,
            stdout=raw_stdout,
            stderr=stderr,
            prompt_dump=_dump,
            msg="" if rc == 0 else f"claude -p exited {rc}",
        )
        return rc, stdout, stderr
    except FileNotFoundError as e:
        _log_claude_p(
            "claude_p.missing_binary",
            book_dir=book_dir,
            level="error",
            phase=phase,
            step=step,
            model=_resolved_model_flag or model,
            duration_ms=int((time.monotonic() - _t0) * 1000),
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
        _dump = _dump_failed_call(book_dir, step=step, prompt=prompt, stdout=_partial_out, stderr=_partial_err)
        _log_claude_p(
            "claude_p.timeout",
            book_dir=book_dir,
            level="error",
            phase=phase,
            step=step,
            model=_resolved_model_flag or model,
            rc=None,
            duration_ms=int((time.monotonic() - _t0) * 1000),
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
) -> tuple[int, str, str]:
    """Timeout → single retry with fallback model → halt."""
    try:
        return _run_claude_p(
            prompt,
            timeout=timeout,
            book_dir=book_dir,
            phase=phase,
            step=step,
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
