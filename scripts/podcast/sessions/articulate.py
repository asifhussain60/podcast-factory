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
    python3 scripts/podcast/sessions/articulate.py <slug> [--force] [--limit N] [--engine auto|claude|codex|gemini]
    python3 scripts/podcast/sessions/articulate.py <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_defects import chapters as split_chapters  # noqa: E402
from _book_edits import anchor_key, write_chapter_body  # noqa: E402

# `_INTRODUCTION_KEY` is imported rather than restated: the pass engine already
# refuses to touch the edition's introduction, and a second copy of that heading
# here would be a second answer to "which section is apparatus" — the two would
# drift the first time either changed, and this module would report articulating
# a section the engine silently passed through.
from _book_voice import _CHAPTER_HEADING_RE, _INTRODUCTION_KEY  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _pipeline_flags import narrative_frame  # noqa: E402
from _sessions_prose_format import normalize_sessions_prose  # noqa: E402
from _text_transform import adapters_for_engine, preflight_engine, resolve_runtime_engine  # noqa: E402
from rearticulate_chapter import rearticulate  # noqa: E402

from sessions.ingest import ARTICULATE_STEP, LANE_STEPS  # noqa: E402
from sessions.spoken import spoken_chapters  # noqa: E402

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

#: Consecutive chapters returning nothing from the model before the run gives up.
#: Two, not one: a single dead call is a transient worth riding through, and a
#: second in a row is a pattern. Sixteen in a row is what actually happened.
_DEAD_STREAK_LIMIT = 2

# Sessions articulation is complete only when every window in the chapter kept
# its rewrite. A `partial` pass is faithful, because failed windows fall back to
# source, but it is not fully book-quality articulated prose and must be retried.
DONE_STATUSES = frozenset({"adapted"})


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


def _normalize_after_articulation(book_dir: Path, title: str, *, log) -> None:
    """Bring a just-articulated chapter's headings and citations up to the
    book's own house style — see `_sessions_prose_format` for exactly what
    that means and why the model output needs it at all: the source
    transcript's own legacy conventions (a bare `81:22` above a verse, a
    `### Title Arabic` heading followed by its own transliteration line)
    ride straight through articulation by design, since rewording is never
    allowed to restructure. Only re-writes book.md when something actually
    changed; a chapter already in house style costs one extra read.
    """
    book_md = book_dir / "book" / "book.md"
    text = book_md.read_text(encoding="utf-8")
    body = next((b for h, b in split_chapters(text) if h.strip() == title), None)
    if body is None:
        return
    new_body, changes = normalize_sessions_prose(body.strip())
    if not changes:
        return
    write_chapter_body(book_dir, title, new_body)
    log(f"      normalized {len(changes)} heading/citation formatting issue(s)")


_USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_read", "cache_create", "cost_usd")


def _read_cost_rows(book_dir: Path) -> list[dict]:
    path = book_dir / "_system" / "cost-ledger.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _usage_since(book_dir: Path, start_count: int) -> dict:
    rows = _read_cost_rows(book_dir)[start_count:]
    usage = {field: 0 for field in _USAGE_FIELDS}
    models: list[str] = []
    steps: list[str] = []
    for row in rows:
        for field in _USAGE_FIELDS:
            value = row.get(field) or 0
            usage[field] += float(value) if field == "cost_usd" else int(value)
        if row.get("model") and row["model"] not in models:
            models.append(str(row["model"]))
        if row.get("step"):
            steps.append(str(row["step"]))
    usage["total_tokens"] = int(
        usage["input_tokens"] + usage["output_tokens"] + usage["cache_read"] + usage["cache_create"]
    )
    usage["cost_usd"] = round(float(usage["cost_usd"]), 6)
    usage["rows"] = len(rows)
    usage["models"] = models
    usage["steps"] = steps
    return usage


