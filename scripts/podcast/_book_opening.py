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


def preface_entry(book_dir: Path) -> dict[str, Any]:
    """The toc's ``preface`` entry, or {}."""
    toc = Path(book_dir) / "book" / "book-toc.json"
    if not toc.exists():
        return {}
    try:
        preface = json.loads(toc.read_text(encoding="utf-8")).get("preface") or {}
    except Exception:
        return {}
    return preface if isinstance(preface, dict) else {}


def preface_title(book_dir: Path) -> str:
    """The heading the front-matter section was emitted under, or ""."""
    return str(preface_entry(book_dir).get("title") or "")


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


def drop_opening(book_md: str, title: str) -> tuple[str, int]:
    """Remove the front-matter section outright. Returns the markdown and words."""
    if not title.strip():
        return book_md, 0
    key = anchor_key(title)
    parts = _HEADING_RE.split(book_md)
    if len(parts) < 3:
        return book_md, 0
    out = [parts[0]]
    dropped = 0
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if anchor_key(parts[i]) == key:
            dropped = len(body.split())
            continue
        out.append(parts[i] + body)
    if not dropped:
        return book_md, 0
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip() + "\n", dropped


def _forget_section(book_dir: Path, title: str, log) -> None:
    """The pass reports must stop naming a section the edition no longer has."""
    from _book_pass_reports import drop_section_from_reports

    drop_section_from_reports(book_dir, title, log=log)


def _coalesce(ranges: list[list[int]]) -> list[list[int]]:
    """Sort and merge overlapping/adjacent line ranges."""
    clean = sorted([int(a), int(b)] for a, b in (r for r in ranges if r and len(r) == 2))
    out: list[list[int]] = []
    for lo, hi in clean:
        if out and lo <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def absorb_preface_range(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Give chapter 1 the source lines the folded opening came from.

    THE FOLD IS NOT COMPLETE WITHOUT THIS, and the reason is not bookkeeping. Every
    downstream step that asks "which Arabic is this English?" reads a chapter's
    ``source_line_ranges`` from ``book-toc.json``: the crosswalk, and
    ``align_arabic_paragraphs``, which is what the paragraph mirror then acts on.
    Fold 436 words into chapter 1 and leave its range naming only the chapter's own
    lines, and the aligner is asked to place prose whose Arabic is not in the range
    it was given — so it does not fail, it places it WRONG.

    Measured on `the-master-and-the-disciple` (2026-08-03): the six folded
    paragraphs and the chapter's own first were all pinned to source paragraph 3,
    every one marked ``confidence: verified``, and the mirror — whose whole job is
    to merge English paragraphs that share an Arabic one — dutifully fused all
    seven into a single 623-word block.

    Idempotent: once ``preface.include`` is false there is nothing left to absorb.
    Also flips that flag, so a later compose neither re-emits the opening as its
    own section nor folds it a second time.
    """
    book_dir = Path(book_dir)
    toc_path = book_dir / "book" / "book-toc.json"
    if not toc_path.exists():
        return {"absorbed": False}
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    preface = toc.get("preface")
    chapters = toc.get("chapters") or []
    if not isinstance(preface, dict) or not preface.get("include") or not chapters:
        return {"absorbed": False}
    pf_ranges = preface.get("source_line_ranges") or []
    if not pf_ranges:
        return {"absorbed": False}

    first = chapters[0]
    merged = _coalesce(list(pf_ranges) + list(first.get("source_line_ranges") or []))
    first["source_line_ranges"] = merged
    preface["include"] = False
    toc_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"    opening: chapter 1 now covers source lines {merged} — the opening's Arabic included")
    return {"absorbed": True, "source_line_ranges": merged}


def apply_opening_fold(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Fold the opening into chapter 1 in ``book/book.md``. Report-shaped.

    The range absorption runs whether or not this call moved any prose, because
    the ASSEMBLY may have done the folding on a compose — in which case book.md
    arrives here already folded and only the toc is left to correct.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"folded": False, "reason": "no book.md"}
    preface = preface_entry(book_dir)
    title = str(preface.get("title") or "")
    if not title:
        return {"folded": False, "reason": "no preface title in book-toc.json"}

    # EXCLUDED means the book has no front matter, so book.md must not carry a
    # front-matter section either — the opening is DELETED rather than folded.
    #
    # The distinction is the one the plan drew per book: an opening that is the
    # source's own first words is folded into chapter 1, and an opening that is
    # ABOUT the book is dropped. `al-anwaar-al-lateefah` is the second kind, and
    # folding it proved the point rather than settling it: its 272 words are 158
    # about "what kind of book you are holding", wrapped in an invocation that
    # chapter 1 ALREADY opens with, so the fold printed the ta'awwudh and basmala
    # twice, four paragraphs apart.
    if not preface.get("include"):
        before = book_md.read_text(encoding="utf-8")
        after, words = drop_opening(before, title)
        if not words:
            return {"folded": False, "dropped": False}
        book_md.write_text(after, encoding="utf-8")
        log(f"    opening: {title!r} DELETED ({words} words) — book-toc.json excludes it")
        _forget_section(book_dir, title, log)
        return {"folded": False, "dropped": True, "words": words, "title": title}

    before = book_md.read_text(encoding="utf-8")
    after, words = fold_opening(before, title)
    if words and after != before:
        book_md.write_text(after, encoding="utf-8")
        log(f"    opening: {title!r} folded into chapter 1 ({words} words), its heading dropped")
    # The pass reports still name this section as a chapter of the book. It is not
    # one any more — its prose moved into chapter 1 — and a report describing a
    # document nobody has is what every gate downstream reads.
    #
    # Keyed on whether the section is ACTUALLY GONE from book.md rather than on
    # whether this call is what removed it, so it also corrects a book the assembly
    # folded, or one folded by an earlier run before this step existed. The one
    # case it must not fire on is a fold that was REFUSED — a front matter still on
    # the page is still a section, and `fold_opening` leaves it there when there is
    # no numbered chapter to fold into.
    section_gone = fold_opening(book_md.read_text(encoding="utf-8"), title)[1] == 0
    if section_gone:
        from _book_pass_reports import drop_section_from_reports

        drop_section_from_reports(book_dir, title, log=log)
    absorbed = absorb_preface_range(book_dir, log=log)
    if not words:
        return {"folded": False, "absorbed": absorbed.get("absorbed", False)}
    return {"folded": True, "words": words, "title": title, "absorbed": absorbed.get("absorbed", False)}
