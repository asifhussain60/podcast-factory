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

Long chapters are WINDOWED (2026-07-19). A chapter handed to the model whole is
capped by what one response can carry: the 7,258-word chapter of one live book
came back ~150 words under the anti-abridgement gate and reverted, and its
14,384-word neighbour came back 98.6% identical to its base — the model had
degraded into transcription, which no fidelity gate can catch because copying is
maximally faithful. Chapters over ``_LONG_CHAPTER_WORDS`` are therefore split at
paragraph boundaries into ``_WINDOW_WORDS``-sized windows, each re-voiced with
the tail of the previous window for continuity and gated against its OWN base, so
one stumbling passage costs that passage rather than the whole chapter. This
mirrors the translation composer, which has windowed long chapters on the same
4,500-word threshold since it shipped (``_translation_edition._LONG_CHAPTER_WORDS``).

This module also drives ``0book-fluency`` (``apply_fluency_adapt``), the automatic
articulation pass for every translation-edition book. It shares ``_run_pass`` /
``_adapt_chapter_body`` with this re-voice pass and with the on-demand Rearticulate
action (``rearticulate_chapter.py``); all three now build their LLM prompt from the
SAME ``_book_voice_prompts._articulation_prompt`` (fluency and rearticulate) or
``_voice_prompt`` (this pass), under the Book Articulation Standard
(``docs/standards/book-articulation.md``, REQ-BA-*). A pass built on
``_articulation_prompt`` may return a trailing ``===ARTICULATION-NOTES===`` block
instead of writing a note into the prose (REQ-BA-160);
``_extract_articulation_notes`` strips it before gating, so it never reaches
book.md, and files its lines into that chapter's pass record for human review.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Sequence

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_articulation_notes import EMPTY_NOTES, extract_articulation_notes, leaked_marker_findings
from _book_compose import _arabic_run_count
from _book_edits import anchor_key, edited_chapter_keys
from _book_fences import span_re
from _book_pass_reports import KEPT_STATUSES, STATUS_OVERWRITTEN, load_prior_records, merge_records
from _book_voice_prompts import _articulation_prompt, _voice_prompt
from _content_profile import source_language as _source_language
from _doctrinal import run_doctrinal_checks
from _literary import teaching_loss_findings
from _narrative import frame_findings, lecture_voice_counts
from _pipeline_flags import narrative_frame, narrator_subject
from _translation_text import _split_paragraphs, _trim_seam_overlap, subordinate_body_headings

_VOICE_TIMEOUT = 900
_CHAPTER_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")


# Editorial asides (from 0book-augment) are NOT re-voiced — skip these spans.
# Tolerant of the bare-marker form a Composer round-trip leaves behind: a span
# this pass cannot see is a span the model rewrites into the narrator's voice.
_EDITORIAL_SPAN_RE = span_re("editorial", trailing=r"\n?")

# Windowing thresholds. `_LONG_CHAPTER_WORDS` matches the translation composer's
# own long-chapter threshold; `_WINDOW_WORDS` sits under it so a split chapter
# always yields at least two substantive windows.
_LONG_CHAPTER_WORDS = 4500
_WINDOW_WORDS = 2500
# A trailing window smaller than this fraction of the target is folded back into
# its predecessor rather than shipped as a runt.
_RUNT_WINDOW_FRACTION = 0.4
# Output this similar to its input was not re-voiced — it was copied. Not a gate
# (reverting to base yields the same text); recorded so the report says so.
_NEAR_IDENTICAL_RATIO = 0.95


def _norm_for_ratio(text: str) -> str:
    return " ".join((text or "").split())


def _similarity(base_text: str, candidate: str) -> float:
    """Whitespace-normalised similarity, 0..1. Computed per window, never per
    whole chapter — SequenceMatcher degrades badly on very long inputs."""
    return SequenceMatcher(None, _norm_for_ratio(base_text), _norm_for_ratio(candidate)).ratio()


