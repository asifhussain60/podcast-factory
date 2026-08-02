"""_book_pass_reports.py — the honesty layer for the fluency/voice pass reports.

The adaptive passes in ``_book_voice`` each write a per-chapter report
(``_system/book-fluency-report.json`` / ``book-voice-report.json``) saying what
they did. This module owns everything that keeps those reports TRUE after the
pass itself has finished:

  * ``merge_records`` — carries a prior run's per-chapter records through a
    targeted ``only=`` re-run without erasing them, and without resurrecting a
    claim the Composer-edit replay has invalidated;
  * ``reconcile_reports_after_replay`` — re-stamps chapters whose adapted text
    a replayed Book Composer edit overwrote later in the same compose.

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
        data["schema"] = schema
        data[count_key] = sum(1 for r in records if isinstance(r, dict) and r.get("status") in KEPT_STATUSES)
        data["overwritten_by_replay"] = sum(
            1 for r in records if isinstance(r, dict) and r.get("status") == STATUS_OVERWRITTEN
        )
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        log(f"    {name[: -len('.json')]}: {changed} chapter(s) re-stamped '{STATUS_OVERWRITTEN}'")
        total += changed
    return total
