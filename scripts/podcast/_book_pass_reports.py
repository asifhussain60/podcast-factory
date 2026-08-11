"""_book_pass_reports.py — the honesty layer for the fluency/voice pass reports.

The adaptive passes in ``_book_voice`` each write a per-chapter report
(``_system/book-fluency-report.json`` / ``book-voice-report.json``) saying what
they did. This module owns everything that keeps those reports TRUE after the
pass itself has finished:

  * ``merge_records`` — carries a prior run's per-chapter records through a
    targeted ``only=`` re-run without erasing them, and without resurrecting a
    claim the Composer-edit replay has invalidated;
  * ``reconcile_reports_after_replay`` — re-stamps chapters whose adapted text
    a replayed Book Composer edit overwrote later in the same compose;
  * ``record_rearticulation`` — the other side of that same ledger: re-stamps
    one chapter once ``rearticulate_chapter`` has put articulated prose back.

Split out of ``_book_voice.py`` on 2026-07-22 (DR-005): the passes produce
prose, this module produces truth about the prose, and the two change for
different reasons — RCA-001 was entirely a failure of the second concern.
"""

from __future__ import annotations

import json
from pathlib import Path

from _book_edits import anchor_key

# A chapter a pass adapted whose text was then replaced by a replayed Book
# Composer edit LATER IN THE SAME COMPOSE. The old report kept saying "adapted"
# — true of what the pass produced, false of what the book kept — and on
# 2026-07-21 that honesty gap let 8 discarded chapters ship through every gate
# (RCA-001). ``reconcile_reports_after_replay`` stamps this status after the
# replay; the original claim survives in ``pre_replay_status``.
STATUS_OVERWRITTEN = "adapted-then-overwritten"
# Statuses that assert "this pass's output is what the book now carries".
KEPT_STATUSES = ("adapted", "partial")


def merge_records(
    previous: list[dict], current: list[dict], *, edited_keys: frozenset[str] | set[str] = frozenset()
) -> list[dict]:
    """Carry a prior run's per-chapter records through a targeted re-run.

    A pass run with ``only=`` marks every other chapter ``skipped``. Writing that
    straight out ERASES the record of the full run that produced the text now on
    disk — the report then says "0 adapted, 8 skipped" for a book whose chapters
    were all adapted an hour earlier. That misreads as "the pass did nothing",
    and on 2026-07-20 it sent a reviewer to exactly that wrong conclusion. A
    skipped chapter therefore keeps whatever the previous report said about it.

    ``composer-edit`` is the same trap wearing a different word. A chapter the
    human has since authored is no longer adapted by this pass, but it very likely
    WAS adapted before they took it over, and replacing the record outright loses
    that. It keeps its new status — that is the true and current fact — and carries
    what the last report said in ``superseded_status``, so the reviewer can still
    see the chapter has a history.

    The carried value is what the pass last said BEFORE any takeover — the prior
    record's own ``superseded_status`` when it has one. Carrying the prior
    ``status`` unconditionally chained ``composer-edit`` onto itself from the
    second run onward, erasing the "was adapted" origin the field exists to keep
    (and making the Composer's articulation guard warn on chapters that were
    legitimately adapted before the human took them over).

    ``edited_keys`` closes the remaining honesty hole (RCA-001): inheriting is
    only truthful while the inherited claim still describes the book. A prior
    "adapted" for a chapter that NOW carries a Composer edit describes text the
    replay has overwritten (or is about to, later in this same compose) — so the
    inherited status is demoted to ``adapted-then-overwritten`` instead of being
    resurrected as a live claim. The original stays in ``pre_replay_status``.
    """
    prior = {r.get("title"): r for r in previous if r.get("title")}
    merged: list[dict] = []
    for record in current:
        title = record.get("title")
        status = record.get("status")
        if status == "skipped" and title in prior:
            inherited = prior[title]
            if inherited.get("status") in KEPT_STATUSES and anchor_key(str(title)) in edited_keys:
                inherited = {
                    **inherited,
                    "pre_replay_status": inherited.get("status"),
                    "status": STATUS_OVERWRITTEN,
                }
            merged.append(inherited)
        elif status == "composer-edit" and title in prior:
            p = prior[title]
            superseded = p.get("superseded_status") or p.get("status")
            merged.append({**record, "superseded_status": superseded})
        else:
            merged.append(record)
    return merged