def _iter_prose_windows(text: str, *, target_words: int = _WINDOW_WORDS) -> list[str]:
    """Split chapter prose into paragraph-aligned windows of ~``target_words``.

    Paragraph-aligned so a window never opens or closes mid-thought, which is
    what makes the per-window fidelity gates meaningful.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []
    windows: list[str] = []
    current: list[str] = []
    current_words = 0
    for para in paragraphs:
        current.append(para)
        current_words += len(para.split())
        if current_words >= target_words:
            windows.append("\n\n".join(current))
            current, current_words = [], 0
    if current:
        if windows and current_words < target_words * _RUNT_WINDOW_FRACTION:
            windows[-1] = windows[-1] + "\n\n" + "\n\n".join(current)
        else:
            windows.append("\n\n".join(current))
    return windows


def _revoice_chapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns re-voiced prose or ''."""
    rc, out, err = _run_claude_p_with_retry(
        _voice_prompt(title, base_text, previous_tail, frame=frame, narrator=narrator),
        timeout=_VOICE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-voice",
        step=label,
        log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-voice",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run 0book-voice; each chapter is idempotent.",
        )
    return (out or "").strip()


# Narrator "announcing the telling" openings — a chapter must begin as a chapter,
# not with the narrator framing the act of narration itself (found live 2026-07-19:
# "Let me set down, as faithfully as I can, how my Master opened the matter...",
# 6 instances in one book alone). Searched only within the chapter's own opening
# window (first ~200 chars) — this voice is intentionally first-person and warm
# by design (see REGISTER above), so a broad first-person match would revert
# legitimate prose; only the specific "I am now going to narrate" framing move
# is forbidden, and it can land a few words into the opening sentence (e.g. "I
# held this book back... and I want to tell you why"), not only at position 0.
_NARRATIVE_OPENING_RE = re.compile(
    r"\b("
    r"let me (tell|set down|speak|recount|say)\b"
    r"|i want to tell you\b"
    r"|i shall (now )?(tell|recount|set down)\b"
    r"|before i (tell|set down|begin)\b"
    r"|allow me to (tell|recount|set down)\b"
    r")",
    re.IGNORECASE,
)


def narrative_opening_findings(text: str, base_text: str | None = None) -> list[str]:
    """Flag a chapter that opens by announcing the act of narration instead of
    starting as a chapter does. Checked only against the chapter's own opening.

    DIFFERENTIAL when ``base_text`` is given: the finding is reported only if the
    re-voice INTRODUCED the announcement. Every other gate in ``revoice_gates``
    already reads this way — abridgement measures against the base's word count,
    teaching-loss and the frame guards take both texts, dropped Arabic runs
    compares run counts, and new doctrinal P0s subtract the base's own. This one
    did not, and the asymmetry cost real work: *Ayyuhal Walad* chapter 2 opens
    "Let me tell you of a man among the Children of Israel" in al-Ghazali's own
    letter, so the model preserving that opening — exactly what faithfulness
    demands — was reverted as though it had invented it, and the chapter shipped
    un-articulated. A source that announces its own telling can otherwise never
    pass articulation at all.

    ``base_text=None`` keeps the older single-argument contract for unit tests
    that exercise the phrase-matching in isolation.
    """
    opening = text.strip()[:200]
    if not _NARRATIVE_OPENING_RE.search(opening):
        return []
    # The author already opened this way — preserving it is fidelity, not drift.
    if base_text is not None and _NARRATIVE_OPENING_RE.search(base_text.strip()[:200]):
        return []
    return [f"narrative-announcement opening: {opening[:120]!r}"]


