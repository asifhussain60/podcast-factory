#!/usr/bin/env python3
"""Small Gemini text-generation helper with the repo's usual ledgers."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"


def call_gemini_text(
    prompt: str,
    *,
    book_dir: Path,
    phase: str,
    step: str,
    model: str = DEFAULT_GEMINI_TEXT_MODEL,
    system_prompt: str = "",
    timeout: int = 300,
    temperature: float = 0.35,
    max_output_tokens: int = 16000,
) -> str:
    """Call Gemini generateContent and append cost/provenance rows on success."""
    from _engine import ENGINE_GEMINI, TASK_REVOICE, engine_guard
    from _secrets import get_gemini_key

    engine_guard(TASK_REVOICE, ENGINE_GEMINI)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={get_gemini_key()}"
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Gemini returned no text: {json.dumps(data)[:500]}") from exc

    _record_ledgers(
        book_dir,
        phase=phase,
        step=step,
        model=model,
        in_chars=len(prompt) + len(system_prompt),
        out_chars=len(text or ""),
    )
    return (text or "").strip()


def _record_ledgers(book_dir: Path, *, phase: str, step: str, model: str, in_chars: int, out_chars: int) -> None:
    try:
        from _cost_ledger import append_gemini_cost

        append_gemini_cost(
            book_dir=book_dir,
            phase=phase,
            step=step,
            model=model,
            in_chars=in_chars,
            out_chars=out_chars,
        )
    except Exception as exc:  # pragma: no cover - ledger failure must not lose text
        print(f"    WARN: Gemini cost-ledger append failed: {exc}", file=sys.stderr)
    try:
        from _authoring._core import record_model_provenance

        record_model_provenance(book_dir, phase=phase, step=step, model=model, fallback=True)
    except Exception as exc:  # pragma: no cover
        print(f"    WARN: Gemini provenance append failed: {exc}", file=sys.stderr)
