#!/usr/bin/env python3
"""Shared isolated text-transformation adapters.

Book fluency, Composer rearticulation, and Sessions articulation all need the
same narrow contract: prompt in, transformed prose out, no workspace agency, and
durable ledger/provenance rows. Keeping the provider wiring here prevents the
Claude, Codex, and Gemini paths from drifting when one runtime needs a fix.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path

from _authoring._core import _run_claude_p, authoring_engine_mode
from _book_compose import _arabic_run_count
from _book_voice_prompts import _articulation_prompt, _articulation_repair_prompt
from _content_profile import source_language as _source_language

_MIN_TIMEOUT = 180
_MAX_TIMEOUT = 600
_WORD_RE = re.compile(r"\b[\w'’-]+\b")
_PHASE = "rearticulate"
_TEXT_TRANSFORM_SYSTEM_PROMPT = (
    "You are a non-agentic text transformation engine. Follow the user's prompt exactly. "
    "Return only the requested transformed prose. Do not mention tools, commands, files, "
    "scripts, terminal output, or the act of processing the request."
)
_GEMINI_MODEL = "gemini-2.5-flash"
_CODEX_MODEL = "gpt-5.5"

TextAdapter = Callable[..., str]


def timeout_for_window(base_text: str) -> int:
    """Derive the model-call timeout from the actual passage being rewritten."""
    words = len(_WORD_RE.findall(base_text or ""))
    arabic_runs = _arabic_run_count(base_text or "")
    seconds = 90 + int(words * 0.04) + int(arabic_runs * 0.5)
    return max(_MIN_TIMEOUT, min(_MAX_TIMEOUT, seconds))


def resolve_runtime_engine(engine: str) -> str:
    """Resolve ``auto`` to the configured authoring engine policy."""
    if engine != "auto":
        return engine
    mode = authoring_engine_mode()
    return "codex" if mode == "codex" else "claude"


def adapters_for_engine(engine: str) -> tuple[TextAdapter | None, TextAdapter | None]:
    """Return generation and repair adapters for an engine name.

    ``claude`` returns ``None`` adapters so callers keep using their existing
    default path. Alternate providers are explicit and testable.
    """
    if engine == "claude":
        return None, None
    if engine == "codex":
        return _codex_adapter, _codex_repair_adapter
    if engine == "gemini":
        return _gemini_adapter, _gemini_repair_adapter
    raise ValueError(f"unknown text transform engine {engine!r}")


def preflight_engine(engine: str) -> None:
    """Fail before a long run if the selected text engine cannot even start."""
    if engine == "claude":
        if not shutil.which("claude"):
            raise RuntimeError("Claude Code CLI not found on PATH; choose --engine codex or install Claude Code.")
        return
    if engine == "codex":
        from _codex_text import _codex_bin

        _codex_bin()
        return
    if engine == "gemini":
        from _secrets import get_gemini_key

        get_gemini_key()
        return
    raise ValueError(f"unknown text transform engine {engine!r}")


def _adapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    lang = _source_language(book_dir)
    timeout = timeout_for_window(base_text)
    log(f"      {label}: timeout={timeout}s ({_window_shape(base_text)})")
    rc, out, err = _run_claude_p(
        _articulation_prompt(title, base_text, previous_tail, frame=frame, narrator=narrator, source_language=lang),
        timeout=timeout,
        book_dir=book_dir,
        phase=_PHASE,
        step=label,
        tools="",
        safe_mode=True,
        no_chrome=True,
        no_session_persistence=True,
        system_prompt=_TEXT_TRANSFORM_SYSTEM_PROMPT,
        effort="low",
    )
    if rc != 0:
        raise RuntimeError(f"{label}: claude -p rc={rc}: {(err or '')[:200]}")
    return (out or "").strip()


def _repair_adapter(
    title: str,
    base_text: str,
    candidate_text: str,
    gates: list[str],
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    lang = _source_language(book_dir)
    timeout = timeout_for_window(base_text)
    log(f"      {label}: repair timeout={timeout}s ({_window_shape(base_text)}, gates={len(gates)})")
    rc, out, err = _run_claude_p(
        _articulation_repair_prompt(
            title,
            base_text,
            candidate_text,
            gates,
            previous_tail,
            frame=frame,
            narrator=narrator,
            source_language=lang,
        ),
        timeout=timeout,
        book_dir=book_dir,
        phase=_PHASE,
        step=label,
        tools="",
        safe_mode=True,
        no_chrome=True,
        no_session_persistence=True,
        system_prompt=_TEXT_TRANSFORM_SYSTEM_PROMPT,
        effort="low",
    )
    if rc != 0:
        raise RuntimeError(f"{label}: claude -p rc={rc}: {(err or '')[:200]}")
    return (out or "").strip()


def _gemini_adapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    return _call_gemini(
        _articulation_prompt(
            title,
            base_text,
            previous_tail,
            frame=frame,
            narrator=narrator,
            source_language=_source_language(book_dir),
        ),
        book_dir=book_dir,
        label=label,
        base_text=base_text,
        log=log,
        temperature=0.35,
        repair=False,
    )


def _gemini_repair_adapter(
    title: str,
    base_text: str,
    candidate_text: str,
    gates: list[str],
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    return _call_gemini(
        _articulation_repair_prompt(
            title,
            base_text,
            candidate_text,
            gates,
            previous_tail,
            frame=frame,
            narrator=narrator,
            source_language=_source_language(book_dir),
        ),
        book_dir=book_dir,
        label=label,
        base_text=base_text,
        log=log,
        temperature=0.25,
        repair=True,
        gate_count=len(gates),
    )


def _codex_adapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    return _call_codex(
        _articulation_prompt(
            title,
            base_text,
            previous_tail,
            frame=frame,
            narrator=narrator,
            source_language=_source_language(book_dir),
        ),
        book_dir=book_dir,
        label=label,
        base_text=base_text,
        log=log,
        repair=False,
    )


def _codex_repair_adapter(
    title: str,
    base_text: str,
    candidate_text: str,
    gates: list[str],
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    return _call_codex(
        _articulation_repair_prompt(
            title,
            base_text,
            candidate_text,
            gates,
            previous_tail,
            frame=frame,
            narrator=narrator,
            source_language=_source_language(book_dir),
        ),
        book_dir=book_dir,
        label=label,
        base_text=base_text,
        log=log,
        repair=True,
        gate_count=len(gates),
    )


def _call_gemini(
    prompt: str,
    *,
    book_dir: Path,
    label: str,
    base_text: str,
    log,
    temperature: float,
    repair: bool,
    gate_count: int = 0,
) -> str:
    from _gemini_text import call_gemini_text

    timeout = timeout_for_window(base_text)
    log(_call_log_line(label, "gemini", timeout, base_text, repair=repair, gate_count=gate_count))
    return call_gemini_text(
        prompt,
        book_dir=book_dir,
        phase=_PHASE,
        step=label,
        model=_GEMINI_MODEL,
        system_prompt=_TEXT_TRANSFORM_SYSTEM_PROMPT,
        timeout=timeout,
        temperature=temperature,
    )


def _call_codex(
    prompt: str,
    *,
    book_dir: Path,
    label: str,
    base_text: str,
    log,
    repair: bool,
    gate_count: int = 0,
) -> str:
    from _codex_text import call_codex_text

    timeout = timeout_for_window(base_text)
    log(_call_log_line(label, "codex", timeout, base_text, repair=repair, gate_count=gate_count))
    return call_codex_text(
        prompt,
        book_dir=book_dir,
        phase=_PHASE,
        step=label,
        model=_CODEX_MODEL,
        system_prompt=_TEXT_TRANSFORM_SYSTEM_PROMPT,
        timeout=timeout,
    )


def _call_log_line(label: str, provider: str, timeout: int, base_text: str, *, repair: bool, gate_count: int) -> str:
    suffix = f", gates={gate_count}" if repair else ""
    mode = " repair" if repair else ""
    return f"      {label}: {provider}{mode} timeout={timeout}s ({_window_shape(base_text)}{suffix})"


def _window_shape(base_text: str) -> str:
    return f"words={len(_WORD_RE.findall(base_text or ''))}, Arabic={_arabic_run_count(base_text or '')}"