def load_prior_records(report_path: Path) -> list[dict]:
    if not report_path.exists():
        return []
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = data.get("chapters")
    return records if isinstance(records, list) else []


# Report file -> (schema stamped on rewrite, top-level kept-count key).
_RECONCILED_REPORTS = (
    ("book-fluency-report.json", "podcast.book-fluency/v5", "adapted"),
    ("book-voice-report.json", "podcast.book-voice/v5", "revoiced"),
)


def restamp_counts(data: dict, records: list, *, schema: str, count_key: str) -> None:
    """Recompute EVERY status-derived top-level count from ``records``.

    ONE function because there were three copies, and all three were wrong in the
    same way: each re-derived ``adapted``/``revoiced`` and ``overwritten_by_replay``
    and none of them touched ``reverted``. A re-stamp that moved a chapter OFF
    ``reverted`` therefore left the summary frozen at the old number while the
    per-chapter record beside it told the truth — the report contradicting itself
    inside one file.

    That is not hypothetical. On kitab-al-riyad three chapters were reverted by the
    fidelity gates on 2026-08-08, then rearticulated one at a time over the next two
    days; each rearticulation correctly restamped its record to ``composer-edit`` and
    correctly recomputed ``adapted``, and ``reverted`` stayed at 3 through all of it.
    The book was never damaged — ``output_words == base_words`` on all three, so the
    faithful base was what stood — but `test_articulation_state_is_intact` reads the
    summary and had been red for a day, reporting a regression that had already been
    repaired. A gate that cries wolf about work already done is one people learn to
    silence.

    Writing every count from one place is what stops the next counter being added to
    two of three call sites. The tally is over the records the caller is about to
    persist, so the drop-a-section path passes its filtered list rather than the
    original.
    """

    def tally(predicate) -> int:
        return sum(1 for r in records if isinstance(r, dict) and predicate(r))

    data["schema"] = schema
    data[count_key] = tally(lambda r: r.get("status") in KEPT_STATUSES)
    data["reverted"] = tally(lambda r: r.get("status") == "reverted")
    data["overwritten_by_replay"] = tally(lambda r: r.get("status") == STATUS_OVERWRITTEN)


def reconcile_reports_after_replay(book_dir: Path, replay_report: dict | None, *, log=print) -> int:
    """Re-stamp the pass reports after the Composer-edit replay. Returns how many
    adapted chapters the replay discarded.

    A pass report is written when the pass runs — steps before the replay — so
    "adapted" is a claim about the book AT THAT MOMENT. When the replay then
    writes a saved Composer edit over an adapted chapter (under ``--force``, or
    when a save landed mid-run between the pass and the replay), the claim goes
    stale in the same compose that made it, and RCA-001 showed exactly that
    report waving 8 discarded chapters through every downstream gate. This runs
    directly after the replay and demotes each such chapter to
    ``adapted-then-overwritten`` (original claim kept in ``pre_replay_status``),
    recomputing the top-level counts so they only ever count SURVIVING work.

    Deliberately conservative: it only ever narrows a claim, never restores one,
    and an unreadable report is left alone — this is a truth-teller, not a gate.
    """
    applied_keys = {
        str(r.get("chapter_key"))
        for r in (replay_report or {}).get("chapters", [])
        if r.get("chapter_key") and not r.get("skipped")
    }
    if not applied_keys:
        return 0
    book_dir = Path(book_dir)
    total = 0
    for name, schema, count_key in _RECONCILED_REPORTS:
        path = book_dir / "_system" / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records = data.get("chapters")
        if not isinstance(records, list):
            continue
        changed = 0
        for record in records:
            if not isinstance(record, dict) or record.get("status") not in KEPT_STATUSES:
                continue
            if anchor_key(str(record.get("title") or "")) in applied_keys:
                record["pre_replay_status"] = record.get("status")
                record["status"] = STATUS_OVERWRITTEN
                changed += 1
        if not changed:
            continue
        restamp_counts(data, records, schema=schema, count_key=count_key)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        log(f"    {name[: -len('.json')]}: {changed} chapter(s) re-stamped '{STATUS_OVERWRITTEN}'")
        total += changed
    return total


