#!/usr/bin/env python3
"""rearticulate_chapter.py — rewrite ONE chapter of book.md into articulate prose.

The engine behind the Book Composer's Rearticulate action. Takes a stiff,
word-for-word, Arabic-calqued chapter and rewrites it as modern, lucid, simple
English under the Book Articulation Standard (docs/standards/book-articulation.md,
REQ-BA-*), preserving every teaching, speech, quote, image, Arabic run, and
enumeration. Builds its prompt from `_book_voice_prompts._articulation_prompt` —
the SAME builder the automatic `0book-fluency` pass uses, so the on-demand tool
and the automatic default cannot silently diverge. Reuses the fluency pass's
engine (`_book_voice._run_pass`) so the windowing, the per-window `revoice_gates`
(abridgement, teaching loss, Arabic retention, doctrinal P0s, narrative frame),
the editorial-aside passthrough and the seam trimming are the SAME code the
pipeline trusts — a window that fails a gate reverts to its base, so a failed
rearticulation is a no-op, never a loss.

The chapter is addressed by its Composer chapter key (`_book_edits.anchor_key`
of the `##` heading), NEVER by printed chapter number — the introduction is an
unnumbered `##` section, so "chapter 3" is section 4 and trusting numbers
rewrites the wrong chapter. The result is recorded into
`_system/composer-edits.json` via `record_edit`, exactly like a human Composer
save: it survives re-compose and marks the chapter as authored. The pass report
is re-stamped in the same breath (`_book_pass_reports.record_rearticulation`),
because a report that still calls the new prose un-articulated would keep the
Composer warning about a chapter this tool has just fixed.

Progress is written to `_system/rearticulate-status.json` (state: running |
done | error) so the Astro endpoint can poll a detached run.

Usage:
    python3 scripts/podcast/rearticulate_chapter.py <slug> <chapter-key> [--json]
    python3 scripts/podcast/rearticulate_chapter.py --book-dir <dir> <chapter-key>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _authoring._core import _run_claude_p_with_retry
from _book_edits import anchor_key, base_fingerprint_for, record_edit
from _book_pass_reports import record_rearticulation
from _book_voice import _CHAPTER_HEADING_RE, _run_pass
from _book_voice_prompts import _articulation_prompt
from _content_profile import source_language as _source_language
from _paths import resolve_content
from _pipeline_flags import narrative_frame, narrator_subject

_TIMEOUT = 900
_PHASE = "rearticulate"


def _adapter(
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
    lang = _source_language(book_dir)
    rc, out, err = _run_claude_p_with_retry(
        _articulation_prompt(title, base_text, previous_tail, frame=frame, narrator=narrator, source_language=lang),
        timeout=_TIMEOUT,
        book_dir=book_dir,
        phase=_PHASE,
        step=label,
        log=log,
    )
    if rc != 0:
        raise RuntimeError(f"{label}: claude -p rc={rc}: {(err or '')[:200]}")
    return (out or "").strip()


def _status_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "rearticulate-status.json"


def _write_status(book_dir: Path, payload: dict) -> None:
    path = _status_path(book_dir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _section_ordinal(text: str, chapter_key: str) -> tuple[int, str] | None:
    """1-based ordinal over ALL ``##`` sections (intro included) + the heading."""
    for idx, m in enumerate(_CHAPTER_HEADING_RE.finditer(text), start=1):
        if anchor_key(m.group(1)) == chapter_key:
            return idx, m.group(1)
    return None


def _chapter_body(text: str, heading: str) -> str:
    parts = _CHAPTER_HEADING_RE.split(text)
    for i in range(1, len(parts), 2):
        if parts[i] == heading:
            return (parts[i + 1] if i + 1 < len(parts) else "").strip()
    return ""


def rearticulate(book_dir: Path, chapter_key: str, *, adapter=None, log=print) -> dict:
    """Rearticulate one chapter in place. Returns the pass record.

    ``adapter`` is injectable for tests (same signature as ``_adapter``).
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise FileNotFoundError(f"missing {book_md}")
    chapter_key = anchor_key(chapter_key)
    text = book_md.read_text(encoding="utf-8")
    found = _section_ordinal(text, chapter_key)
    if not found:
        raise ValueError(f"no ## section matches chapter key {chapter_key!r}")
    ordinal, heading = found

    started = datetime.now(timezone.utc).isoformat()
    _write_status(
        book_dir,
        {"chapter_key": chapter_key, "state": "running", "started_at": started, "pid": os.getpid()},
    )
    frame = narrative_frame(book_dir)
    subject = narrator_subject(book_dir)
    log(f"    rearticulate: {heading!r} (section {ordinal}, frame={frame or 'none'})")

    # force=True: the button's contract is overwrite-in-place, so a chapter that
    # already carries a Composer edit is rearticulated too, not passed through.
    new_text, records = _run_pass(
        book_md,
        adapter or _adapter,
        log=log,
        noun="rearticulate",
        label_prefix="rearticulate",
        only=[ordinal],
        frame=frame,
        narrator_subject=subject,
        force=True,
    )
    record = next(
        (r for r in records if r.get("status") not in ("skipped", "composer-edit")),
        {"status": "skipped"},
    )

    if record.get("status") in ("adapted", "partial"):
        tmp = book_md.with_suffix(".md.tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, book_md)
        # Durable, exactly like a human Composer save: the rearticulated body is
        # recorded in the sidecar so it survives re-compose. The base fingerprint
        # is QUOTED from composer-base.json (the value the replay stamped), never
        # hashed here — self-hashing against the live text is the exact bug that
        # made every edit report CONFLICT before 2026-07-21.
        body = _chapter_body(new_text, heading)
        record_edit(
            book_dir,
            chapter_key=chapter_key,
            body_md=body,
            base_fingerprint=base_fingerprint_for(book_dir, chapter_key),
            saved_at=datetime.now(timezone.utc).isoformat(),
        )
        # The pass report still describes the PREVIOUS state of this chapter —
        # for the chapter that needed this tool, "adapted-then-overwritten".
        # Leaving it there means the Composer goes on warning that articulated
        # prose is un-articulated, so the run would fix the book and not the
        # thing the reader is looking at.
        record_rearticulation(book_dir, heading, str(record.get("status")), log=log)

    result = {
        "chapter_key": chapter_key,
        "state": "done",
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "record": record,
    }
    _write_status(book_dir, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="?", help="content slug (resolved via _paths)")
    ap.add_argument("chapter_key", help="Composer chapter key (anchor_key of the ## heading)")
    ap.add_argument("--book-dir", help="explicit book directory (overrides slug)")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON on stdout")
    args = ap.parse_args()

    if args.book_dir:
        book_dir = Path(args.book_dir)
    elif args.slug:
        book_dir = resolve_content(args.slug)
    else:
        ap.error("either <slug> or --book-dir is required")

    try:
        result = rearticulate(book_dir, args.chapter_key)
    except Exception as e:
        payload = {
            "chapter_key": anchor_key(args.chapter_key),
            "state": "error",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            _write_status(Path(book_dir), payload)
        except Exception:
            pass
        print(json.dumps({"ok": False, **payload}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
