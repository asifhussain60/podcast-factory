#!/usr/bin/env python3
"""_vowel_gemini.py — the metered Gemini transport the vowelling passes share.

Split out of `vowel_book.py` (DR-005, 2026-09-04) when the retry, the failure
classification and the character meter took that file past its 600-line ceiling.
Same split as `_illustrate_resume.py` beside `_book_illustrate.py`: the thing
extracted is the one with its own reason to exist, and `vowel_book` re-exports
every name so no caller had to move.

Three things live here because they are one decision each, and each one was got
wrong before:

  A CALL IS RETRIED, NOT REPORTED. Throttling and the 5xx family are re-sent with
  capped backoff; a 4xx that is not 429 is not, because a bad request will not
  become a good one. The transport is `_azure_http._http_retry` — stdlib urllib,
  nothing in it Azure-specific — rather than a second backoff implementation.

  A FAILED CALL IS NOT A VERDICT ON THE ARABIC. `GeminiCallFailed` and
  `MODEL_ERROR_PREFIX` are what let the caller tell "there was no answer" from
  "the answer was wrong about the text", and retry them differently.

  WHAT WAS ASKED IS WHAT IS BILLED. The meter counts at the transport rather than
  at the five call sites, because only one of the five ever counted, and a
  throttled attempt is deliberately not counted — it never reached the model.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODEL = "gemini-2.5-pro"
"""Vocalisation is a reasoning task, not a lookup: the reading of an ambiguous
verb comes from the surrounding sense. Flash guesses; Pro deliberates."""

_METER_LOCK = threading.Lock()
#: Characters actually SENT TO and RETURNED BY the API, across every call this
#: module makes, from every thread. Counted here rather than at the call sites
#: because there are five of them — the run sweep, its headroom retry, the
#: salvage pass, the lexical sweep and the glossary — and only the first was ever
#: counted, so a book's recorded Gemini spend was short by everything else.
_METER = {"in_chars": 0, "out_chars": 0}


def meter_reading() -> dict[str, int]:
    """A snapshot of the running totals. Subtract two to bill one pass."""
    with _METER_LOCK:
        return dict(_METER)


def _bill_since(before: dict[str, int], stats: dict) -> None:
    now = meter_reading()
    for key in ("in_chars", "out_chars"):
        stats[key] = stats.get(key, 0) + now[key] - before.get(key, 0)


#: Marks a refusal that is a FAILED CALL rather than the vowelling gate's verdict.
#: The two travel in the same list because both end a run's first attempt, but they
#: are retried differently: a gate refusal is re-asked in fragments (only the piece
#: holding the disputed letter stays bare), while a failed call is simply asked
#: again, whole — nothing about the text was ever in question. It is a string
#: because it is also the wire format that reaches `book-vowelling.json`, where a
#: human reads why a passage is bare.
MODEL_ERROR_PREFIX = "model error: "


class GeminiCallFailed(RuntimeError):
    """The call did not produce a reply — which is NOT a verdict on the Arabic.

    Kept distinct from a vowelling-gate refusal on purpose. A gate refusal says
    the answer was wrong about the text; this says there was no answer. Recording
    the second as the first is what let a throttled run ship bare with its report
    blaming the passage.
    """


def _gemini(system: str, user: str, *, model: str = MODEL, max_output_tokens: int = 4000) -> str:
    """One vocalisation call, re-sent on 429/5xx.

    Transport is `_azure_http._http_retry` — stdlib urllib with capped backoff
    that honours `Retry-After`. Nothing in that helper is Azure-specific; it is
    named for where it was extracted from, and borrowing it is the alternative to
    a second backoff implementation that would drift from the first.

    Throttling used to travel out of here as an HTTPError, and the pool that fans
    these calls out recorded it as `model error: HTTP Error 429` — a refusal the
    salvage pass then skipped, because salvage re-asks what the GATE turned away.
    A throttled book shipped bare Arabic and blamed the text for it.
    """
    from _azure_http import _http_retry
    from _secrets import get_gemini_key

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={get_gemini_key()}"
    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            # Temperature near zero: vocalising a fixed text is not a creative
            # task, and the same passage should come back the same way twice.
            # The token budget is headroom for 2.5 Pro's thinking, which is drawn
            # from this same allowance -- a tight budget returns an empty answer.
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_output_tokens},
        }
    ).encode()
    status, _headers, raw = _http_retry(
        "POST", url, headers={"Content-Type": "application/json"}, body=body, timeout=300
    )
    if status != 200:
        raise GeminiCallFailed(f"HTTP {status}: {raw.decode('utf-8', 'replace')[:200]}")
    data = json.loads(raw)
    # 2.5 Pro draws its thinking from the SAME token allowance as the answer, so a
    # long run can return a candidate carrying only thought parts, or no `parts`
    # key at all. Indexing straight into `parts[0]["text"]` raised KeyError on
    # those and they were recorded as "model error: 'parts'" — a spurious refusal
    # of a passage nothing was actually wrong with. Read the first non-thought
    # part instead, and treat an answerless response as empty so the caller can
    # retry it with more room.
    answer = ""
    for candidate in data.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            if part.get("thought"):
                continue
            text = part.get("text", "")
            if text.strip():
                answer = text
                break
        if answer:
            break
    # Billed here rather than by the caller: a reply that came back answerless was
    # still paid for, and so was every headroom retry. A throttled attempt is NOT
    # billed — it never reached the model — which is why this sits past the status
    # check and not inside the transport.
    with _METER_LOCK:
        _METER["in_chars"] += len(user)
        _METER["out_chars"] += len(answer)
    return answer


def _ask_with_headroom(system: str, run: str) -> str:
    """One vocalisation, retried once with a bigger budget if it came back empty.

    An empty answer from 2.5 Pro nearly always means thinking consumed the token
    allowance rather than that the passage is unvowellable, and the runs it
    happens on are the long ones — exactly the passages worth having.
    """
    out = _clean(_gemini(system, run))
    if out:
        return out
    return _clean(_gemini(system, run, max_output_tokens=12000))


def _clean(raw: str) -> str:
    """Models like to wrap a one-line answer in a fence or quotes."""
    text = raw.strip().removeprefix("```").removesuffix("```").strip()
    for line in text.splitlines():
        stripped = line.strip().strip("\"'«»")
        if stripped and any("؀" <= c <= "ۿ" for c in stripped):
            return stripped
    return ""
