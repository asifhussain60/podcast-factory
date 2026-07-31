"""_book_bridges.py — orientation sentences that survive a re-compose.

The comprehension review finds terms the book leans on before it explains them.
The fix Asif approved is a BRIDGE, never a reorder: one sentence of orientation
where the term first lands, leaving the source's order untouched.

The naive fix — edit ``book/book.md`` — is erased by the next compose, which
regenerates that file from the source. A converged book would silently un-converge
the first time anything upstream re-ran. So a bridge is stored in a durable
sidecar (``_system/comprehension-bridges.json``) and INJECTED into book.md as a
pipeline step, the same shape as the editorial asides: fenced, idempotent, and
replayed on every compose.

Two properties this leans on:

  * IDEMPOTENT — injection strips its own previous output before re-inserting, so
    running it twice leaves the same file. Convergence loops re-enter constantly.
  * ANCHORED BY QUOTE, not by offset. The re-voice rewrites prose; a line number
    would rot the moment anything upstream changed, and a bridge would land in the
    wrong paragraph without anyone noticing. An anchor that no longer matches is
    reported and skipped — never guessed at.

Pure apart from reading/writing those two files. No LLM: the sentences are
authored by the reviewer, this module only places them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _book_fences import span_re

BRIDGE_OPEN = "<!-- bridge:begin -->"
BRIDGE_CLOSE = "<!-- bridge:end -->"
# Consumes the blank-line runs on BOTH sides of the fence, not just the trailing
# one. Stripping only the trailing run leaves the leading separator behind as
# residue; the next injection then adds its OWN separator on top, and the blank
# lines around a bridge grow by one on every compose. Normalizing the whole match
# (fence plus its surrounding whitespace) to a single paragraph break is what
# makes strip -> inject a true round trip instead of a slow leak.
# Matches the bare-marker form as well — see `_book_fences`.
_BRIDGE_SPAN_RE = span_re("bridge", leading=r"\n*", trailing=r"\n*")

# A bridge is one sentence. Longer and it stops being a handhold and becomes a
# digression that competes with the passage it was meant to open.
_MAX_BRIDGE_WORDS = 45
_MIN_BRIDGE_WORDS = 6


def sidecar_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "comprehension-bridges.json"


def read_bridges(book_dir: Path) -> list[dict[str, Any]]:
    """Every stored bridge. A missing or unreadable sidecar means none."""
    path = sidecar_path(book_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("bridges") if isinstance(data, dict) else data
    return [b for b in items if isinstance(b, dict)] if isinstance(items, list) else []


def write_bridges(book_dir: Path, bridges: list[dict[str, Any]]) -> Path:
    """Replace the sidecar. The reviewer owns this list; injection only reads it."""
    path = sidecar_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "book.comprehension-bridges/v1", "bridges": bridges}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def gate_bridge(bridge: dict[str, Any]) -> tuple[bool, list[str]]:
    """Accept or reject one bridge before it can reach the page.

    A bridge is additive orientation. It may not carry a claim the book does not
    already make, and this cannot check that — but it CAN refuse the shapes that
    are never right: empty, essay-length, or a rewrite masquerading as a bridge.
    """
    reasons: list[str] = []
    text = " ".join(str(bridge.get("text") or "").split())
    words = text.split()
    if not str(bridge.get("term") or "").strip():
        reasons.append("no term — a bridge exists to orient a specific word")
    if not str(bridge.get("anchor") or "").strip():
        reasons.append("no anchor — nothing to attach it to")
    if len(words) < _MIN_BRIDGE_WORDS:
        reasons.append("too short to orient anyone")
    elif len(words) > _MAX_BRIDGE_WORDS:
        reasons.append(f"a bridge is one sentence ({len(words)}>{_MAX_BRIDGE_WORDS} words)")
    if re.search(r"\b(chapter \d|see page|as discussed|later in this book)\b", text, re.I):
        reasons.append("cross-reference instead of orientation — the reader needs the meaning here, now")
    return (not reasons), reasons


def strip_bridges(book_md: str) -> str:
    """Remove every previously injected bridge, normalizing its whitespace to one
    blank line. What makes strip -> inject a true round trip rather than a leak."""
    return _BRIDGE_SPAN_RE.sub("\n\n", book_md)


def format_bridge(text: str) -> str:
    """One bridge, fenced so it is findable and removable, styled as a quiet aside.

    A ``>`` blockquote line, like the editorial-note fences it sits beside — the
    renderer already turns a ``> `` paragraph into a bordered aside with no CSS
    change needed. Italicized so it never reads as the book's own voice: a bridge
    is orientation, not a claim the author is making.

    LABELLED, for the same reason the editorial notes are. An unattributed italic
    aside inside a speaker's discourse leaves a reader nothing but the italics to
    tell him it is not the book talking, and `the-master-and-the-disciple`
    promises in its own front matter that he can always tell the two apart.

    Curly quotation marks are folded to straight ones because the book sets every
    other quotation straight; two asides in smart quotes are visibly foreign on
    the printed page. Cheaper to normalize here than to police every author.
    """
    body = " ".join(text.split())
    for curly, straight in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'")):
        body = body.replace(curly, straight)
    return f"{BRIDGE_OPEN}\n> **A note for the reader.** *{body}*\n{BRIDGE_CLOSE}"


def inject(book_md: str, bridges: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Place each bridge beside the paragraph its anchor names.

    After it by default. ``placement: "before"`` puts it above instead, which a
    paragraph ending in a colon requires: the chapter-4 orientation note landed
    between "so that He says to whatever He wills:" and the verse that answers it,
    severing the book's most famous sentence from its own verb. Orientation that
    has to precede the passage it orients is not a special case worth a second
    mechanism, just a field.

    Returns the new markdown and the list of bridges that could NOT be placed —
    an anchor the prose no longer contains is reported, never approximated.
    """
    text = strip_bridges(book_md)
    unplaced: list[dict[str, Any]] = []
    for bridge in bridges:
        ok, _ = gate_bridge(bridge)
        anchor = " ".join(str(bridge.get("anchor") or "").split())
        if not ok or not anchor:
            unplaced.append(bridge)
            continue
        index = _find_anchor(text, anchor)
        if index is None:
            unplaced.append(bridge)
            continue
        if str(bridge.get("placement") or "after").lower() == "before":
            cut = text.rfind("\n\n", 0, index)
            cut = 0 if cut == -1 else cut
        else:
            cut = text.find("\n\n", index)
            cut = len(text) if cut == -1 else cut
        # A fixed separator on each side, built from content trimmed of ITS OWN
        # edge whitespace — the insertion point can never accumulate blank lines
        # no matter how many times a bridge here is stripped and re-placed.
        head = text[:cut].rstrip("\n")
        tail = text[cut:].lstrip("\n")
        text = head + "\n\n" + format_bridge(str(bridge["text"])) + ("\n\n" + tail if tail else "\n")
    return text, unplaced


