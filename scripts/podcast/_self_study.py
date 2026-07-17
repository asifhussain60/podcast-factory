"""_self_study.py — materialize book/book-self-study.md from book.md.

The render-time self-study layer (book-html.mjs, opt-in `selfStudy`) renders
labeled Contextual-note and Study-summary asides from HTML-comment fences. This
module GENERATES that content and injects the fences, producing a separate
``book/book-self-study.md`` — the base ``book/book.md`` is never mutated, so the
reading edition is untouched.

Two per-chapter blocks are added:

  * a source-grounded **Contextual note** — reuses the (fixed) 0book-augment
    enrichment: KB-atom-grounded, doctrinally gated, additive only; and
  * a **Study summary** — Decision 1 (2026-07-17): a LABELED study-summary is the
    explicit, scoped exception to the anti-summary rule. It is drawn ONLY from the
    chapter's own teaching (no outside content, no new claims) and passes a
    faithfulness gate before it is kept.

Both use ``claude -p`` (flat-rate; $0 tracked spend). Idempotent: regenerating
rebuilds book-self-study.md from the clean base each run.
"""
from __future__ import annotations

import re
from pathlib import Path

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_augment import (
    _CHAPTER_HEADING_RE,
    _chapter_body,
    _load_kb_atoms,
    _slug,
    format_editorial_block,
    gate_editorial_block,
    _generate_enrichment,
    _BLOCK_OPEN,
    _BLOCK_CLOSE,
    _MAX_BLOCK_WORDS,
    _MIN_BLOCK_WORDS,
)

# ─── Study-summary block contract (mirrors the editorial fence shape) ───────
SUMMARY_LABEL = "Study summary"
_SUMMARY_OPEN = "<!-- study-summary:begin -->"
_SUMMARY_CLOSE = "<!-- study-summary:end -->"
_SUMMARY_TIMEOUT = 900

# A summary that merely re-teaches, cites the future, or runs long is dropped.
_META_PHRASES = ("in this chapter", "the author", "this summary", "we will", "as we saw")


def format_summary_block(text: str) -> str:
    """Wrap a study summary in the canonical labeled + fenced block."""
    from _book_augment import _wrap_para
    body = " ".join((text or "").split())
    inner = "\n".join(f"> {line}" for line in _wrap_para(body))
    return f"{_SUMMARY_OPEN}\n> **{SUMMARY_LABEL}.** \n{inner}\n{_SUMMARY_CLOSE}"


def gate_summary(text: str) -> tuple[bool, list[str]]:
    """Deterministic accept/reject for one study summary. (accepted, reasons)."""
    reasons: list[str] = []
    body = " ".join((text or "").split())
    words = len(body.split())
    if not body or body.upper().startswith("NONE"):
        return False, ["empty/NONE"]
    if words < _MIN_BLOCK_WORDS:
        reasons.append(f"too short ({words}w)")
    if words > _MAX_BLOCK_WORDS:
        reasons.append(f"too long ({words}w)")
    low = body.lower()
    for phrase in _META_PHRASES:
        if phrase in low:
            reasons.append(f"meta/self-referential: {phrase!r}")
            break
    if body.count("#") or _SUMMARY_OPEN in body:
        reasons.append("contains markup")
    return (not reasons), reasons


def _summary_prompt(title: str, chapter_text: str) -> str:
    return f"""You are writing a short STUDY SUMMARY for a self-study reading edition — a study
aid printed as a clearly-labeled box after the chapter. It condenses what the chapter itself
teaches so a reader studying without a teacher can review the essentials.

Hard rules:
- Draw ONLY from the chapter below. Add nothing from outside it; introduce no new claim,
  ruling, name, citation, or example that is not already in the chapter.
- 2 to 4 sentences, plain declarative prose. No heading, no list, no preamble, no meta
  ("in this chapter", "the author"), no reference to other chapters.
- State the chapter's key teachings directly, as settled points — not a description of the
  chapter. If the chapter is too slight to summarize faithfully, output exactly: NONE

CHAPTER "{title}"
{chapter_text[:7000]}

Output only the summary prose, or NONE."""


