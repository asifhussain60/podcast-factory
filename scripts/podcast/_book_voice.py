"""0book-voice — the author-companion re-voice pass (v2).

Runs ONLY when ``book_voice == author_companion`` under the ``book_pipeline_v2``
flag. It restyles the faithful base prose into the author's intimate first-person
register WITHOUT changing what is taught. It is independent of augmentation (it
runs on the base body only; editorial asides are not re-voiced).

Accuracy veto (the whole reason this is a gated pass, not a free rewrite):
each re-voiced chapter must survive three deterministic gates before it replaces
the base chapter —

  1. teaching-loss (``_literary.teaching_loss_findings``): no dropped teaching;
  2. Arabic preservation: the re-voice keeps at least as many Arabic script runs
     as the base (a printed edition must not lose its Arabic quotations);
  3. doctrinal (``_doctrinal.run_doctrinal_checks``): no NEW P0 the base did not
     already have.

A chapter that fails any gate is REVERTED to its faithful base text — a re-voice
is never allowed to regress fidelity. The single LLM call is isolated in
``_revoice_chapter`` so the gate + revert logic is unit-testable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_compose import _arabic_run_count
from _doctrinal import run_doctrinal_checks
from _literary import teaching_loss_findings

_VOICE_TIMEOUT = 900
_CHAPTER_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
# Editorial asides (from 0book-augment) are NOT re-voiced — skip these spans.
_EDITORIAL_SPAN_RE = re.compile(
    r"<!-- editorial:begin -->.*?<!-- editorial:end -->\n?", re.DOTALL
)


def _voice_prompt(title: str, base_text: str) -> str:
    return f"""You are the author of this Islamic teaching text, preparing a modern reading edition of
your own work. Re-voice the chapter below into your intimate, direct first-person register.

ABSOLUTE FAITHFULNESS
Preserve every teaching, argument, example, named person, citation, Quran verse, hadith, quote, and
Arabic script exactly as given. Keep every Arabic-script quotation verbatim (do not romanize it away,
do not drop it). You may modernize connective prose and warm the tone; you may NOT add, remove,
summarize, or alter any teaching. Output must be about the same length as the input — never shorter.

REGISTER
Contemporary literary English, first person, addressed warmly to the reader. No archaic diction, no
podcast language, no meta-commentary, no headings. Write the chapter, not about it.

OUTPUT
Return ONLY the re-voiced chapter prose. No title line, no preamble, no code fences.

CHAPTER "{title}"
{base_text}"""


def _revoice_chapter(title: str, base_text: str, book_dir: Path, label: str, log) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns re-voiced prose or ''."""
    rc, out, err = _run_claude_p_with_retry(
        _voice_prompt(title, base_text), timeout=_VOICE_TIMEOUT, book_dir=book_dir,
        phase="0book-voice", step=label, log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-voice",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run 0book-voice; each chapter is idempotent.",
        )
    return (out or "").strip()


def revoice_gates(base_text: str, revoiced: str) -> list[str]:
    """Deterministic fidelity gates. Empty list => the re-voice may be kept."""
    findings: list[str] = []
    if not revoiced.strip():
        return ["empty re-voice output"]
    # Anti-abridgement: a re-voice must be about the same length, never a summary.
    base_words = len(base_text.split())
    if base_words >= 8 and len(revoiced.split()) < 0.6 * base_words:
        findings.append(
            f"abridged re-voice ({len(revoiced.split())}<{round(0.6 * base_words)} words)"
        )
    findings.extend(teaching_loss_findings(base_text, revoiced))
    if _arabic_run_count(revoiced) < _arabic_run_count(base_text):
        findings.append(
            f"Arabic runs dropped ({_arabic_run_count(revoiced)}<{_arabic_run_count(base_text)})"
        )
    base_p0 = {f.signature for f in run_doctrinal_checks(base_text) if f.severity == "P0"}
    new_p0 = [
        f for f in run_doctrinal_checks(revoiced)
        if f.severity == "P0" and f.signature not in base_p0
    ]
    if new_p0:
        findings.append(
            "new doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in new_p0[:3])
        )
    return findings


def _fluency_prompt(title: str, base_text: str) -> str:
    return f"""You are polishing one chapter of a faithful Islamic reading edition into fluent,
idiomatic modern English. This is a de-calque pass: fix stiff, word-for-word-from-Arabic
phrasing so it reads like a book, NOT like a literal gloss.

ABSOLUTE FAITHFULNESS (a de-calque is not a rewrite)
Keep the SAME meaning, the SAME third-person scholarly register, and every teaching, argument,
named person, citation, Quran verse, hadith, quote, and Arabic script exactly as given. Keep every
Arabic-script quotation verbatim. You may only smooth connective prose and Arabic word-order that
reads awkwardly in English. Do not switch to first person, do not add, remove, summarize, or
reinterpret anything. Output must be about the same length — never shorter.

OUTPUT
Return ONLY the polished chapter prose. No title line, no preamble, no code fences.

CHAPTER "{title}"
{base_text}"""