def _find_anchor(text: str, anchor: str) -> int | None:
    """Locate the anchor in the prose, tolerating whitespace and markdown emphasis.

    Exact-match first; then a whitespace-flattened search, because the anchor was
    captured from a PDF where line wrapping differs from the markdown source.
    """
    if anchor in text:
        return text.index(anchor)
    flat_anchor = re.sub(r"[*_`]", "", anchor).lower()
    flat_text = re.sub(r"[*_`]", "", text).lower()
    position = flat_text.find(flat_anchor)
    return position if position != -1 else None


def apply_bridges(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Inject the stored bridges into book.md. Idempotent; safe on every compose."""
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    bridges = read_bridges(book_dir)
    if not book_md.exists() or not bridges:
        return {"applied": 0, "unplaced": []}
    text, unplaced = inject(book_md.read_text(encoding="utf-8"), bridges)
    book_md.write_text(text, encoding="utf-8")
    applied = len(bridges) - len(unplaced)
    log(f"    bridges: {applied} placed, {len(unplaced)} unplaced")
    for bridge in unplaced:
        log(f"      ! {bridge.get('term')}: anchor no longer in the prose — bridge skipped")
    return {"applied": applied, "unplaced": unplaced}


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import sys

    if len(sys.argv) != 2:
        print("usage: _book_bridges.py <BOOK_DIR>", file=sys.stderr)
        raise SystemExit(2)
    apply_bridges(Path(sys.argv[1]))
    raise SystemExit(0)