def _quality_from_record(record: dict) -> dict:
    windows = int(record.get("windows") or 0)
    kept = int(record.get("windows_kept") or 0)
    gates = [str(g) for g in (record.get("gates") or [])]
    warnings = [str(w) for w in (record.get("warnings") or [])]
    assembly_gates = [str(g) for g in (record.get("assembly_gates") or [])]
    return {
        "windows": windows,
        "windows_kept": kept,
        "windows_cached": int(record.get("windows_cached") or 0),
        "windows_repaired": int(record.get("windows_repaired") or 0),
        "windows_source_preserved": int(record.get("windows_source_preserved") or 0),
        "model_failures": int(record.get("model_failures") or 0),
        "fresh_calls_disabled": bool(record.get("fresh_calls_disabled")),
        "window_keep_rate": round(kept / windows, 4) if windows else None,
        "gates": gates,
        "warnings": warnings,
        "assembly_gates": assembly_gates,
    }


def _looks_like_unreachable_model(status: str, record: dict, usage: dict) -> bool:
    if status == "adapted":
        return False
    gates = [str(g) for g in (record.get("gates") or [])]
    if gates and all("no candidate" in gate for gate in gates):
        return True
    return (
        int(usage.get("total_tokens") or 0) == 0
        and int(record.get("model_failures") or 0) > 0
        and bool(record.get("fresh_calls_disabled"))
    )


