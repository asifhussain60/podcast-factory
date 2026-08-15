"""_articulation_reconcile.py — durable memory + a real second attempt for
chapters the articulation (fluency/rearticulate) pass reverted.

WHY THIS EXISTS
----------------
`_book_voice.py::_adapt_chapter_body` gates every window of a chapter rewrite
against `revoice_gates()` and reverts a failing window to its base prose. That
reason string is real and specific (e.g. "abridged re-voice (139<147 words)")
and IS returned in the chapter's `record["gates"]` list — but the caller only
ever prints it (`log(...)`, i.e. stdout) and moves on. Nothing on disk survives
the process exiting, and nothing ever revisits the chapter. Confirmed on
2026-08-15: 10 of 18 chapters across two live books were stuck "partial" with
no way to ask "why," and the compose-time automatic pass (`apply_fluency_adapt`)
was calling `_run_pass` with NO `repair_fn` at all — every failing window there
had zero retries, not even the one-shot repair the on-demand
`rearticulate_chapter.py` path already had.

WHAT THIS MODULE ADDS
----------------------
1. `record_chapter_attempt` — persists every partial/reverted chapter's gate
   findings to `_system/articulation-reconcile.json`, append-only per chapter,
   so the failure reason survives past the one process that produced it.
2. `reconcile_records` — after a normal `_run_pass`, re-runs (`force=True`)
   just the chapters still partial/reverted, ONE more time, through the SAME
   windowing engine — but with `repair_fn` wrapped so each window's repair
   prompt sees every DISTINCT gate reason from every attempt so far, not just
   its own latest one. A real second chance with new information, not a
   re-roll. Chapters still open after this stay recorded with
   `needs_human: true` — durable, visible debt, never silently dropped.

Granularity note: gate findings are recorded and fed forward at CHAPTER
granularity (the `record["gates"]` list, which already carries per-window
strings like "fluency-02-part-03: <reason>") rather than indexed by individual
window fingerprint. Operating at the `_run_pass` boundary — not inside
`_adapt_chapter_body` — keeps this a small, low-risk addition rather than
surgery on the load-bearing per-window loop, while still recovering the exact
reason text this session could not answer "why was this chapter partial" with.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "podcast.articulation-reconcile/v1"


def reconcile_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "articulation-reconcile.json"


def _load(book_dir: Path) -> dict:
    path = reconcile_path(book_dir)
    if not path.is_file():
        return {"schema": SCHEMA, "chapters": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": SCHEMA, "chapters": {}}
    data.setdefault("schema", SCHEMA)
    data.setdefault("chapters", {})
    return data


def _save(book_dir: Path, data: dict) -> None:
    path = reconcile_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def record_chapter_attempt(
    book_dir: Path,
    chapter_title: str,
    status: str,
    gate_findings: list[str],
    *,
    attempt_kind: str,
) -> None:
    """Append one attempt's outcome for a chapter. `resolved` reflects the
    LATEST attempt only; the `log` list keeps every attempt's own findings so
    the full history is never lost, even once the chapter is later fixed.
    """
    data = _load(book_dir)
    entry = data["chapters"].setdefault(chapter_title, {"resolved": False, "needs_human": False, "log": []})
    resolved = status == "adapted"
    entry["resolved"] = resolved
    entry["needs_human"] = (not resolved) and attempt_kind == "second-attempt"
    entry["log"].append(
        {
            "attempt_kind": attempt_kind,
            "status": status,
            "gate_findings": list(gate_findings),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save(book_dir, data)


def open_chapters(book_dir: Path) -> list[str]:
    """Titles of chapters whose latest recorded attempt is still unresolved."""
    data = _load(book_dir)
    return [title for title, entry in data["chapters"].items() if not entry.get("resolved")]


def gate_articulation_complete(book_dir: Path) -> tuple[bool, str]:
    """validate_book_ready.py's B9 — is every chapter's articulation actually
    finished, or is something still silently stuck partial/reverted?

    Exempt (passes with a note) when there's no fluency report at all — a
    companion/non-translation book, or one whose reading edition was built
    before this pass existed, same exemption every other B-gate already
    grants itself. `superseded_status` (chained forward by
    `_book_pass_reports.merge_records` — see that module) is the field to
    read, not `status`, because `status` can say `composer-edit` for a
    chapter a human now owns even though the articulation pass itself never
    finished it; `composer-edit` chapters are always exempt regardless, since
    the pipeline defers to the human there.
    """
    book_dir = Path(book_dir)
    report_path = book_dir / "_system" / "book-fluency-report.json"
    if not report_path.is_file():
        return True, "no book-fluency-report.json — articulation contract does not apply"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return True, f"book-fluency-report.json unreadable, skipping ({e})"

    stuck: list[str] = []
    for chapter in report.get("chapters", []):
        status = chapter.get("superseded_status") or chapter.get("status")
        if status in ("partial", "reverted", "skipped"):
            stuck.append(chapter.get("title", "?"))
    if not stuck:
        return True, f"{len(report.get('chapters', []))} chapter(s) all articulated"

    reconcile = _load(book_dir)
    unresolved = [t for t in stuck if not reconcile["chapters"].get(t, {}).get("resolved")]
    if not unresolved:
        return True, f"{len(stuck)} chapter(s) were stuck but reconcile ledger shows all resolved"
    return (
        False,
        f"{len(unresolved)} chapter(s) still not fully articulated and unresolved in "
        f"articulation-reconcile.json: {unresolved[:3]}{'...' if len(unresolved) > 3 else ''} "
        "— run reconcile_articulation.py",
    )


def _prior_gate_findings(book_dir: Path, chapter_title: str) -> list[str]:
    data = _load(book_dir)
    entry = data["chapters"].get(chapter_title)
    if not entry:
        return []
    seen: list[str] = []
    for attempt in entry.get("log", []):
        for finding in attempt.get("gate_findings", []):
            if finding not in seen:
                seen.append(finding)
    return seen


def _wrap_repair_with_history(repair_fn: Callable[..., str], history_by_label: dict[str, list[str]]):
    """Wrap a repair_fn so each window's repair prompt sees every DISTINCT gate
    reason recorded for its chapter so far, not just this window's own latest
    failure — the "genuinely different, not a re-roll" part of a second
    attempt. `label` here is the per-window part label
    (`"<prefix>-NN-part-MM"`); history is keyed by chapter title, since that's
    the granularity `record_chapter_attempt` persists at.
    """

    def wrapped(title, base_text, candidate_text, gates, book_dir, label, log, **kwargs):
        prior = history_by_label.get(title, [])
        merged = list(gates)
        for finding in prior:
            if finding not in merged:
                merged.append(finding)
        return repair_fn(title, base_text, candidate_text, merged, book_dir, label, log, **kwargs)

    return wrapped


def _chapter_numbers_by_title(book_md_path: Path) -> dict[str, int]:
    """Map each chapter title to its 1-based section number, EXACTLY the way
    `_book_voice._run_pass` numbers sections — including the introduction as
    section 1 when present. `records` (returned by `_run_pass`) has NO entry
    for the introduction, so `enumerate(records, start=1)` silently
    off-by-ones every chapter number whenever a book opens with one — which is
    most books composed by this pipeline. Re-deriving the numbering here,
    against the same regex and the same anchor_key, is what keeps `only=[...]`
    on a retry pointed at the chapter it means to hit.
    """
    import re

    from _book_edits import anchor_key
    from _book_voice import _CHAPTER_HEADING_RE, _INTRODUCTION_KEY, _LEGACY_INTRODUCTION_KEY

    text = Path(book_md_path).read_text(encoding="utf-8")
    parts = _CHAPTER_HEADING_RE.split(text)
    numbers: dict[str, int] = {}
    for i in range(1, len(parts), 2):
        head = parts[i]
        if anchor_key(head) in (_INTRODUCTION_KEY, _LEGACY_INTRODUCTION_KEY):
            continue
        number = i // 2 + 1
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        numbers[title] = number
    return numbers


def reconcile_records(
    book_dir: Path,
    book_md: Path,
    records: list[dict],
    *,
    fn: Callable[..., str],
    repair_fn: Callable[..., str] | None,
    frame: str | None,
    narrator_subject: str,
    window_words: int,
    log=print,
) -> tuple[str, list[dict]]:
    """Persist every partial/reverted chapter's findings, then give the ones
    still open ONE more bounded attempt with accumulated context. Returns
    (book_md's current text, the merged records) — unchanged if nothing was
    open. Safe to call even when `repair_fn` is None (still persists; the
    retry then only benefits from a fresh model call, not repair feedback).
    """
    open_titles: list[str] = []
    for record in records:
        status = record.get("status")
        title = record.get("title", "")
        if status in ("partial", "reverted"):
            record_chapter_attempt(book_dir, title, status, record.get("gates", []), attempt_kind="pass")
            open_titles.append(title)

    if not open_titles:
        return book_md.read_text(encoding="utf-8"), records

    numbers_by_title = _chapter_numbers_by_title(book_md)
    open_numbers = [numbers_by_title[t] for t in open_titles if t in numbers_by_title]
    if not open_numbers:
        return book_md.read_text(encoding="utf-8"), records

    log(f"    articulation-reconcile: {len(open_numbers)} chapter(s) still need reconciling — one more attempt")
    history = {title: _prior_gate_findings(book_dir, title) for title in open_titles}
    wrapped_repair = _wrap_repair_with_history(repair_fn, history) if repair_fn else None

    from _book_voice import _run_pass  # deferred: _book_voice imports this module too

    new_text, retry_records = _run_pass(
        book_md,
        fn,
        log=log,
        noun="reconcile",
        label_prefix="reconcile",
        only=open_numbers,
        frame=frame,
        narrator_subject=narrator_subject,
        force=True,
        window_words=window_words,
        repair_fn=wrapped_repair,
    )
    book_md.write_text(new_text, encoding="utf-8")

    # retry_records has the SAME titles in the SAME order as records (both
    # walk every non-introduction section of the same book.md) — only the
    # 1-based section NUMBER is offset when an introduction precedes chapter
    # 1, so the merge keys on title, never on the numbers used above.
    open_title_set = set(open_titles)
    merged = [
        retry_records[i] if records[i].get("title", "") in open_title_set else records[i] for i in range(len(records))
    ]
    for title in open_titles:
        record = next((r for r in merged if r.get("title") == title), None)
        if record is None:
            continue
        record_chapter_attempt(
            book_dir,
            title,
            record.get("status", "reverted"),
            record.get("gates", []),
            attempt_kind="second-attempt",
        )
    return new_text, merged
