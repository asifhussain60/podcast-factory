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
one stumbling passage costs that passage rather than the whole chapter. See the
constant for its 2026-08-11 history. ``revoice_gates`` also catches the OPPOSITE
failure (2026-08-12): a response many times longer than its window, which no
prior gate checked for at all.

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
from pathlib import Path
from typing import Callable, Sequence

from _articulation_reconcile import reconcile_records
from _authoring._core import AuthoringError, _run_claude_p_with_retry, pure_text_call_options
from _book_articulation_notes import EMPTY_NOTES, extract_articulation_notes
from _book_edits import anchor_key, edited_chapter_keys
from _book_fences import span_re
from _book_pass_reports import load_prior_records, merge_records, restamp_counts

# `assembled_chapter_gates`, `narrative_opening_findings`, and `revoice_gates`
# live in `_book_voice_gates`
# (split 2026-08-12, DR-005) and are re-exported here so every existing
# `from _book_voice import revoice_gates` keeps working.
from _book_voice_gates import assembled_chapter_gates, narrative_opening_findings, revoice_gates  # noqa: F401
from _book_voice_prompts import _articulation_prompt
from _book_voice_windows import (
    _WINDOW_WORDS,
    _arabic_placeholder_findings,
    _cache_window_part,
    _cached_window_part,
    _drop_cached_window_part,
    _iter_prose_windows,
    _protect_arabic_runs,
    _protect_structural_artifacts,
    _protected_artifact_window,
    _restore_arabic_runs,
    _restore_structural_artifacts,
    _similarity,
    _structural_artifact_findings,
)
from _content_profile import source_language as _source_language
from _narrative import lecture_voice_counts
from _pipeline_flags import narrative_frame, narrator_subject
from _text_transform import _repair_adapter
from _translation_text import _trim_seam_overlap, subordinate_body_headings

_VOICE_TIMEOUT = 900
_CHAPTER_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")


# Editorial asides (from 0book-augment) are NOT re-voiced — skip these spans.
# Tolerant of the bare-marker form a Composer round-trip leaves behind: a span
# this pass cannot see is a span the model rewrites into the narrator's voice.
_EDITORIAL_SPAN_RE = span_re("editorial", trailing=r"\n?")

