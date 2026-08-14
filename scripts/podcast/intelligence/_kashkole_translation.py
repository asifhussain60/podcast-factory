"""Prompt, windowing, and quality gates for Kashkole translation."""

from __future__ import annotations

import re
import sqlite3

from _arabic_coverage import ARABIC_BODY, arabic_span_is_grounded

try:
    from _mushaf import is_quranic, mushaf_available
except Exception:  # pragma: no cover - the mirror may be absent on a fresh clone

    def mushaf_available() -> bool:
        return False

    def is_quranic(span: str) -> bool:
        return False


PROMPT_VERSION = "1.0"
WINDOW_CHARS = 3_500
WINDOW_THRESHOLD = 5_000
SHORT_RATIO = 0.60

INSTRUCTION = """\
You are rendering a passage of Urdu religious scholarship into English for a \
printed reading edition of the Ismaili wisdom corpus.

This is a TRANSLATION, and it is held to the same standard as the reading \
editions in this library. Follow every rule below exactly.

REGISTER (REQ-BA-010). Modern, lucid, simple English for a general reader, not a \
specialist. Every sentence understandable on first read. Prefer the plain word to \
the ornate one. Simple is not casual: the register stays dignified and bookish — \
no contractions, no marketing tone, no lecture or podcast voice.

DE-CALQUE (REQ-BA-020). Never carry Urdu or Arabic word order, pronoun chains or \
rhetorical scaffolding into the English. Split, merge and reorder sentences \
within a paragraph freely so the English reads as English.

MEANING IS INVARIANT (REQ-BA-030). Every teaching, argument, example, named \
person, citation and enumerated list survives intact. Add NOTHING — no outside \
facts, no modern analogies, no explanatory asides, no bracketed interpolations. \
Drop nothing, summarize nothing, reinterpret nothing.

QUOTATIONS ARE ARTIFACTS (REQ-BA-040). Direct speech, Qur'an verses, hadith, \
poetry and quoted sayings keep their boundaries, their speakers and their \
content. Never add, remove or re-point a speech tag.

ARABIC SCRIPT IS UNTOUCHABLE (REQ-BA-060). This is the rule that matters most \
here, because the source is itself in Arabic script. The URDU PROSE is what you \
translate. Any run of ARABIC quotation inside it — a Qur'an verse, a hadith, a \
prayer, an Arabic phrase the author is quoting rather than writing — is COPIED \
THROUGH VERBATIM, character for character, including its vowel marks. Never \
translate it away, never romanize it, never re-vowel it. Where the Urdu supplies \
a rendering of such a quotation, translate that rendering and keep the Arabic \
beside it.

IMAGERY (REQ-BA-050). Metaphors and parables keep their concrete images. Recast \
the grammar around an image; never replace the image with an abstraction.

TERMS (REQ-BA-070, -080). Render each technical term the same way every time it \
appears. Where an accepted English word carries the meaning, use it. Do not add \
new parenthetical transliterations; keep glosses the source already has.

LENGTH (REQ-BA-100). The English is approximately as long as the Urdu. A \
translation is a rewording, never an abridgement. Keep the paragraph structure of \
the source unless English demands otherwise.

SPELLING (REQ-BA-110). American spelling, the serial comma, periods and commas \
inside closing quotes.

OUTPUT. Return ONLY the English rendering. No preamble, no notes, no commentary, \
no markdown fences, no headings that are not in the source.
"""

TITLE_INSTRUCTION = """\
Render this Urdu topic title into a short, dignified English title for a printed \
reading edition. Modern, lucid English; title case; no trailing period; no \
transliteration in parentheses; no commentary. Return ONLY the title.
"""


def _context(row: sqlite3.Row) -> str:
    bits = []
    if row["binder"]:
        bits.append(f"Binder: {row['binder']}")
    if row["chapter"]:
        bits.append(f"Chapter: {row['chapter']}")
    if row["name"]:
        bits.append(f"Topic: {row['name']}")
    return "\n".join(bits)


def body_prompt(row: sqlite3.Row, window: str, *, part: int, total: int, tail: str) -> str:
    head = [INSTRUCTION, "", "--- CONTEXT (do not translate, for orientation only) ---", _context(row)]
    if total > 1:
        head += [
            "",
            f"This is part {part} of {total} of one topic. Translate ONLY the part "
            "given below. Do not summarize what came before and do not preview what "
            "comes after; the parts are joined verbatim.",
        ]
        if tail:
            head += [
                "",
                "The previous part ended with the following English, for continuity of "
                "terminology and voice. Do NOT repeat it:",
                tail,
            ]
    head += ["", "--- URDU SOURCE ---", window, "", "--- ENGLISH RENDERING ---"]
    return "\n".join(head)


_PARA_RE = re.compile(r"\n\s*\n")
_SENT_RE = re.compile(r"(?<=[۔.!?])\s+")


def windows_of(body: str, size: int = WINDOW_CHARS) -> list[str]:
    """Split a body at paragraph boundaries, falling back to sentences."""
    body = (body or "").strip()
    if len(body) <= WINDOW_THRESHOLD:
        return [body] if body else []

    units: list[str] = []
    for para in _PARA_RE.split(body):
        para = para.strip()
        if not para:
            continue
        if len(para) <= size:
            units.append(para)
            continue
        buf = ""
        for sent in _SENT_RE.split(para):
            if not sent.strip():
                continue
            if len(buf) + len(sent) + 1 > size and buf:
                units.append(buf.strip())
                buf = sent
            else:
                buf = f"{buf} {sent}".strip()
        if buf.strip():
            units.append(buf.strip())

    out: list[str] = []
    buf = ""
    for unit in units:
        if len(buf) + len(unit) + 2 > size and buf:
            out.append(buf.strip())
            buf = unit
        else:
            buf = f"{buf}\n\n{unit}".strip()
    if buf.strip():
        out.append(buf.strip())
    return out


_ARABIC_RUN_RE = re.compile(rf"[{ARABIC_BODY}]+(?:\s+[{ARABIC_BODY}]+)*")


def quranic_runs(text: str, *, min_words: int = 4) -> list[str]:
    """Return Arabic-script runs that the canonical mushaf recognizes."""
    if not mushaf_available():
        return []
    found: list[str] = []
    for run in _ARABIC_RUN_RE.findall(text or ""):
        if len(run.split()) < min_words:
            continue
        try:
            if is_quranic(run):
                found.append(run)
        except Exception:
            continue
    return found


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def check(source: str, rendered: str) -> tuple[str, list[str]]:
    """Return ``(status, concerns)`` for one rendering without raising."""
    concerns: list[str] = []
    src, out = _normalize(source), _normalize(rendered)
    if not out:
        return "failed", ["empty rendering"]

    ratio = len(out) / max(1, len(src))
    if ratio < SHORT_RATIO:
        concerns.append(f"abridged: rendering is {ratio:.0%} of the source")

    for run in quranic_runs(source):
        if not arabic_span_is_grounded(run, rendered):
            concerns.append(f"quranic run not carried through: {run[:40]}")

    status = "short" if any(c.startswith("abridged") for c in concerns) else "ok"
    if any(c.startswith("quranic") for c in concerns):
        status = "short" if status == "short" else "review"
    return status, concerns
