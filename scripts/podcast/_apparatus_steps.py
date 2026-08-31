"""_apparatus_steps.py — the compose apparatus's step vocabulary and its recorder.

Split out of `_book_apparatus` on 2026-08-08, for two reasons beyond the DR-005 line
cap that forced the moment:

  * `_phase_review`'s gate PC2 needs the step LIST and nothing else. Importing it from
    `_book_apparatus` pulled the whole apparatus — and every module it lazily
    imports — into a review that only wanted twenty-five strings.
  * The list is a CONTRACT between three readers: the apparatus that records against
    it, `_compose_skips` which classifies each name as page-altering or advisory, and
    the review gate that compares recorded against declared. A contract with three
    readers belongs in its own file rather than inside one of them.
"""

from __future__ import annotations

from pathlib import Path

from _step_ledger import record_step as _record_step

#: The modules that HOST apparatus steps — i.e. that contain `_ok(...)` /
#: `_record_skip(...)` call sites. Declared here because three separate tests scan those
#: call sites to pin the vocabulary against `APPARATUS_STEPS` and against
#: `_compose_skips`' classification, and on 2026-08-08 all three broke at once when the
#: report-only steps moved to `_book_reports`: each test had `_book_apparatus.py`
#: hard-coded. One list, so the next split updates them together instead of silently
#: dropping whichever steps moved.
APPARATUS_MODULES: tuple[str, ...] = ("_book_apparatus.py", "_book_reports.py", "_book_typography.py")

#: The phase every apparatus step files under. The apparatus is the tail of a compose
#: whether it was reached through `compose_book_v2` or run standalone by
#: `apply_book_apparatus.py`, so both callers use the same phase — a review gate asking
#: "did this compose run its steps" must get the same answer either way.
PHASE = "0book-compose"

#: Every step the apparatus runs, in order, declared ONCE so a review gate can ask the
#: question that matters: not "did anything fail" but "did each step it was supposed to
#: run actually leave a record". A step that vanished from the sequence entirely used to
#: be undetectable — nothing failed, so nothing was reported.
#:
#: These names are also the keys `_compose_skips` classifies as page-altering or
#: advisory, so one vocabulary serves the skip record, the ledger and the gate. A test
#: pins this list against the recording sites in `_book_apparatus` and `_book_reports`,
#: so a step cannot be added to either without being declared here.
APPARATUS_STEPS: tuple[str, ...] = (
    "composer-edits",
    "report-reconcile",
    "front-matter",
    "opening-fold",
    "introduction",
    "translit",
    "quran-arabic",
    "citation-names",
    "glossary-harvest",
    "annotation-policy",
    "etymology",
    "glossary-vowelling",
    "inline-arabic",
    "text-shape",
    "vowelling",
    "arabic-substitution",
    "spelling",
    "opening",
    "arabic-audit",
    "duplication",
    "defect-scan",
    "visual-policy",
    "bridges",
    "honorifics",
    "arabic-alignment",
    "paragraph-mirror",
    "substitution-restamp",
)


def record_ok(book_dir: Path, name: str, *, outcome: str = "ok", **evidence) -> None:
    """Record that `name` finished. Never raises — see `_step_ledger.record_step`.

    Called as the LAST statement inside each step's existing `try`, so it adds a record
    without touching control flow: the surrounding `except` still owns failures (and
    records them too, via `_compose_skips.record_skip`). `outcome="noop"` is for a step
    that legitimately had nothing to do, `"skipped"` for one a config knob or an
    idempotency marker turned off — a review gate needs those apart from `ok`, because
    "ran and changed nothing" is what most silent-failure bugs look like.
    """
    _record_step(book_dir, phase=PHASE, step=name, outcome=outcome, evidence=evidence)