def revoice_gates(
    base_text: str,
    revoiced: str,
    *,
    check_opening: bool = True,
    frame: str | None = None,
    narrator_subject: str = "",
) -> list[str]:
    """Deterministic fidelity gates. Empty list => the re-voice may be kept.

    ``check_opening`` is False for continuation windows of a split chapter — the
    narrative-opening rule is about how a CHAPTER opens, and a mid-chapter window
    that legitimately says "let me tell you" must not be reverted for it.

    ``frame`` adds the narrative guards from ``_narrative``: grammatical person,
    speech-tag integrity, Arabic-script retention, supplied diacritics, and
    enumeration survival. Passed by both routes; omitted only by unit tests that
    exercise the older gates in isolation.
    """
    findings: list[str] = []
    if not revoiced.strip():
        return ["empty re-voice output"]
    # Anti-abridgement: a re-voice must be about the same length, never a summary.
    base_words = len(base_text.split())
    if base_words >= 8 and len(revoiced.split()) < 0.6 * base_words:
        findings.append(f"abridged re-voice ({len(revoiced.split())}<{round(0.6 * base_words)} words)")
    findings.extend(teaching_loss_findings(base_text, revoiced))
    if check_opening:
        findings.extend(narrative_opening_findings(revoiced, base_text))
    if _arabic_run_count(revoiced) < _arabic_run_count(base_text):
        findings.append(f"Arabic runs dropped ({_arabic_run_count(revoiced)}<{_arabic_run_count(base_text)})")
    base_p0 = {f.signature for f in run_doctrinal_checks(base_text) if f.severity == "P0"}
    new_p0 = [f for f in run_doctrinal_checks(revoiced) if f.severity == "P0" and f.signature not in base_p0]
    if new_p0:
        findings.append("new doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in new_p0[:3]))
    if frame:
        findings.extend(frame_findings(base_text, revoiced, frame=frame, narrator_subject=narrator_subject))
    findings.extend(leaked_marker_findings(revoiced))
    return findings


def _adapt_chapter_body(
    title: str,
    base_prose: str,
    book_dir: Path,
    label: str,
    log,
    fn: Callable[..., str],
    *,
    noun: str,
    frame: str | None = None,
    narrator_subject: str = "",
) -> tuple[str, dict]:
    """Adapt one chapter body, windowing it when it is too long for a single call.

    Returns ``(new_body, record)``. Each window is gated against its own base and
    reverts alone, so a long chapter is never all-or-nothing. ``record`` documents
    what actually happened — the thing the old ``{revoiced, reverted}`` counters
    could not answer without forensics against the cost ledger.
    """
    base_words = len(base_prose.split())
    windows = (_iter_prose_windows(base_prose) if base_words > _LONG_CHAPTER_WORDS else [base_prose]) or [base_prose]
    kept_parts: list[str] = []
    gates: list[str] = []
    warnings: list[str] = []
    kept = 0
    tail = ""
    notes = {k: [] for k in EMPTY_NOTES}
    for idx, window in enumerate(windows, start=1):
        part_label = label if len(windows) == 1 else f"{label}-part-{idx:02d}"
        try:
            candidate = fn(
                title,
                window,
                book_dir,
                part_label,
                log,
                previous_tail=tail,
                frame=frame or "",
                narrator=narrator_subject,
            )
        except AuthoringError:
            raise
        except Exception as e:  # non-fatal: this window falls back to its base
            log(f"      {noun}: {title!r} {part_label} skipped (non-fatal): {e}")
            candidate = ""
        # REQ-BA-160: strip any trailing ===ARTICULATION-NOTES=== block BEFORE
        # gating, so length/fidelity checks never see it and it can never reach
        # book.md. A no-op for prompts (e.g. author-companion voice) that never
        # emit one.
        candidate, window_notes = extract_articulation_notes(candidate)
        gate = (
            revoice_gates(
                window,
                candidate,
                check_opening=idx == 1,
                frame=frame,
                narrator_subject=narrator_subject,
            )
            if candidate
            else ["no candidate"]
        )
        if gate:
            gates.extend(f"{part_label}: {g}" for g in gate)
            part = window
        else:
            kept += 1
            part = candidate
            for key, values in window_notes.items():
                notes[key].extend(values)
            if _similarity(window, candidate) >= _NEAR_IDENTICAL_RATIO:
                warnings.append(f"{part_label}: output near-identical to base — copied, not re-voiced")
        if kept_parts:
            part = _trim_seam_overlap(kept_parts[-1], part)
        kept_parts.append(part)
        tail = " ".join(part.split()[-80:])
    new_body = "\n\n".join(kept_parts).strip()
    status = "adapted" if kept == len(windows) else ("reverted" if kept == 0 else "partial")
    # R-NO-LECTURE-VOICE is removed by the PROMPT and only guarded differentially,
    # so the pass reports how much of it survived. Without the number, "the frame
    # converted" and "the book stopped sounding like a lecture" are indistinguishable
    # from the record — which is exactly how a converted `al-anwaar` chapter 1 was
    # reported as adapted while still saying "Hold that frame, and step now inside it".
    before_address, before_stage = lecture_voice_counts(base_prose)
    after_address, after_stage = lecture_voice_counts(new_body)
    record = {
        "title": title,
        "base_words": base_words,
        "output_words": len(new_body.split()),
        "windows": len(windows),
        "windows_kept": kept,
        "status": status,
        "gates": gates,
        "warnings": warnings,
        "lecture_voice_before": {"reader_address": before_address, "stage_directions": before_stage},
        "lecture_voice_after": {"reader_address": after_address, "stage_directions": after_stage},
        **notes,
    }
    if status == "reverted":
        log(f"      {noun}: {title!r} reverted to base ({'; '.join(gates[:2])})")
    elif status == "partial":
        log(f"      {noun}: {title!r} partial — {kept}/{len(windows)} windows kept ({'; '.join(gates[:2])})")
    for warning in warnings:
        log(f"      {noun}: {title!r} {warning}")
    return new_body, record


def _fluency_chapter(
    title: str,
    base_text: str,
    book_dir: Path,
    label: str,
    log,
    *,
    previous_tail: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns polished prose or ''."""
    lang = _source_language(book_dir)
    rc, out, err = _run_claude_p_with_retry(
        _articulation_prompt(title, base_text, previous_tail, frame=frame, narrator=narrator, source_language=lang),
        timeout=_VOICE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-fluency",
        step=label,
        log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-fluency",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run the fluency pass; each chapter is idempotent.",
        )
    return (out or "").strip()


# `_book_frontmatter.INTRO_HEADING`, as `anchor_key` sees it. Not imported, to
# keep this module free of a front-matter dependency; pinned by a test.
_INTRODUCTION_KEY = "introduction to the book"


def _run_pass(
    book_md: Path,
    fn: Callable[..., str],
    *,
    log,
    noun: str,
    label_prefix: str,
    only: Sequence[int] | None = None,
    frame: str | None = None,
    narrator_subject: str = "",
    force: bool = False,
) -> tuple[str, list[dict]]:
    """Walk book.md's ``##`` sections, adapting each selected one.

    ``only`` is a set of 1-based section numbers (matching the ``<prefix>-NN``
    step labels in the cost ledger). Sections outside it are passed through
    byte-identical — re-adapting already-adapted prose compounds, so a targeted
    re-run must be structurally unable to touch the chapters it is not fixing.

    A chapter the human has authored in the Book Composer is passed through the
    same way, for a stronger reason: the Composer is the singular path for
    PDF-bound chapter changes, so that prose is the author's, and re-voicing it
    would be paying a model to produce text the replay then discards. ``force``
    is the deliberate override — and it really does overwrite human chapters.
    """
    book_dir = book_md.parent.parent
    selected = set(only) if only else None
    authored = set() if force else edited_chapter_keys(book_dir)
    text = book_md.read_text(encoding="utf-8")
    parts = _CHAPTER_HEADING_RE.split(text)  # [pre, head1, body1, head2, body2, ...]
    out = [parts[0]]
    records: list[dict] = []
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        number = i // 2 + 1
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        # The edition's introduction is APPARATUS and no prose pass may touch it.
        # It is authored under the articulation register already, it has no source
        # to be faithful to, and the fidelity gates below judge a rendering of a
        # SOURCE — so running them over it would revert or rewrite on evidence
        # that does not apply.
        #
        # During a compose it is simply not there yet (the apparatus injects it
        # after this pass). Standalone, on a finished book, it IS there and is the
        # first `## ` section — so `only=[1]` means the introduction and not
        # chapter one, which is exactly the accident this prevents.
        if anchor_key(head) == _INTRODUCTION_KEY:
            out.append(head + "\n\n" + body.strip() + "\n")
            continue
        if anchor_key(head) in authored:
            log(f"      {label_prefix}-{number:02d}: {title} — Composer edit, not regenerated")
            records.append({"title": title, "status": "composer-edit", "windows": 0, "windows_kept": 0})
            out.append(head + "\n\n" + body.strip() + "\n")
            continue
        if selected is not None and number not in selected:
            records.append({"title": title, "status": "skipped", "windows": 0, "windows_kept": 0})
            out.append(head + "\n\n" + body.strip() + "\n")  # same shape as an adapted section
            continue
        asides = _EDITORIAL_SPAN_RE.findall(body)
        base_prose = _EDITORIAL_SPAN_RE.sub("", body).strip()
        new_body, record = _adapt_chapter_body(
            title,
            base_prose,
            book_dir,
            f"{label_prefix}-{number:02d}",
            log,
            fn,
            noun=noun,
            frame=frame,
            narrator_subject=narrator_subject,
        )
        records.append(record)
        if asides:
            new_body = new_body.rstrip() + "\n\n" + "\n".join(a.strip() for a in asides)
        out.append(head + "\n\n" + subordinate_body_headings(new_body).strip() + "\n")
    new_text = (out[0].rstrip() + "\n\n" + "\n".join(out[1:])).strip() + "\n" if len(out) > 1 else text
    return new_text, records


def apply_fluency_adapt(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    adapter: Callable[..., str] | None = None,
    only: Sequence[int] | None = None,
) -> Path:
    """De-calque each chapter of the FAITHFUL base into fluent modern English.

    Book Pipeline v2 runs this over the faithful-voice base (author_companion books
    get fluency from their re-voice pass instead). It reuses the same fidelity
    gates as the re-voice pass: a chapter that drops a teaching, loses Arabic, gains
    a doctrinal P0, or abridges is REVERTED to its base text — per window, so a long
    chapter is not all-or-nothing. Editorial asides are left untouched. ``only``
    restricts the pass to the given 1-based section numbers. Chapters authored in
    the Book Composer are passed through untouched unless ``force`` — which had been
    an accepted-and-ignored parameter until this became its meaning. Returns the
    book.md path.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-fluency",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before the fluency pass.",
        )
    frame = narrative_frame(book_dir)
    subject = narrator_subject(book_dir)
    log(f"    0book-fluency: narrative frame = {frame}")
    new_text, records = _run_pass(
        book_md,
        adapter or _fluency_chapter,
        log=log,
        noun="fluency",
        label_prefix="fluency",
        only=only,
        frame=frame,
        narrator_subject=subject,
        force=force,
    )
    book_md.write_text(new_text, encoding="utf-8")
    report_path = book_dir / "_system" / "book-fluency-report.json"
    records = merge_records(load_prior_records(report_path), records, edited_keys=edited_chapter_keys(book_dir))
    adapted = sum(1 for r in records if r["status"] in KEPT_STATUSES)
    reverted = sum(1 for r in records if r["status"] == "reverted")
    overwritten = sum(1 for r in records if r["status"] == STATUS_OVERWRITTEN)
    report_path.write_text(
        json.dumps(
            {
                "schema": "podcast.book-fluency/v5",
                "narrative_frame": frame,
                "adapted": adapted,
                "reverted": reverted,
                "overwritten_by_replay": overwritten,
                "chapters": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"    0book-fluency: {adapted} chapters de-calqued, {reverted} reverted to base")
    return book_md


def apply_author_companion_voice(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    revoicer: Callable[..., str] | None = None,
    only: Sequence[int] | None = None,
) -> Path:
    """Re-voice each chapter of ``book/book.md`` into author-companion register.

    ``revoicer`` defaults to the real LLM call; tests inject a fake. A window that
    fails any fidelity gate is reverted to its faithful base; chapters longer than
    ``_LONG_CHAPTER_WORDS`` are split into windows first, so one bad passage no
    longer reverts a whole chapter. ``only`` restricts the pass to the given 1-based
    section numbers — use it to re-run a chapter without re-voicing (and thereby
    degrading) the ones already done. Editorial asides are preserved untouched, as
    are chapters authored in the Book Composer unless ``force``. Returns the
    book.md path.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-voice",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before 0book-voice.",
        )
    frame = narrative_frame(book_dir)
    subject = narrator_subject(book_dir)
    log(f"    0book-voice: narrative frame = {frame}")
    new_text, records = _run_pass(
        book_md,
        revoicer or _revoice_chapter,
        log=log,
        noun="voice",
        label_prefix="voice",
        only=only,
        frame=frame,
        narrator_subject=subject,
        force=force,
    )
    book_md.write_text(new_text, encoding="utf-8")
    report_path = book_dir / "_system" / "book-voice-report.json"
    records = merge_records(load_prior_records(report_path), records, edited_keys=edited_chapter_keys(book_dir))
    revoiced = sum(1 for r in records if r["status"] in KEPT_STATUSES)
    reverted = sum(1 for r in records if r["status"] == "reverted")
    overwritten = sum(1 for r in records if r["status"] == STATUS_OVERWRITTEN)
    report_path.write_text(
        json.dumps(
            {
                "schema": "podcast.book-voice/v5",
                "narrative_frame": frame,
                "revoiced": revoiced,
                "reverted": reverted,
                "overwritten_by_replay": overwritten,
                "chapters": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"    0book-voice: {revoiced} chapters re-voiced, {reverted} reverted to base")
    return book_md
