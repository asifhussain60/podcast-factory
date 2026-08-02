"""_book_articulation_notes.py — parse the optional ``===ARTICULATION-NOTES===``
block (REQ-BA-160, docs/standards/book-articulation.md) off the end of an
articulation-pass candidate before it is gated or written to ``book.md``.

The block is how the fluency/rearticulate passes report an ambiguity, a passage
that may confuse a modern reader, or a term worth standardizing — WITHOUT writing
any of that into the chapter prose itself (REQ-BA-030 already forbids added
content; this is not an exception to it). Extraction happens once, in
``_book_voice._adapt_chapter_body``, before the fidelity gates run, so gates never
see the block and length checks are never thrown off by it. A block that survives
extraction (malformed, truncated output, future prompt drift) is a defect per
REQ-BA-160, not a feature — ``leaked_marker_findings`` feeds that into
``revoice_gates`` so the window reverts instead of shipping a leaked note.
"""

from __future__ import annotations

import re

_NOTES_BLOCK_RE = re.compile(
    r"\n?===ARTICULATION-NOTES===\s*\n(.*?)\n===END-NOTES===\s*$",
    re.DOTALL,
)
_NOTE_LINE_RE = re.compile(r"^(AMBIGUITY|COMPREHENSION|TERMINOLOGY):\s*(.+)$")

# Checked against the CLEANED candidate (after extraction) as a defensive
# belt-and-suspenders — matches this repo's existing gate style (e.g. the B4
# process-chatter check in _translation_text.py carries the same marker).
LEAK_MARKERS = ("===ARTICULATION-NOTES===", "[Editorial query")

EMPTY_NOTES = {"editorial_queries": [], "comprehension_flags": [], "terminology_notes": []}


def extract_articulation_notes(candidate: str) -> tuple[str, dict[str, list[str]]]:
    """Split a raw articulation-pass candidate into ``(clean_prose, notes)``.

    ``notes`` has keys ``editorial_queries``, ``comprehension_flags``,
    ``terminology_notes`` — each a list of strings, empty when the pass reported
    nothing. A missing or malformed block is a no-op: the candidate is returned
    unchanged and all three lists are empty, which is also what happens for
    routes/prompts (e.g. the author-companion re-voice pass) that never ask for
    notes in the first place.
    """
    match = _NOTES_BLOCK_RE.search(candidate or "")
    if not match:
        return candidate, dict(EMPTY_NOTES)
    clean = candidate[: match.start()].rstrip()
    body = match.group(1)
    notes: dict[str, list[str]] = {k: [] for k in EMPTY_NOTES}
    kind_to_key = {
        "AMBIGUITY": "editorial_queries",
        "COMPREHENSION": "comprehension_flags",
        "TERMINOLOGY": "terminology_notes",
    }
    for line in body.splitlines():
        m = _NOTE_LINE_RE.match(line.strip())
        if not m:
            continue
        text = m.group(2).strip()
        if text:
            notes[kind_to_key[m.group(1)]].append(text)
    return clean, notes


def leaked_marker_findings(text: str) -> list[str]:
    """REQ-BA-160 belt-and-suspenders: a marker surviving extraction reverts the window."""
    for marker in LEAK_MARKERS:
        if marker in (text or ""):
            return [f"leaked articulation-notes marker in output: {marker!r}"]
    return []