def _generate_summary(title: str, chapter_text: str, book_dir: Path, label: str, log) -> str:
    rc, out, err = _run_claude_p_with_retry(
        _summary_prompt(title, chapter_text), timeout=_SUMMARY_TIMEOUT,
        book_dir=book_dir, phase="0book-self-study", step=label, log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-self-study",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run --self-study; passing chapters are idempotent.",
        )
    out = (out or "").strip()
    return "" if out.upper().startswith("NONE") else out


def _strip_all_fences(text: str) -> str:
    """Remove any prior editorial + study-summary fenced blocks (idempotency)."""
    for open_, close_ in ((_BLOCK_OPEN, _BLOCK_CLOSE), (_SUMMARY_OPEN, _SUMMARY_CLOSE)):
        text = re.sub(re.escape(open_) + r".*?" + re.escape(close_) + r"\n?", "",
                      text, flags=re.DOTALL)
    return text


def _insert_after_body(book_md: str, blocks_by_heading: dict[str, str]) -> str:
    """Append each chapter's combined block(s) immediately after that chapter's body."""
    sections = _CHAPTER_HEADING_RE.split(book_md)
    if len(sections) < 3:
        return book_md.rstrip() + "\n"
    result = sections[0].strip()
    for i in range(1, len(sections), 2):
        head = sections[i].strip()
        body = (sections[i + 1] if i + 1 < len(sections) else "").strip()
        chunk = f"{head}\n\n{body}" if body else head
        block = blocks_by_heading.get(head)
        if block:
            chunk = f"{chunk}\n\n{block.strip()}"
        result = f"{result}\n\n{chunk}" if result else chunk
    return result.strip() + "\n"


def build_self_study_markdown(
    book_dir: Path, *, log=print, with_notes: bool = True,
) -> Path:
    """Generate book/book-self-study.md from book/book.md. Returns its path."""
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-self-study",
            message=f"missing {book_md} — run 0book-compose first.",
            manual_fallback="Run 0book-compose (base) before --self-study.")

    text = _strip_all_fences(book_md.read_text(encoding="utf-8"))
    atoms = _load_kb_atoms() if with_notes else []
    headings = _CHAPTER_HEADING_RE.findall(text)

    blocks: dict[str, str] = {}
    summaries = notes = dropped = 0
    for head in headings:
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        chapter_text = _chapter_body(text, head)
        parts: list[str] = []

        if with_notes:
            try:
                note = _generate_enrichment(title, chapter_text, atoms, book_dir,
                                            f"note-{_slug(title)}", log)
            except AuthoringError:
                raise
            except Exception as e:  # noqa: BLE001
                note = ""
                log(f"      self-study: note for {title!r} skipped ({e})")
            if note:
                ok, reasons = gate_editorial_block(note)
                if ok:
                    parts.append(format_editorial_block(note)); notes += 1
                else:
                    dropped += 1
                    log(f"      self-study: dropped note for {title!r} ({'; '.join(reasons[:2])})")

        try:
            summary = _generate_summary(title, chapter_text, book_dir,
                                        f"summary-{_slug(title)}", log)
        except AuthoringError:
            raise
        except Exception as e:  # noqa: BLE001
            summary = ""
            log(f"      self-study: summary for {title!r} skipped ({e})")
        if summary:
            ok, reasons = gate_summary(summary)
            if ok:
                parts.append(format_summary_block(summary)); summaries += 1
            else:
                dropped += 1
                log(f"      self-study: dropped summary for {title!r} ({'; '.join(reasons[:2])})")

        if parts:
            blocks[head.strip()] = "\n\n".join(parts)

    out_md = book_dir / "book" / "book-self-study.md"
    out_md.write_text(_insert_after_body(text, blocks), encoding="utf-8")
    log(f"    0book-self-study: wrote {out_md.name} "
        f"({summaries} summaries, {notes} notes, {dropped} dropped, "
        f"{len(headings)} chapters)")
    return out_md
