"""_book_opening.py — fold the source's own opening into chapter 1, on disk.

WHY THIS EXISTS SEPARATELY FROM THE ASSEMBLY
--------------------------------------------
`_translation_edition` already folds the opening when it COMPOSES a book. That
covers a book being written. It does not cover the five editions already written,
and reaching them through a compose is not a small cost — it is a re-translation.

Measured, on 2026-08-03, on `ayyuhal-walad`, whose front matter was the only thing
meant to change: every chunk was stale against a prompt fix from the day before,
so the whole book was re-translated, and the result lost 615 words of teaching
beyond the front matter and 38 quotation-length Arabic runs — Qur'an 53:39,
18:107, 25:70, 17:79, 7:50, 7:179, several hadith, and the entire closing
supplication of chapter 9. Nothing failed: the length gate passed, the fluency
pass reverted nothing, and the Arabic total barely moved because new runs
replaced the lost ones. That is the same shape as every defect this lane has
found — plausible output, no error, caught only by reading it against the source.

So the fold is available WITHOUT a model: this module moves the front-matter
section's prose into the first numbered chapter of a `book.md` already on disk,
and `_book_apparatus` runs it as a deterministic step. Same outcome as the
assembly's fold, no re-translation, no spend.

IDEMPOTENT, AND THE TWO PATHS COMPOSE
A book the assembly already folded has no front-matter section left, so this is a
no-op. A book this folded has none either, so a later compose folds at assembly
time and this stays a no-op. Neither can double.

RUN IT AFTER THE MACHINE PREFACE IS CLEARED, NOT BEFORE. The retired preface sits
INSIDE the front-matter section, so folding first would carry it into chapter 1 —
the one text this whole change exists to remove.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _book_edits import anchor_key

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
# A chapter of the book, as the assembly writes it: `## 3. The Hours Before Dawn`.
# Arabic-Indic and Persian digits are accepted for the same reason `anchor_key`
# accepts them — this is an Arabic-source project and a numbered heading may
# carry them.
_NUMBERED_RE = re.compile(r"^##\s+[0-9٠-٩۰-۹]+\.\s")


def preface_title(book_dir: Path) -> str:
    """The heading the front-matter section was emitted under, or ""."""
    toc = Path(book_dir) / "book" / "book-toc.json"
    if not toc.exists():
        return ""
    try:
        preface = json.loads(toc.read_text(encoding="utf-8")).get("preface") or {}
    except Exception:
        return ""
    return str(preface.get("title") or "") if isinstance(preface, dict) else ""


def fold_opening(book_md: str, title: str) -> tuple[str, int]:
    """Move the ``title`` section's body into the first numbered chapter.

    Returns the new markdown and how many words moved. Returns the input
    unchanged with 0 when there is no such section, when it is empty, or when
    there is no numbered chapter to fold into — losing the source's words to a
    book with no chapters is the one outcome worth refusing over.
    """
    if not title.strip():
        return book_md, 0
    key = anchor_key(title)
    parts = _HEADING_RE.split(book_md)
    if len(parts) < 3:
        return book_md, 0

    heads = [(i, parts[i]) for i in range(1, len(parts), 2)]
    front = next((i for i, h in heads if anchor_key(h) == key), None)
    if front is None:
        return book_md, 0
    chapter = next((i for i, h in heads if _NUMBERED_RE.match(h.strip())), None)
    if chapter is None:
        return book_md, 0

    opening = parts[front + 1].strip()
    if not opening:
        return book_md, 0

    body = parts[chapter + 1].strip()
    parts[chapter + 1] = "\n\n" + opening + "\n\n" + body + "\n"
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        if i == front:
            continue  # the section and its body leave together
        out.append(parts[i] + parts[i + 1] if i + 1 < len(parts) else parts[i])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n", len(opening.split())


def apply_opening_fold(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Fold the opening into chapter 1 in ``book/book.md``. Report-shaped."""
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"folded": False, "reason": "no book.md"}
    title = preface_title(book_dir)
    if not title:
        return {"folded": False, "reason": "no preface title in book-toc.json"}
    before = book_md.read_text(encoding="utf-8")
    after, words = fold_opening(before, title)
    if not words or after == before:
        return {"folded": False}
    book_md.write_text(after, encoding="utf-8")
    log(f"    opening: {title!r} folded into chapter 1 ({words} words), its heading dropped")
    return {"folded": True, "words": words, "title": title}
