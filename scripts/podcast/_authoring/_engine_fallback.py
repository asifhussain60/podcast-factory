"""Subscription-backed authoring engine fallback policy."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ._claude_runtime import log_claude_p

AUTHORING_ENGINE_ENV = "PODCAST_FACTORY_AUTHORING_ENGINE"
CODEX_FALLBACK_ENV = "PODCAST_FACTORY_CODEX_FALLBACK"

_AUTHORING_ENGINE_AUTO = "auto"
_AUTHORING_ENGINE_CLAUDE = "claude"
_AUTHORING_ENGINE_CODEX = "codex"
_AUTHORING_ENGINES = {_AUTHORING_ENGINE_AUTO, _AUTHORING_ENGINE_CLAUDE, _AUTHORING_ENGINE_CODEX}

_CLAUDE_UNAVAILABLE_PATTERNS = (
    "usage limit",
    "limit reached",
    "rate limit",
    "429",
    "too many requests",
    "quota",
    "exhausted",
    "subscription",
    "insufficient credits",
    "credit balance",
    "auth failed",
    "authentication",
    "unauthorized",
    "http 401",
    "token expired",
    "claude code cli not found",
    "not found on path",
)


def authoring_engine_mode() -> str:
    """Which subscription-backed authoring engine should be tried first."""
    mode = os.environ.get(AUTHORING_ENGINE_ENV, _AUTHORING_ENGINE_AUTO).strip().lower()
    return mode if mode in _AUTHORING_ENGINES else _AUTHORING_ENGINE_AUTO


def codex_fallback_enabled() -> bool:
    """Whether ``auto`` mode may use Codex after a Claude availability failure."""
    value = os.environ.get(CODEX_FALLBACK_ENV, "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def codex_allowed_as_fallback() -> bool:
    return authoring_engine_mode() == _AUTHORING_ENGINE_AUTO and codex_fallback_enabled()


def forced_codex() -> bool:
    return authoring_engine_mode() == _AUTHORING_ENGINE_CODEX


def looks_like_claude_unavailable(rc: int, stdout: str, stderr: str) -> bool:
    if rc == 0:
        return False
    parts = [stderr or "", stdout or ""]
    try:
        payload = json.loads(stdout or "{}")
        if payload.get("is_error"):
            parts.extend(
                str(payload.get(k) or "") for k in ("api_error_status", "api_error_type", "error", "result", "message")
            )
    except (TypeError, ValueError):
        pass
    combined = "\n".join(parts).lower()
    return any(pattern in combined for pattern in _CLAUDE_UNAVAILABLE_PATTERNS)


def run_codex_authoring(
    prompt: str,
    *,
    cwd: Path | None,
    timeout: int,
    book_dir: Path | None,
    phase: str,
    step: str,
    system_prompt: str | None,
    reason: str,
    claude_rc: int | None = None,
    claude_stdout: str = "",
    claude_stderr: str = "",
) -> tuple[int, str, str]:
    from _codex_text import call_codex_agent

    rc, stdout, stderr = call_codex_agent(
        prompt,
        cwd=cwd,
        book_dir=book_dir,
        phase=phase or "(unspecified)",
        step=step or "(unspecified)",
        system_prompt=system_prompt or "",
        timeout=timeout,
    )
    log_claude_p(
        "codex_authoring.call",
        book_dir=book_dir,
        level="info" if rc == 0 else "error",
        phase=phase,
        step=step,
        model="codex",
        rc=rc,
        reason=reason,
        claude_rc=claude_rc,
        prompt=prompt,
        stdout=stdout,
        stderr=stderr,
    )
    if rc == 0:
        return rc, stdout, stderr
    detail = "\n".join(
        part
        for part in (
            f"Claude primary rc={claude_rc}" if claude_rc is not None else "",
            (claude_stderr or claude_stdout or "")[:600],
            f"Codex fallback rc={rc}",
            (stderr or stdout or "")[:600],
        )
        if part
    )
    return rc, stdout, detail
