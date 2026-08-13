"""Claude CLI runtime options and observability helpers."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_MODEL_LABEL = "claude-opus-4-8"

PURE_TEXT_SYSTEM_PROMPT = (
    "You are a non-agentic text transformation engine. Use only the user's prompt "
    "as context. Return only the requested text or data, with no commentary."
)

PURE_JSON_SYSTEM_PROMPT = (
    "You are a non-agentic JSON/data transformation engine. Use only the user's "
    "prompt as context. Return only the requested machine-readable data, with no commentary."
)


def pure_text_call_options(*, effort: str | None = None) -> dict[str, Any]:
    """Options for bounded prompt-in/result-out calls."""
    opts: dict[str, Any] = {
        "tools": "",
        "safe_mode": True,
        "no_chrome": True,
        "no_session_persistence": True,
        "system_prompt": PURE_TEXT_SYSTEM_PROMPT,
    }
    if effort is not None:
        opts["effort"] = effort
    return opts


def pure_json_call_options(*, effort: str | None = "low") -> dict[str, Any]:
    """Options for small deterministic classification / extraction calls."""
    opts = pure_text_call_options(effort=effort)
    opts["system_prompt"] = PURE_JSON_SYSTEM_PROMPT
    return opts


def record_model_provenance(
    book_dir: Path | None, *, phase: str, step: str, model: str, fallback: bool = False
) -> None:
    """Append one row naming which model authored this call."""
    if book_dir is None:
        return
    try:
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
            fh.write(json.dumps(row) + "\n")
    except Exception as e:
        sys.stderr.write(f"[record_model_provenance] skipped: {e!r}\n")


def dump_failed_call(book_dir: Path | None, *, step: str, prompt: str, stdout: Any, stderr: Any) -> str | None:
    """Write full failed-call evidence to a sidecar, never into the success path."""
    try:
        from _progress import current_run_id, init_run_log, run_log_path

        if not current_run_id():
            init_run_log(book_dir)
        base = run_log_path()
        if base is None:
            return None
        safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (step or "call"))[:60]
        stamp = time.strftime("%H%M%S", time.gmtime())
        digest = hashlib.sha256(prompt.encode("utf-8", "replace")).hexdigest()[:10]
        p = Path(base).parent / f"{Path(base).stem}.{safe}-{stamp}-{digest}.failure.txt"
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
                    _stream_text(stdout),
                    "",
                    "===== STDERR =====",
                    _stream_text(stderr),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return str(p)
    except Exception as e:
        sys.stderr.write(f"[dump_failed_call] skipped: {e!r}\n")
        return None


def log_claude_p(
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
        sys.stderr.write(f"[log_claude_p] dropped {event!r}: {e!r}\n")


def call_diagnostics(
    *,
    timeout: int,
    tools: str | None,
    safe_mode: bool,
    no_chrome: bool,
    no_session_persistence: bool,
    effort: str | None,
    system_prompt: str | None,
) -> dict[str, Any]:
    """Fields shared by success and failure timeline events."""
    return {
        "timeout_s": timeout,
        "execution_mode": _execution_mode(
            tools=tools,
            safe_mode=safe_mode,
            no_chrome=no_chrome,
            no_session_persistence=no_session_persistence,
        ),
        "tool_mode": _tool_mode(tools),
        "safe_mode": safe_mode,
        "no_chrome": no_chrome,
        "no_session_persistence": no_session_persistence,
        "effort": effort,
        "system_prompt_sha256": (
            hashlib.sha256(system_prompt.encode("utf-8", "replace")).hexdigest()[:16]
            if system_prompt is not None
            else None
        ),
    }


def _stream_text(v: Any) -> str:
    if v is None:
        return "(none)"
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


def _execution_mode(*, tools: str | None, safe_mode: bool, no_chrome: bool, no_session_persistence: bool) -> str:
    if tools == "" and safe_mode and no_chrome and no_session_persistence:
        return "isolated"
    return "agentic"


def _tool_mode(tools: str | None) -> str:
    if tools is None:
        return "default-authoring-tools"
    if tools == "":
        return "none"
    return "custom"