def _record(book_dir: Path, key: str, title: str, status: str, *, metrics: dict | None = None) -> None:
    ledger = read_ledger(book_dir)
    entry = {
        "title": title,
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if metrics:
        entry.update(metrics)
    ledger["chapters"][key] = entry
    _ledger_path(book_dir).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_step_status(book_dir: Path, *, status: str, kept: int, total: int) -> None:
    """Record how far the articulation step has actually gotten.

    `sessions-articulate` sits BEFORE `sessions-preface` in `LANE_STEPS`, but it
    is legitimately run after it — the introduction the preface writes is
    apparatus this pass skips. So the step's own status is set and the lane's
    `phase` pointer is left exactly where the ingest put it. Writing
    `phase: sessions-articulate` here would report a finished book as three
    steps from done.

    ``status`` is ``"completed"`` ONLY when every non-introduction chapter is
    kept — never merely "the run finished without crashing". A run that reaches
    the end of its chapter list with real, non-outage reverts still remaining is
    NOT complete; it is running and waiting for a retry, same as an aborted one.
    Conflating "the process returned" with "the book is done" is what let the
    very first run stamp `completed` at 2 of 23 chapters kept, which
    `book_status_card.py` then read as 100% of this step's weight earned —
    reporting the book as 92% complete and one step from done while twenty-one
    of twenty-three chapters still read exactly as the transcript left them.

    Called at the START of a run too (``kept``/``total`` as they stand before
    any chapter is touched), so a heartbeat mid-run sees ``running`` promptly
    rather than whatever an earlier run's completion — or non-completion —
    happened to leave behind.
    """
    path = book_dir / "_system" / "orchestrator-state.json"
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    phases = state.get("phases") or {step: {"status": "pending"} for step in LANE_STEPS}
    entry = {"status": status, "chapters_kept": kept, "chapters_total": total}
    entry["completed_at" if status == "completed" else "updated_at"] = datetime.now(timezone.utc).isoformat()
    phases[ARTICULATE_STEP] = entry
    state["phases"] = phases
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def articulate_book(
    book_dir: Path,
    *,
    force: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    engine: str = "auto",
    log=print,
) -> dict:
    """Articulate every chapter. Returns a summary of what happened."""
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise FileNotFoundError(f"missing {book_md} — run the ingest first.")

    engine = resolve_runtime_engine(engine)
    frame = narrative_frame(book_dir)
    # Only a fully adapted chapter is done. A partial pass kept at least one
    # window, but the stitched chapter still mixes articulated prose with source
    # fallback, so this lane retries it instead of treating it as book-quality.
    done = (
        set()
        if force
        else {k for k, v in read_ledger(book_dir)["chapters"].items() if v.get("status") in DONE_STATUSES}
    )
    chapters = chapter_keys(book_md)
    # A chapter taken off the tape is NOT articulated, and the exclusion is here
    # rather than in the prompt because no instruction can make a rewrite safe
    # for it. This pass turns spoken sentences into literary ones — which is
    # right for a chapter built from written notes, and is exactly what breaks a
    # chapter whose paragraphs have to stay the words on the recording for the
    # read-along to light them up. The light corrector in `read_along.py` owns
    # these instead.
    spoken = set(spoken_chapters(book_dir))
    todo = [(k, t) for k, t in chapters if k not in done and k not in spoken]
    skipped = len(chapters) - len(todo)
    if spoken:
        log(f"  articulate: leaving {len(spoken)} spoken chapter(s) to the read-along corrector")
    if limit is not None:
        todo = todo[:limit]

    log(
        f"  articulate: {book_dir.name} — frame={frame}, engine={engine}, "
        f"{len(todo)} chapter(s) to do, {skipped} already articulated"
    )
    if dry_run:
        for key, title in todo:
            log(f"    would articulate: {title}")
        return {
            "frame": frame,
            "planned": len(todo),
            "skipped": skipped,
            "adapted": 0,
            "partial": 0,
            "reverted": 0,
            "failed": [],
            "engine": engine,
        }

    if todo:
        _write_step_status(book_dir, status="running", kept=skipped, total=len(chapters))

    adapter, repair_adapter = adapters_for_engine(engine)

    adapted = partial = reverted = 0
    failed: list[dict] = []
    dead_streak = 0
    aborted = False
    for index, (key, title) in enumerate(todo, start=1):
        log(f"  [{index}/{len(todo)}] {title}")
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        cost_start = len(_read_cost_rows(book_dir))
        try:
            result = rearticulate(
                book_dir,
                key,
                adapter=adapter,
                repair_adapter=repair_adapter,
                log=log,
                write_partial=False,
            )
        except Exception as exc:  # one bad chapter must not end a multi-hour run
            log(f"      FAILED: {exc}")
            failed.append({"chapter": title, "key": key, "error": str(exc)[:300]})
            finished_at = datetime.now(timezone.utc)
            usage = _usage_since(book_dir, cost_start)
            metrics = {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_seconds": round(time.perf_counter() - started_perf, 3),
                "usage": usage,
            }
            _record(
                book_dir,
                key,
                title,
                "failed",
                metrics=metrics,
            )
            if int(usage.get("total_tokens") or 0) == 0:
                dead_streak += 1
            else:
                dead_streak = 0
            if dead_streak >= _DEAD_STREAK_LIMIT:
                log(
                    f"  articulate: STOPPING — {dead_streak} chapters in a row failed before "
                    f"recording model usage. This looks like an exhausted or unreachable engine. "
                    f"{len(todo) - index} chapter(s) untouched. Re-run to resume."
                )
                aborted = True
                break
            continue
        # `rearticulate` returns the STATUS ENVELOPE it writes to
        # `rearticulate-status.json` — `{chapter_key, state, started_at,
        # finished_at, record}` — and the pass verdict is the nested `record`.
        # Reading `status` off the envelope returns None for every chapter, which
        # counted five successful chapters as reverted on the first live run.
        record = result.get("record") or {}
        status = str(record.get("status") or "unknown")

        if status == "adapted":
            adapted += 1
            _normalize_after_articulation(book_dir, title, log=log)
        elif status == "partial":
            partial += 1
        else:
            reverted += 1
        # Written per chapter, not at the end: a run interrupted at chapter 19 of
        # 23 must not re-pay for the eighteen that succeeded.
        finished_at = datetime.now(timezone.utc)
        metrics = {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(time.perf_counter() - started_perf, 3),
            "usage": _usage_since(book_dir, cost_start),
            "quality": _quality_from_record(record),
        }
        # A window whose model call returned nothing is recorded `no candidate`.
        # One is a transient; a RUN of them means the model is unreachable — a rate
        # limit, a broken CLI, a hook cancelling the subprocess — and every further
        # chapter will be marked reverted without a single word being read. The
        # zero-token branch catches mixed cache/process-failure chapters too: they
        # may be "partial", but they still prove fresh generation is unavailable.
        if _looks_like_unreachable_model(status, record, metrics["usage"]):
            dead_streak += 1
        else:
            dead_streak = 0
        _record(book_dir, key, title, status, metrics=metrics)
        log(f"      {status} — {metrics['duration_seconds']:.1f}s, {metrics['usage']['total_tokens']} tokens")

        if dead_streak >= _DEAD_STREAK_LIMIT:
            log(
                f"  articulate: STOPPING — {dead_streak} chapters in a row returned nothing from the "
                f"model. This is not a quality result; the model is unreachable. "
                f"{len(todo) - index} chapter(s) untouched. Re-run to resume."
            )
            aborted = True
            break

    # Re-read the ledger rather than trust this run's own counters: `skipped`
    # chapters were already kept before this call started, and `adapted` counts
    # only what THIS run kept. The true completeness question is "is anything
    # left un-kept at all", which only the ledger — updated per chapter above,
    # including by the failed/aborted paths — can answer.
    now_kept = sum(1 for v in read_ledger(book_dir)["chapters"].values() if v.get("status") in DONE_STATUSES)
    _write_step_status(
        book_dir,
        status="completed" if now_kept >= len(chapters) else "running",
        kept=now_kept,
        total=len(chapters),
    )
    # Once, at the end of the run rather than per chapter — the audit re-scans
    # the whole book, and 20+ chapters is 20+ needless re-scans of the same
    # already-kept prose. Only the just-kept chapters' Arabic actually needs a
    # fresh resolution, so a Compose review right after this run shows correct
    # quotation-card citations without waiting on the apparatus step.
    if adapted:
        from _book_arabic_audit import run_arabic_audit

        run_arabic_audit(book_dir, log=log)
    return {
        "frame": frame,
        "planned": len(todo),
        "skipped": skipped,
        "adapted": adapted,
        "partial": partial,
        "reverted": reverted,
        "failed": failed,
        "aborted": aborted,
        "engine": engine,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--force", action="store_true", help="re-run chapters this lane has already articulated")
    parser.add_argument("--limit", type=int, default=None, help="stop after N chapters")
    parser.add_argument("--engine", choices=("auto", "claude", "codex", "gemini"), default="auto")
    parser.add_argument("--dry-run", action="store_true", help="list what would run and exit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    book_dir = resolve_content(args.slug)
    if book_dir is None:
        print(f"no book found for slug {args.slug!r}", file=sys.stderr)
        return 2

    engine = resolve_runtime_engine(args.engine)
    if not args.dry_run:
        try:
            preflight_engine(engine)
        except Exception as exc:
            print(f"  articulate: cannot use {engine} engine — {exc}", file=sys.stderr)
            return 2

    summary = articulate_book(
        book_dir,
        force=args.force,
        limit=args.limit,
        dry_run=args.dry_run,
        engine=engine,
        log=(lambda *_: None) if args.json else print,
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"  articulate: {summary['adapted']} adapted, {summary['partial']} partial, "
            f"{summary['reverted']} reverted, {len(summary['failed'])} failed, {summary['skipped']} skipped"
        )
    return 1 if summary["failed"] or summary.get("aborted") else 0


if __name__ == "__main__":
    # This run is routinely launched detached (`nohup ... > log.txt &`) so a
    # heartbeat can watch it, and stdout redirected to a file rather than a
    # terminal is FULLY buffered by default. That log stayed at 0 bytes for the
    # entire ten-hour run on 2026-08-12 — every "quiet tick" I reported wasn't
    # quiet, it was a monitoring channel with no signal, because nothing had
    # been flushed. Line-buffering here is cheap (a few hundred lines over a
    # multi-hour run) and makes the log mean what it says.
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    raise SystemExit(main())
