"""_step_ledger.py — one record per pipeline step, whether or not it spent money.

WHY THIS EXISTS

  Before this, a step left a trace only if it did one of two things: spent money
  (`_cost_ledger.append_cost_row`) or threw (`_compose_skips.record_skip`). A step
  that ran and quietly did nothing left NOTHING — so a deterministic pass that
  no-op'd because of a bug was indistinguishable from one that worked correctly.

  That blind spot covers most of the pipeline. The nineteen apparatus steps in
  `_book_apparatus`, the vowelling, the glossary vowelling, the Arabic alignment
  and the paragraph mirror are all deterministic: they spend nothing, so the cost
  ledger never mentions them, and on success they say nothing either. The only
  evidence a book had an Arabic overlay applied was the page itself.

  This ledger is the missing record: EVERY step appends one line saying what it
  did, and `_phase_review` reads those lines to judge whether the phase actually
  worked rather than trusting its exit status.

WHAT AN OUTCOME MEANS

  ok       ran and changed something (the normal success)
  noop     ran, found nothing to do, and that is legitimate (e.g. a book with no
           Arabic has nothing to vowel). Distinct from `ok` ON PURPOSE: a review
           gate can then ask "did this no-op when its inputs say it had work?",
           which is the shape most silent-failure bugs actually take.
  skipped  deliberately not run — a config knob turned it off
  failed   raised

DESIGN NOTES

  * Append-only JSONL with the same `fcntl.LOCK_EX` critical section the cost
    ledger uses, because `run_windowed` already writes from several threads and
    the per-chapter loop is about to.
  * `run_id` scopes each line to one orchestrator run, so history is preserved
    (a book keeps every run's records) while a reader can still ask "what did
    THIS run do" — the mistake `compose-skips.json` made until 2026-07-21, when
    it appended forever and a skip fixed three runs ago still read as current.
  * Every write is wrapped: a recorder must never become the failure it records.
    This is the same rule `record_skip` follows, and it matters more here because
    this one is called from every step in the pipeline.
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "podcast.step-ledger/v1"
RECORD_NAME = "step-ledger.jsonl"

#: The four outcomes. See the module docstring for what each one asserts.
OUTCOME_OK = "ok"
OUTCOME_NOOP = "noop"
OUTCOME_SKIPPED = "skipped"
OUTCOME_FAILED = "failed"
OUTCOMES = frozenset({OUTCOME_OK, OUTCOME_NOOP, OUTCOME_SKIPPED, OUTCOME_FAILED})


@dataclass
class StepRecord:
    ts: str
    phase: str
    step: str
    outcome: str
    duration_ms: int = 0
    run_id: str | None = None
    error: str | None = None
    #: Step-declared evidence. Free-form by design — a step knows what proves it
    #: worked and a central schema would only go stale. Conventional keys the
    #: review gates understand: `outputs` / `inputs` (lists of {path, bytes}) and
    #: `changed` (int, items altered).
    evidence: dict[str, Any] = field(default_factory=dict)


def ledger_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / RECORD_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id() -> str | None:
    try:
        from _runlog import current_run_id

        return current_run_id()
    except Exception:
        return None


def file_evidence(*paths: Path | str) -> list[dict[str, Any]]:
    """[{path, bytes}] for each path — the common shape of output evidence.

    A missing path is recorded with `bytes: None` rather than omitted, because
    "the step claims it wrote this and it is not there" is precisely what a review
    gate needs to see. Dropping it would hide the finding.
    """
    out: list[dict[str, Any]] = []
    for p in paths:
        p = Path(p)
        try:
            out.append({"path": p.name, "bytes": p.stat().st_size})
        except OSError:
            out.append({"path": p.name, "bytes": None})
    return out


def record_step(
    book_dir: Path,
    *,
    phase: str,
    step: str,
    outcome: str,
    duration_ms: int = 0,
    evidence: dict[str, Any] | None = None,
    error: str | None = None,
) -> StepRecord | None:
    """Append one line to <book_dir>/_system/step-ledger.jsonl.

    Returns the record, or None if it could not be written — never raises. An
    unknown `outcome` is recorded verbatim rather than rejected: a caller passing
    a typo should show up in the ledger as an oddity a gate can flag, not crash
    the pipeline step it was only trying to describe.
    """
    row = StepRecord(
        ts=_now_iso(),
        phase=str(phase),
        step=str(step),
        outcome=str(outcome),
        duration_ms=int(duration_ms),
        run_id=_run_id(),
        error=error,
        evidence=dict(evidence or {}),
    )
    try:
        import fcntl as _fcntl

        path = ledger_path(book_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
            try:
                f.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
                f.flush()
            finally:
                _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)
    except Exception:  # a recorder must never become the failure it records
        return None
    return row


@contextmanager
def step(
    book_dir: Path,
    phase: str,
    name: str,
    *,
    log=None,
):
    """Time a step, record exactly one line for it, and re-raise on failure.

    The ergonomic path for wrapping an existing step without restructuring it::

        with step(book_dir, "0book-compose", "inline-arabic") as rec:
            n = apply_inline_arabic(book_dir)
            rec.changed(n)
            rec.outputs(book_dir / "book" / "book.md")

    Defaults to `ok`. A step that legitimately had nothing to do calls
    `rec.noop("why")`; one turned off by config calls `rec.skipped("why")`. An
    exception is recorded as `failed` WITH its message and then re-raised — this
    context manager deliberately does not swallow, so it can be dropped around a
    step whose caller already has its own error handling (as every apparatus step
    does) without changing that behaviour.
    """

    class _Rec:
        def __init__(self) -> None:
            self.outcome = OUTCOME_OK
            self.evidence: dict[str, Any] = {}
            self.note: str | None = None

        def noop(self, why: str = "") -> None:
            self.outcome = OUTCOME_NOOP
            if why:
                self.evidence["why"] = why

        def skipped(self, why: str = "") -> None:
            self.outcome = OUTCOME_SKIPPED
            if why:
                self.evidence["why"] = why

        def changed(self, n: int) -> None:
            self.evidence["changed"] = int(n)

        def outputs(self, *paths: Path | str) -> None:
            self.evidence["outputs"] = file_evidence(*paths)

        def inputs(self, *paths: Path | str) -> None:
            self.evidence["inputs"] = file_evidence(*paths)

        def detail(self, **kw: Any) -> None:
            self.evidence.update(kw)

    rec = _Rec()
    t0 = time.monotonic()
    try:
        yield rec
    except BaseException as e:
        record_step(
            book_dir,
            phase=phase,
            step=name,
            outcome=OUTCOME_FAILED,
            duration_ms=int((time.monotonic() - t0) * 1000),
            evidence=rec.evidence,
            error=f"{type(e).__name__}: {e}",
        )
        raise
    record_step(
        book_dir,
        phase=phase,
        step=name,
        outcome=rec.outcome,
        duration_ms=int((time.monotonic() - t0) * 1000),
        evidence=rec.evidence,
    )


# ─── Readers ─────────────────────────────────────────────────────────────────


def read_steps(book_dir: Path, *, phase: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
    """Every recorded step, oldest first. Filters are AND-ed.

    A malformed line is skipped rather than raising: this feeds review gates, and
    one bad line must not blind a gate to the rest of the run.
    """
    path = ledger_path(book_dir)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        if phase is not None and row.get("phase") != phase:
            continue
        if run_id is not None and row.get("run_id") != run_id:
            continue
        rows.append(row)
    return rows


def latest_run_id(book_dir: Path) -> str | None:
    """The run_id of the most recent recorded step, or None."""
    rows = read_steps(book_dir)
    for row in reversed(rows):
        rid = row.get("run_id")
        if rid:
            return str(rid)
    return None


def latest_steps(book_dir: Path, *, phase: str | None = None) -> list[dict[str, Any]]:
    """Steps from the most recent run only — 'what did THIS run do'.

    Falls back to every record when nothing carries a run_id, so a book whose
    steps predate run correlation still reports something rather than nothing.
    """
    rid = latest_run_id(book_dir)
    if rid is None:
        return read_steps(book_dir, phase=phase)
    return read_steps(book_dir, phase=phase, run_id=rid)


def outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    """{outcome: count} over the given rows."""
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("outcome") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def last_by_step(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """{step: its most recent record} — a step retried within one run reports its
    final outcome, not its first, so a recovered failure is not read as a defect."""
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("step") or "")
        if name:
            out[name] = row
    return out
