"""_scholar_bridge.py — reach the Ismaili Scholar from Python.

The Scholar's grounding, persona, word cap, Qur'anic citation resolution and
etymology veto are TypeScript reading three SQLite files, and they belong to the
Explain button on the Book Composer. This module ASKS for them, over
``plan-dashboard/scripts/gem-card.mjs``, rather than reimplementing them here —
the same relationship the Podcast Factory Library has with the site's renderer.

Two calls with the model in between, and the model is the caller's:

    prepare(...)  -> what to send Claude, plus how well the passage grounded
    finish(...)   -> Claude's raw reply, turned into a card

Nothing here calls a model or writes a file. A bridge failure raises
``ScholarBridgeError`` with what the bridge said, so a driver can drop one finding
without losing a chapter.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from _paths import REPO_ROOT

_DASHBOARD = REPO_ROOT / "plan-dashboard"
_BRIDGE = _DASHBOARD / "scripts" / "gem-card.mjs"
#: Registers the resolver that lets Node import the site's own TypeScript. The
#: bridge imports it itself; naming it here too would be a second answer.
_TIMEOUT = 120


class ScholarBridgeError(RuntimeError):
    """The bridge could not answer. Carries whatever it managed to say."""


def _run(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not _BRIDGE.exists():
        raise ScholarBridgeError(f"bridge not found: {_BRIDGE}")
    try:
        proc = subprocess.run(
            ["node", str(_BRIDGE), command],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            cwd=str(_DASHBOARD),
        )
    except subprocess.TimeoutExpired as exc:
        raise ScholarBridgeError(f"{command}: timed out after {_TIMEOUT}s") from exc
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out.splitlines()[-1]) if out else {}
    except Exception as exc:
        raise ScholarBridgeError(f"{command}: unreadable reply ({(proc.stderr or out)[:200]})") from exc
    if not data.get("ok"):
        raise ScholarBridgeError(f"{command}: {data.get('error') or (proc.stderr or '')[:200]}")
    return data


def prepare(
    *,
    concept: str,
    context: str = "",
    chapter_context: str = "",
    book_title: str = "",
    question: str = "",
) -> dict[str, Any]:
    """Everything needed to ask the Scholar about one passage.

    Returns ``system`` and ``user`` (the turn), ``anchor`` (the card's title, so
    no Python copy of that rule exists), ``tightenSystem`` (the instruction for
    the second pass, travelling with the turn for the same reason), and
    ``grounded`` — how many knowledge-base atoms bore on the passage. Zero is the
    caller's cue: Asif's rule is that an ungrounded passage yields no card
    (2026-08-06), and checking it BEFORE the model runs is what makes that free.
    """
    return _run(
        "prepare",
        {
            "concept": concept,
            "context": context,
            "chapterContext": chapter_context,
            "bookTitle": book_title,
            "question": question,
        },
    )


def research(
    *,
    concept: str,
    context: str = "",
    chapter_context: str = "",
    book_title: str = "",
    question: str = "",
) -> dict[str, Any]:
    """Answer a passage the knowledge base cannot ground, from the open web.

    THE ONE PAID CALL in this lane, and the one place a model runs behind the
    bridge. It is Gemini with Google-Search grounding because ``claude -p`` here
    runs without WebSearch or WebFetch and cannot do it at all. Reached only when
    ``prepare`` reported no grounding — two passages of twenty-three on
    ``the-master-and-the-disciple``.

    Raises ``ScholarBridgeError`` when the search stood on nothing
    ("researched but unsourced"), which is Asif's rule rather than a technical
    limit: a best guess about a religious teaching, filed under a scholar's
    byline, is worse than no card.
    """
    return _run(
        "research",
        {
            "concept": concept,
            "context": context,
            "chapterContext": chapter_context,
            "bookTitle": book_title,
            "question": question,
        },
    )


def parse(*, raw: str) -> dict[str, Any]:
    """Claude's reply, read with the parser the Explain button uses.

    Its own call rather than the front of ``finish`` because there is work
    between them: the tightening pass runs on the PARSED body. Folding the two
    together handed the tightener the raw JSON envelope, and a reply the parser
    could not read came back out as a card beginning ``{"body": "…`` — filed,
    plausible-looking, and wrong (measured on this book, 2026-08-06).

    Raises ``ScholarBridgeError`` when the reply cannot be read, which is what
    makes that failure drop a finding instead of producing a card.
    """
    return _run("parse", {"raw": raw})


def finish(
    *,
    body: str,
    etymology: list[str] | None = None,
    tightened_raw: str = "",
    max_words: int | None = None,
) -> dict[str, Any]:
    """Bound the card, name its verses, drop any etymology the corpus refutes.

    ``tightened_raw`` is used only if it passes the articulation guards on the
    far side — every Arabic run and every citation kept, and no growth. It is an
    improvement, never a dependency.
    """
    payload: dict[str, Any] = {"body": body}
    if etymology:
        payload["etymology"] = etymology
    if tightened_raw:
        payload["tightenedRaw"] = tightened_raw
    if max_words:
        payload["maxWords"] = max_words
    return _run("finish", payload)