def _fluency_chapter(title: str, base_text: str, book_dir: Path, label: str, log) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns polished prose or ''."""
    rc, out, err = _run_claude_p_with_retry(
        _fluency_prompt(title, base_text), timeout=_VOICE_TIMEOUT, book_dir=book_dir,
        phase="0book-fluency", step=label, log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-fluency",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run the fluency pass; each chapter is idempotent.",
        )
    return (out or "").strip()


def apply_fluency_adapt(
    book_dir: Path, *, log=print, force: bool = False,
    adapter: Callable[..., str] | None = None,
) -> Path:
    """De-calque each chapter of the FAITHFUL base into fluent modern English.

    Book Pipeline v2 runs this over the faithful-voice base (author_companion books
    get fluency from their re-voice pass instead). It reuses the same fidelity
    gates as the re-voice pass: a chapter that drops a teaching, loses Arabic, gains
    a doctrinal P0, or abridges is REVERTED to its base text. Editorial asides are
    left untouched. Returns the book.md path.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-fluency",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before the fluency pass.",
        )
    fn = adapter or _fluency_chapter
    text = book_md.read_text(encoding="utf-8")
    parts = _CHAPTER_HEADING_RE.split(text)
    out = [parts[0]]
    adapted = reverted = 0
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        asides = _EDITORIAL_SPAN_RE.findall(body)
        base_prose = _EDITORIAL_SPAN_RE.sub("", body).strip()
        try:
            candidate = fn(title, base_prose, book_dir, f"fluency-{i//2+1:02d}", log)
        except AuthoringError:
            raise
        except Exception as e:  # noqa: BLE001
            log(f"      fluency: {title!r} skipped (non-fatal): {e}")
            candidate = ""
        gate = revoice_gates(base_prose, candidate) if candidate else ["no candidate"]
        if gate:
            reverted += 1
            log(f"      fluency: {title!r} reverted to base ({'; '.join(gate[:2])})")
            new_body = base_prose
        else:
            adapted += 1
            new_body = candidate
        if asides:
            new_body = new_body.rstrip() + "\n\n" + "\n".join(a.strip() for a in asides)
        out.append(head + "\n\n" + new_body.strip() + "\n")
    new_text = (out[0].rstrip() + "\n\n" + "\n".join(out[1:])).strip() + "\n" if len(out) > 1 else text
    book_md.write_text(new_text, encoding="utf-8")
    (book_dir / "_system" / "book-fluency-report.json").write_text(
        json.dumps({"schema": "podcast.book-fluency/v1", "adapted": adapted, "reverted": reverted},
                   indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"    0book-fluency: {adapted} chapters de-calqued, {reverted} reverted to base")
    return book_md


def apply_author_companion_voice(
    book_dir: Path, *, log=print, force: bool = False,
    revoicer: Callable[..., str] | None = None,
) -> Path:
    """Re-voice each chapter of ``book/book.md`` into author-companion register.

    ``revoicer`` defaults to the real LLM call; tests inject a fake. A chapter
    that fails any fidelity gate is reverted to its faithful base. Editorial
    asides are preserved untouched. Returns the book.md path.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-voice",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before 0book-voice.",
        )
    fn = revoicer or _revoice_chapter
    text = book_md.read_text(encoding="utf-8")
    parts = _CHAPTER_HEADING_RE.split(text)  # [pre, head1, body1, head2, body2, ...]
    out = [parts[0]]
    revoiced = reverted = 0
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        asides = _EDITORIAL_SPAN_RE.findall(body)
        base_prose = _EDITORIAL_SPAN_RE.sub("", body).strip()
        try:
            candidate = fn(title, base_prose, book_dir, f"voice-{i//2+1:02d}", log)
        except AuthoringError:
            raise
        except Exception as e:  # noqa: BLE001 — one bad chapter reverts, never aborts
            log(f"      voice: {title!r} re-voice skipped (non-fatal): {e}")
            candidate = ""
        gate = revoice_gates(base_prose, candidate) if candidate else ["no candidate"]
        if gate:
            reverted += 1
            log(f"      voice: {title!r} reverted to base ({'; '.join(gate[:2])})")
            new_body = base_prose
        else:
            revoiced += 1
            new_body = candidate
        if asides:
            new_body = new_body.rstrip() + "\n\n" + "\n".join(a.strip() for a in asides)
        out.append(head + "\n\n" + new_body.strip() + "\n")
    new_text = (out[0].rstrip() + "\n\n" + "\n".join(out[1:])).strip() + "\n" if len(out) > 1 else text
    book_md.write_text(new_text, encoding="utf-8")
    (book_dir / "_system" / "book-voice-report.json").write_text(
        json.dumps({
            "schema": "podcast.book-voice/v1",
            "revoiced": revoiced,
            "reverted": reverted,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"    0book-voice: {revoiced} chapters re-voiced, {reverted} reverted to base")
    return book_md
