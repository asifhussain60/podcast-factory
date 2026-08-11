"""Run the articulation pass over every chapter of an ingested Sessions book.

`sessions-articulate` was a step name with no code behind it until 2026-08-11.
The ingest converts a delivered lecture into chapters — headings, paragraphs,
images, verse cards, vowelled Arabic — but the SENTENCES are still the ones the
speaker said aloud, and a transcript tidied is not a book. This is the step that
makes them read like one, against the same Book Articulation Standard
(`docs/standards/book-articulation.md`, REQ-BA-*) that produced the editions the
Sessions books sit beside on the shelf.

WHY IT IS ITS OWN MODULE and not part of the ingest: the ingest is a
deterministic HTML walk with no model behind it, so re-running it is free and
safe. This is hours of model time. Folding the two together would mean paying
for the whole book again to fix one image path.

WHAT IT REUSES, and reimplements none of:

    `rearticulate_chapter.rearticulate`  — the engine behind the Book Composer's
    Rearticulate button, which is itself the fluency pass's engine. So the
    windowing (>4,500 words split at 2,500), the per-window `revoice_gates`
    (abridgement, teaching loss, Arabic retention, doctrinal P0s, narrative
    frame), the per-window revert, and the Composer-edit record all behave here
    exactly as they do everywhere else. A window that fails a gate reverts to
    its base: a failed articulation is a no-op, never a loss.

The Composer-edit record is the part that matters for this lane specifically.
`ingest.py` regenerates `book.md` from the dump every time it runs and then
replays `_system/composer-edits.json` over the result. Articulated prose that
lived only in `book.md` would be destroyed by the next ingest; recorded as an
edit, it survives — the same guarantee a chapter Asif types by hand gets.

RESUMABLE by default, against this lane's own ledger (`LEDGER_NAME` below), so an
interrupted run picks up where it stopped instead of paying for the whole book
twice. `--force` re-runs chapters already articulated.

Note that the engine rearticulates a chapter that carries a Composer edit rather
than passing it through: that is the Rearticulate button's contract and it is
right here, because every chapter of both books already carries one from the
mechanical repairs that ran before this step existed. The base text handed to the
model is what is in `book.md` — repairs included — so those survive into the
result, and the Arabic-retention gate is what keeps the verses intact.

Usage:
    python3 scripts/podcast/sessions/articulate.py <slug> [--force] [--limit N]
    python3 scripts/podcast/sessions/articulate.py <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_edits import anchor_key  # noqa: E402

# `_INTRODUCTION_KEY` is imported rather than restated: the pass engine already
# refuses to touch the edition's introduction, and a second copy of that heading
# here would be a second answer to "which section is apparatus" — the two would
# drift the first time either changed, and this module would report articulating
# a section the engine silently passed through.
from _book_voice import _CHAPTER_HEADING_RE, _INTRODUCTION_KEY  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _pipeline_flags import narrative_frame  # noqa: E402
from rearticulate_chapter import rearticulate  # noqa: E402

from sessions.ingest import ARTICULATE_STEP, LANE_STEPS  # noqa: E402

#: This lane's own record of which chapters have been articulated.
#:
#: NOT `edited_chapter_keys` — every chapter of both Sessions books already
#: carries a Composer edit, written by the mechanical defect repairs (honorifics,
#: verse-card cleaning, stray emphasis) that ran before this step existed. Using
#: the edit sidecar as the resume signal would skip all 29 chapters and report a
#: finished run. NOT the fluency report either: `record_rearticulation` only
#: touches reports that already name the chapter, and a Sessions book has never
#: had one. So the lane keeps its own, which is honest about what it means.
LEDGER_NAME = "sessions-articulation.json"


def chapter_keys(book_md: Path) -> list[tuple[str, str]]:
    """``(anchor key, heading text)`` for every ``##`` section worth articulating."""
    text = book_md.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for match in _CHAPTER_HEADING_RE.finditer(text):
        heading = match.group(1)
        key = anchor_key(heading)
        if key == _INTRODUCTION_KEY:
            continue
        out.append((key, heading.lstrip("#").strip()))
    return out


def _ledger_path(book_dir: Path) -> Path:
    return book_dir / "_system" / LEDGER_NAME


