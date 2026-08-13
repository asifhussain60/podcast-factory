#!/usr/bin/env python3
"""Codex CLI text-generation helper backed by ChatGPT auth, not an API key."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_CODEX_BIN = "/Applications/ChatGPT.app/Contents/Resources/codex"


def call_codex_text(
    prompt: str,
    *,
    book_dir: Path,
    phase: str,
    step: str,
    model: str | None = None,
    system_prompt: str = "",
    timeout: int = 300,
) -> str:
    """Run a non-interactive Codex turn and append subscription usage ledgers."""
    codex_bin = _codex_bin()
    model = model or os.environ.get("PODCAST_FACTORY_CODEX_MODEL") or DEFAULT_CODEX_MODEL
    output_path = Path(tempfile.gettempdir()) / f"podcast-factory-codex-{uuid.uuid4().hex}.txt"
    full_prompt = _prompt(system_prompt, prompt)
    cmd = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "-C",
        tempfile.gettempdir(),
        "--skip-git-repo-check",
        "--json",
        "-m",
        model,
        "--output-last-message",
        str(output_path),
        "-",
    ]
    try:
        proc = subprocess.run(cmd, input=full_prompt, capture_output=True, text=True, timeout=timeout)
        text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"codex exec timed out after {timeout}s") from exc
    finally:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass

    if proc.returncode != 0:
        detail = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()[:600]
        raise RuntimeError(f"codex exec rc={proc.returncode}: {detail}")
    if not text:
        detail = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()[:600]
        raise RuntimeError(f"codex exec returned no text: {detail}")

    _record_ledgers(
        book_dir,
        phase=phase,
        step=step,
        model=model,
        usage=_usage_from_jsonl(proc.stdout),
    )
    return text


def _codex_bin() -> str:
    configured = os.environ.get("PODCAST_FACTORY_CODEX_BIN")
    if configured:
        return configured
    if Path(DEFAULT_CODEX_BIN).exists():
        return DEFAULT_CODEX_BIN
    found = shutil.which("codex")
    if found:
        return found
    raise RuntimeError("Codex CLI not found. Set PODCAST_FACTORY_CODEX_BIN to the codex executable.")


def _prompt(system_prompt: str, user_prompt: str) -> str:
    if not system_prompt:
        return user_prompt
    return (
        "System instruction for this isolated text transformation:\n"
        f"{system_prompt.strip()}\n\n"
        "User request:\n"
        f"{user_prompt}"
    )


def _usage_from_jsonl(stdout: str) -> dict[str, int]:
    usage: dict[str, int] = {}
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    total_input = int(usage.get("input_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or 0)
    cache_write = int(usage.get("cache_write_input_tokens") or 0)
    return {
        "input_tokens": max(0, total_input - cached),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "cache_read": cached,
        "cache_create": cache_write,
    }


def _record_ledgers(book_dir: Path, *, phase: str, step: str, model: str, usage: dict[str, int]) -> None:
    try:
        from _cost_ledger import CostRow, _now_iso

        row = CostRow(
            ts=_now_iso(),
            phase=phase,
            step=step,
            model=f"codex/{model}",
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cache_read=int(usage.get("cache_read") or 0),
            cache_create=int(usage.get("cache_create") or 0),
            cost_usd=0.0,
            engine="max",
        )
        ledger = Path(book_dir) / "_system" / "cost-ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(row)) + "\n")
    except Exception as exc:  # pragma: no cover - ledger trouble is never fatal
        print(f"    WARN: Codex cost-ledger append failed: {exc}", file=sys.stderr)
    try:
        from _authoring._core import record_model_provenance

        record_model_provenance(book_dir, phase=phase, step=step, model=f"codex/{model}", fallback=True)
    except Exception as exc:  # pragma: no cover
        print(f"    WARN: Codex provenance append failed: {exc}", file=sys.stderr)