def record_rearticulation(book_dir: Path, title: str, status: str, *, log=print) -> int:
    """Re-stamp one chapter after an on-demand rearticulation. Returns reports changed.

    ``rearticulate_chapter`` articulates a single chapter and records the result
    as a Composer edit — the prose on disk is now adapted, but the pass report
    still carries whatever the last full compose said about it, which for the
    chapter that needed the tool is ``adapted-then-overwritten``. Left alone, the
    report goes on calling articulated prose un-articulated: the Composer keeps
    warning, and `articulationWarningsFrom` keeps refusing to clear a chapter
    that is in fact fine. This is the same honesty duty as
    ``reconcile_reports_after_replay``, on the other side of the ledger.

    The stamp is ``composer-edit`` + ``superseded_status`` — deliberately NOT a
    bare ``adapted``. A rearticulated chapter IS owned by a Composer save (that
    is what makes it durable), so ``adapted`` would be demoted straight back to
    ``adapted-then-overwritten`` by ``merge_records``' ``edited_keys`` rule on
    the very next targeted re-run. The takeover shape is both true and stable:
    the pass adapted this chapter, then a save took it over — which is exactly
    what happened, in that order, inside one command.

    Conservative like its siblings: only a report that already names the chapter
    is touched, an unreadable report is left alone, and a status the pass does
    not count as kept is refused rather than laundered into one.
    """
    if status not in KEPT_STATUSES:
        return 0
    key = anchor_key(title or "")
    if not key:
        return 0
    book_dir = Path(book_dir)
    total = 0
    for name, schema, count_key in _RECONCILED_REPORTS:
        path = book_dir / "_system" / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records = data.get("chapters")
        if not isinstance(records, list):
            continue
        changed = False
        for record in records:
            if not isinstance(record, dict):
                continue
            if anchor_key(str(record.get("title") or "")) != key:
                continue
            record.pop("pre_replay_status", None)
            record["status"] = "composer-edit"
            record["superseded_status"] = status
            changed = True
        if not changed:
            continue
        restamp_counts(data, records, schema=schema, count_key=count_key)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        log(f"    {name[: -len('.json')]}: {title!r} re-stamped 'composer-edit' (superseded '{status}')")
        total += 1
    return total


def drop_section_from_reports(book_dir: Path, title: str, *, log=print) -> int:
    """Forget a section the pass reports still describe as a chapter.

    Folding the source's own opening into chapter 1 removes a `## ` section from
    the edition. The pass reports were written while that section existed and go on
    naming it, so a nine-chapter book ships with a fluency report claiming ten
    adapted chapters — which is not a rounding error but a report describing a
    document nobody has. `test_articulation_state_is_intact` catches exactly this,
    and caught it on `ayyuhal-walad` (2026-08-03).

    The prose is NOT lost, it moved, so this is bookkeeping rather than a retreat:
    what the pass did to those words still stands, it is simply no longer a
    chapter's worth of work. Counts are recomputed the same way
    ``reconcile_reports_after_replay`` recomputes them, so both paths agree.

    Idempotent and conservative: a report that does not name the section, or that
    cannot be parsed, is left exactly as it is.
    """
    key = anchor_key(title or "")
    if not key:
        return 0
    book_dir = Path(book_dir)
    total = 0
    for name, schema, count_key in _RECONCILED_REPORTS:
        path = book_dir / "_system" / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records = data.get("chapters")
        if not isinstance(records, list):
            continue
        kept = [r for r in records if not (isinstance(r, dict) and anchor_key(str(r.get("title") or "")) == key)]
        if len(kept) == len(records):
            continue
        data["chapters"] = kept
        restamp_counts(data, kept, schema=schema, count_key=count_key)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        log(f"    {name[: -len('.json')]}: dropped {title!r} — it is no longer a section of the edition")
        total += len(records) - len(kept)
    return total