def read_ledger(book_dir: Path) -> dict:
    path = _ledger_path(book_dir)
    if not path.exists():
        return {"schema": "podcast.sessions-articulation/v1", "chapters": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": "podcast.sessions-articulation/v1", "chapters": {}}
    data.setdefault("chapters", {})
    return data


def _record(book_dir: Path, key: str, title: str, status: str) -> None:
    ledger = read_ledger(book_dir)
    ledger["chapters"][key] = {
        "title": title,
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    _ledger_path(book_dir).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _mark_step_complete(book_dir: Path, *, chapters: int, reverted: int) -> None:
    """Record that the articulation step ran, without moving the lane backwards.

    `sessions-articulate` sits BEFORE `sessions-preface` in `LANE_STEPS`, but it
    is legitimately run after it — the introduction the preface writes is
    apparatus this pass skips. So the step's own status is set and the lane's
    `phase` pointer is left exactly where the ingest put it. Writing
    `phase: sessions-articulate` here would report a finished book as three
    steps from done.
    """
    path = book_dir / "_system" / "orchestrator-state.json"
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    phases = state.get("phases") or {step: {"status": "pending"} for step in LANE_STEPS}
    phases[ARTICULATE_STEP] = {
        "status": "completed",
        "chapters": chapters,
        "reverted": reverted,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    state["phases"] = phases
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def articulate_book(
    book_dir: Path,
    *,
    force: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    log=print,
) -> dict:
    """Articulate every chapter. Returns a summary of what happened."""
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise FileNotFoundError(f"missing {book_md} — run the ingest first.")

    frame = narrative_frame(book_dir)
    done = set() if force else {k for k, v in read_ledger(book_dir)["chapters"].items() if v.get("status") != "failed"}
    chapters = chapter_keys(book_md)
    todo = [(k, t) for k, t in chapters if k not in done]
    skipped = len(chapters) - len(todo)
    if limit is not None:
        todo = todo[:limit]

    log(f"  articulate: {book_dir.name} — frame={frame}, {len(todo)} chapter(s) to do, {skipped} already articulated")
    if dry_run:
        for key, title in todo:
            log(f"    would articulate: {title}")
        return {"frame": frame, "planned": len(todo), "skipped": skipped, "adapted": 0, "reverted": 0, "failed": []}

    adapted = reverted = 0
    failed: list[dict] = []
    for index, (key, title) in enumerate(todo, start=1):
        log(f"  [{index}/{len(todo)}] {title}")
        try:
            record = rearticulate(book_dir, key, log=log)
        except Exception as exc:  # one bad chapter must not end a multi-hour run
            log(f"      FAILED: {exc}")
            failed.append({"chapter": title, "key": key, "error": str(exc)[:300]})
            _record(book_dir, key, title, "failed")
            continue
        status = str(record.get("status") or "unknown")
        if status in ("adapted", "partial"):
            adapted += 1
        else:
            reverted += 1
        # Written per chapter, not at the end: a run interrupted at chapter 19 of
        # 23 must not re-pay for the eighteen that succeeded.
        _record(book_dir, key, title, status)
        log(f"      {status}")

    _mark_step_complete(book_dir, chapters=adapted, reverted=reverted)
    return {
        "frame": frame,
        "planned": len(todo),
        "skipped": skipped,
        "adapted": adapted,
        "reverted": reverted,
        "failed": failed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--force", action="store_true", help="re-run chapters this lane has already articulated")
    parser.add_argument("--limit", type=int, default=None, help="stop after N chapters")
    parser.add_argument("--dry-run", action="store_true", help="list what would run and exit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    book_dir = resolve_content(args.slug)
    if book_dir is None:
        print(f"no book found for slug {args.slug!r}", file=sys.stderr)
        return 2

    summary = articulate_book(
        book_dir,
        force=args.force,
        limit=args.limit,
        dry_run=args.dry_run,
        log=(lambda *_: None) if args.json else print,
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"  articulate: {summary['adapted']} adapted, {summary['reverted']} reverted, "
            f"{len(summary['failed'])} failed, {summary['skipped']} skipped"
        )
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