# 4,500 -> 4,000 on 2026-08-11 after a 4,479-word chapter returned an
# 840-word summary; this path owns book-prose windows, not source-span windows.
_LONG_CHAPTER_WORDS = 4000
# Output this similar to its input was not re-voiced — it was copied. Not a gate
# (reverting to base yields the same text); recorded so the report says so.
_NEAR_IDENTICAL_RATIO = 0.95


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
    window_words: int = _WINDOW_WORDS,
    repair_fn: Callable[..., str] | None = None,
) -> tuple[str, dict]:
    """Adapt one chapter body, windowing it when it is too long for a single call.

    Returns ``(new_body, record)``. Each window is gated against its own base and
    reverts alone, so a long chapter is never all-or-nothing. ``record`` documents
    what actually happened — the thing the old ``{revoiced, reverted}`` counters
    could not answer without forensics against the cost ledger.
    """
    base_words = len(base_prose.split())
    windows = _iter_prose_windows(base_prose, target_words=window_words) or [base_prose]
    kept_parts: list[str] = []
    gates: list[str] = []
    warnings: list[str] = []
    kept = 0
    tail = ""
    notes = {k: [] for k in EMPTY_NOTES}
    cached = 0
    repaired = 0
    source_preserved = 0
    model_failures = 0
    consecutive_model_failures = 0
    fresh_calls_disabled = False
    for idx, window in enumerate(windows, start=1):
        part_label = label if len(windows) == 1 else f"{label}-part-{idx:02d}"
        if _protected_artifact_window(window):
            kept += 1
            source_preserved += 1
            warnings.append(f"{part_label}: protected source artifact copied verbatim")
            if kept_parts:
                window = _trim_seam_overlap(kept_parts[-1], window)
            kept_parts.append(window)
            tail = " ".join(window.split()[-80:])
            _cache_window_part(book_dir, part_label, window, window)
            continue
        artifact_protected_window, protected_artifacts = _protect_structural_artifacts(window)
        protected_window, protected_arabic = _protect_arabic_runs(artifact_protected_window)
        candidate = _cached_window_part(book_dir, part_label, window)
        from_cache = candidate is not None
        if from_cache:
            cached += 1
            log(f"      {part_label}: cache hit")
        elif fresh_calls_disabled:
            log(f"      {noun}: {title!r} {part_label} skipped (fresh model calls disabled after repeated failures)")
            candidate = ""
        else:
            try:
                candidate = fn(
                    title,
                    protected_window,
                    book_dir,
                    part_label,
                    log,
                    previous_tail=tail,
                    frame=frame or "",
                    narrator=narrator_subject,
                )
                consecutive_model_failures = 0
            except AuthoringError:
                raise
            except Exception as e:  # non-fatal: this window falls back to its base
                log(f"      {noun}: {title!r} {part_label} skipped (non-fatal): {e}")
                model_failures += 1
                consecutive_model_failures += 1
                if consecutive_model_failures >= 3:
                    fresh_calls_disabled = True
                    warnings.append(
                        f"{part_label}: fresh model calls disabled after {consecutive_model_failures} "
                        "consecutive process failures"
                    )
                candidate = ""
        # This block through the near-identical check used to run UNGUARDED
        # (2026-08-12): a candidate that broke some downstream step propagated a
        # bare exception past `_run_pass` to the caller's broad catch, reporting
        # the WHOLE CHAPTER failed rather than reverting the one window. Same
        # treatment as the model-call try/except above: `part` falls back to the
        # clean `window`, exactly like a normal gate rejection.
        try:
            # REQ-BA-160: strip any trailing ===ARTICULATION-NOTES=== block BEFORE
            # gating, so length/fidelity checks never see it and it can never reach
            # book.md. A no-op for prompts (e.g. author-companion voice) that never
            # emit one.
            raw_candidate = candidate or ""
            candidate = raw_candidate if from_cache else _restore_arabic_runs(raw_candidate, protected_arabic)
            candidate = candidate if from_cache else _restore_structural_artifacts(candidate, protected_artifacts)
            candidate, window_notes = extract_articulation_notes(candidate)
            placeholder_gate = (
                []
                if from_cache
                else (
                    _structural_artifact_findings(protected_artifacts, raw_candidate)
                    + _arabic_placeholder_findings(protected_arabic, raw_candidate)
                )
            )
            gate = placeholder_gate + (
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
            if gate and repair_fn and raw_candidate and not from_cache:
                original_gate = gate
                try:
                    repaired_raw = repair_fn(
                        title,
                        protected_window,
                        raw_candidate,
                        original_gate,
                        book_dir,
                        f"{part_label}-repair",
                        log,
                        previous_tail=tail,
                        frame=frame or "",
                        narrator=narrator_subject,
                    )
                    repaired_candidate = _restore_arabic_runs(repaired_raw or "", protected_arabic)
                    repaired_candidate = _restore_structural_artifacts(repaired_candidate, protected_artifacts)
                    repaired_candidate, repaired_notes = extract_articulation_notes(repaired_candidate)
                    repaired_placeholder_gate = _structural_artifact_findings(
                        protected_artifacts, repaired_raw or ""
                    ) + _arabic_placeholder_findings(protected_arabic, repaired_raw or "")
                    repaired_gate = repaired_placeholder_gate + (
                        revoice_gates(
                            window,
                            repaired_candidate,
                            check_opening=idx == 1,
                            frame=frame,
                            narrator_subject=narrator_subject,
                        )
                        if repaired_candidate
                        else ["no candidate"]
                    )
                    if repaired_gate:
                        gate = original_gate + [f"repair still failed: {g}" for g in repaired_gate]
                    else:
                        log(f"      {part_label}: repair accepted")
                        candidate, window_notes, gate = repaired_candidate, repaired_notes, []
                        repaired += 1
                except Exception as e:
                    log(f"      {noun}: {title!r} {part_label} repair skipped (non-fatal): {e}")
            if gate:
                part = window
                if from_cache:
                    _drop_cached_window_part(book_dir, part_label, window)
            else:
                part = candidate
                if not from_cache:
                    _cache_window_part(book_dir, part_label, window, candidate)
                if _similarity(window, candidate) >= _NEAR_IDENTICAL_RATIO:
                    warnings.append(f"{part_label}: output near-identical to base — copied, not re-voiced")
        except Exception as e:
            log(f"      {noun}: {title!r} {part_label} gate check raised (non-fatal): {e}")
            window_notes, gate, part = {k: [] for k in EMPTY_NOTES}, [f"gate check raised: {e}"], window
        if gate:
            gates.extend(f"{part_label}: {g}" for g in gate)
        else:
            kept += 1
            for key, values in window_notes.items():
                notes[key].extend(values)
        if kept_parts:
            part = _trim_seam_overlap(kept_parts[-1], part)
        kept_parts.append(part)
        tail = " ".join(part.split()[-80:])
    new_body = "\n\n".join(kept_parts).strip()
    status = "adapted" if kept == len(windows) else ("reverted" if kept == 0 else "partial")
    assembly_gates = assembled_chapter_gates(base_prose, new_body) if kept == len(windows) else []
    pre_assembly_kept = kept
    if assembly_gates and kept:
        gates.extend(f"assembled chapter: {g}" for g in assembly_gates)
        new_body = base_prose
        kept = 0
        status = "reverted"
    elif status == "partial":
        warnings.append(f"assembled chapter is partial — {kept}/{len(windows)} windows kept; review voice continuity")
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
        "windows_cached": cached,
        "windows_repaired": repaired,
        "windows_source_preserved": source_preserved,
        "model_failures": model_failures,
        "fresh_calls_disabled": fresh_calls_disabled,
        "pre_assembly_windows_kept": pre_assembly_kept,
        "status": status,
        "gates": gates,
        "assembly_gates": assembly_gates,
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
        **pure_text_call_options(),
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
_LEGACY_INTRODUCTION_KEY = "introduction"  # pre-v2 legacy books (mukhtasar-ul-asar-1/2)


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
    window_words: int = _WINDOW_WORDS,
    repair_fn: Callable[..., str] | None = None,
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
        # During a compose it is simply not there yet (the apparatus injects it
        # after this pass). Standalone, on a finished book, it IS there and is the
        # first `## ` section — so `only=[1]` means the introduction and not
        # chapter one, which is exactly the accident this prevents.
        if anchor_key(head) in (_INTRODUCTION_KEY, _LEGACY_INTRODUCTION_KEY):
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
            window_words=window_words,
            repair_fn=repair_fn,
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
    repair_fn: Callable[..., str] | None = None,
) -> Path:
    """De-calque each chapter of the FAITHFUL base into fluent modern English.

    Book Pipeline v2 runs this over the faithful-voice base (author_companion books
    get fluency from their re-voice pass instead). It reuses the same fidelity
    gates as the re-voice pass: a chapter that drops a teaching, loses Arabic, gains
    a doctrinal P0, or abridges is REVERTED to its base text — per window, so a long
    chapter is not all-or-nothing. Editorial asides are left untouched. ``only``
    restricts the pass to the given 1-based section numbers. Chapters authored in
    the Book Composer are passed through untouched unless ``force`` — which had been
    an accepted-and-ignored parameter until this became its meaning. ``repair_fn``
    defaults to the real one-shot repair adapter (until 2026-08-15 this pass ran
    with NO repair attempt at all, unlike the on-demand Rearticulate action —
    tests that fake ``adapter`` should also pass a deterministic ``repair_fn``
    (or one that simply echoes its candidate back) to stay hermetic. Returns the
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
    resolved_repair_fn = repair_fn if repair_fn is not None else _repair_adapter
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
        repair_fn=resolved_repair_fn,
    )
    book_md.write_text(new_text, encoding="utf-8")
    # A chapter left partial/reverted gets its findings persisted and ONE more
    # bounded attempt with that history folded in — see _articulation_reconcile.
    # This is what makes every FUTURE book's automatic compose-time pass
    # self-heal instead of silently shipping stuck chapters; no orchestrator
    # phase change needed, this just runs inside the existing sub-step.
    new_text, records = reconcile_records(
        book_dir,
        book_md,
        records,
        fn=adapter or _fluency_chapter,
        repair_fn=resolved_repair_fn,
        frame=frame,
        narrator_subject=subject,
        window_words=_WINDOW_WORDS,
        log=log,
    )
    report_path = book_dir / "_system" / "book-fluency-report.json"
    records = merge_records(load_prior_records(report_path), records, edited_keys=edited_chapter_keys(book_dir))
    # Counted by the SAME function the re-stamp paths use, so the pass and every
    # later correction can never disagree about what a counter means. Keys are
    # pre-declared to fix their order in the JSON — restamp_counts assigns into
    # them, so routing through it does not churn the diff of every book's report.
    report = {
        "schema": "",
        "narrative_frame": frame,
        "adapted": 0,
        "reverted": 0,
        "overwritten_by_replay": 0,
        "chapters": records,
    }
    restamp_counts(report, records, schema="podcast.book-fluency/v5", count_key="adapted")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"    0book-fluency: {report['adapted']} chapters de-calqued, {report['reverted']} reverted to base")
    return book_md


# `apply_author_companion_voice` and its default adapter `_revoice_chapter` live
# in `_book_voice_companion` (split 2026-08-15, DR-005) and are re-exported here
# so every existing `from _book_voice import apply_author_companion_voice` keeps
# working.
from _book_voice_companion import (  # noqa: E402, F401
    _revoice_chapter,
    apply_author_companion_voice,
)
