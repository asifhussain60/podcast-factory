#!/usr/bin/env python3
"""Every state a book can reach must be a state a book can resume from.

The pipeline's phase drivers and its resume dispatcher are written independently:
a driver calls `update_phase(phase=..., status=...)`, and `run_resume` matches on
`(state.phase, state.phase_status)` to pick the driver that continues the run.
Nothing connected the two. Every existing test covers ONE phase or ONE lane, so a
driver could write a state the dispatcher had no branch for and no test noticed —
`run_resume` falls through to "No automated action for current phase" and returns
3, the watchdog reads 3 as a generic crash, and the book spends its whole attempt
budget re-running a command that cannot advance it.

That is not hypothetical. On 2026-08-08 this harness found eight such states across
five phases, the worst being `per-chapter-optimize`, whose own failure message reads
"Fix P0s and --resume" ([chapter_driver.py:513]) — a printed instruction that could
not work, because the dispatcher had no branch for that phase at all.

So this file derives the reachable states FROM THE CODE rather than from a
hand-kept list, and drives the real dispatcher against each one:

  1. `_reachable_pairs` walks every non-test module under scripts/podcast/ and
     collects every literal `(phase, status)` an `update_phase` call can write.
  2. `DYNAMIC_SITES` declares the pairs the call sites with a computed phase or
     status can produce. A new module with a computed site fails
     `test_every_dynamic_call_site_is_declared` until it is added here — the
     scanner cannot read those, so they are declared instead of guessed.
  3. `NON_RESUMABLE` names the states that deliberately have no automatic
     branch, each with its reason. This list must shrink, never grow silently;
     the pre-0a entries carry their `--retry-phase` recovery, and
     `RetryPhaseRecoveryTests` proves that recovery actually dispatches, so the
     allowlist cannot become a place where holes go to be forgotten.

Nothing here spends a model call or touches a real book: the four drivers are
mocked and asserted on, exactly as `test_resume_dispatcher_book_lane.py` does.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import sys
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _progress import PHASES, STALE_RUNNING_SEC, state_path  # noqa: E402
from phases import resume_dispatcher  # noqa: E402

# ── what the code can write ──────────────────────────────────────────────────

# Call sites whose phase or status is a variable. The AST scan cannot resolve
# these, so the pairs they can produce are declared here, keyed by module. The
# key set is asserted against the scan, so a NEW computed site anywhere fails
# this file rather than quietly widening what the pipeline can reach.
_INITIAL_PHASE_MAP = ("0b", "0c", "0ci", "0d", "0e")
_BOOK_LANE = ("0book-design", "0book-compose", "0book-illustrate", "0book-slide-import", "0book-render")

DYNAMIC_SITES: dict[str, tuple[tuple[str, str], ...]] = {
    # `phase_map` in `_drive_authoring_through_0f`, plus the three phases a
    # source-ready book stamps out of band because it has no PDF to ingest.
    "phases/initial_driver.py": tuple(
        (phase, status) for phase in _INITIAL_PHASE_MAP for status in ("running", "completed", "failed", "halted")
    )
    + (("pre-flight", "completed"), ("branch", "completed"), ("scaffold", "completed")),
    # `_BOOK_PHASES` stamped skipped when the book opts out of a reading edition
    # or curates its figures by hand, and the crash handler that fails whichever
    # book phase was running.
    "phases/book_driver.py": tuple((phase, "skipped") for phase in _BOOK_LANE)
    + tuple((phase, "failed") for phase in _BOOK_LANE),
    # Both audio phases are skipped together for a manual (NotebookLM) engine.
    "phases/audio_driver.py": (("audio-script", "skipped"), ("audio-render", "skipped")),
    # `_publish` re-stamps the cohort phase after every chapter; the terminal
    # status is failed when a majority of decks came back bad, else completed.
    "phases/slide_cohort.py": (
        ("per-chapter-slides", "running"),
        ("per-chapter-slides", "completed"),
        ("per-chapter-slides", "failed"),
    ),
    # The cost-ceiling halt re-stamps whatever phase is already current, so it
    # cannot produce a phase the run had not already reached on its own.
    "phases/resume_dispatcher.py": (),
}

# `update_phase` records 06a's own block as halted, then overrides the TOP-LEVEL
# phase_status to awaiting_human_review, which the dispatcher handles generically
# for every phase. The harness matches on the top-level value, so the block
# status alone would have it looking for a branch that must not exist.
TOP_LEVEL_STATUS_OVERRIDES: dict[tuple[str, str], str] = {
    ("06a", "halted"): "awaiting_human_review",
}

# States with no automatic dispatch, on purpose. Each entry is a decision, not an
# omission — anything without a reason good enough to write down here is a defect.
NON_RESUMABLE: dict[tuple[str, str], str] = {
    ("pre-flight", "completed"): (
        "an initial launch that dies before Azure ingest has nothing authored to continue; "
        "recovery is --retry-phase 0a, proved by RetryPhaseRecoveryTests"
    ),
    ("branch", "completed"): "same as pre-flight — recovery is --retry-phase 0a",
    ("scaffold", "completed"): "same as pre-flight — recovery is --retry-phase 0a",
    ("publish", "completed"): (
        "re-entering the publish driver re-runs publish, which flips the book live and deploys "
        "to Cloudflare; whether to repeat that is a human decision, never a watchdog's"
    ),
    ("trainer", "completed"): "same driver as publish — see publish/completed",
    ("merge", "completed"): "same driver as publish — see publish/completed",
}


def _module_pairs() -> tuple[dict[str, set[str]], set[str]]:
    """Every literal (phase, status) an update_phase call can write, and the
    modules holding a call site with a computed phase or status."""
    literal: dict[str, set[str]] = {}
    computed: set[str] = set()

    def _literal(node: ast.expr | None) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    for py in sorted(SCRIPTS_PODCAST.rglob("*.py")):
        if "tests" in py.relative_to(SCRIPTS_PODCAST).parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — a syntax error is another test's job
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "update_phase":
                continue
            kw = {k.arg: k.value for k in node.keywords}
            phase, status = _literal(kw.get("phase")), _literal(kw.get("status"))
            if phase and status:
                literal.setdefault(phase, set()).add(status)
            else:
                computed.add(str(py.relative_to(SCRIPTS_PODCAST)))
    return literal, computed


def _reachable_pairs() -> set[tuple[str, str]]:
    literal, _ = _module_pairs()
    pairs = {(phase, status) for phase, statuses in literal.items() for status in statuses}
    for declared in DYNAMIC_SITES.values():
        pairs.update(declared)
    return pairs


# ── driving the real dispatcher ──────────────────────────────────────────────

# Every driver `run_resume` can hand off to. A dispatched state calls exactly one.
DRIVERS = (
    "_drive_authoring_through_0f",
    "_drive_source_ready_through_0f",
    "_drive_per_chapter_and_after",
    "_drive_publish_through_done",
)

# The fall-through at the bottom of `run_resume`. Exit code 3 alone is NOT the
# signal — a phase parked at a human-review gate returns 3 too, and correctly so.
# Only this line means the dispatcher had no branch for the state it was handed.
FALL_THROUGH = "No automated action for current phase"


@dataclass(frozen=True)
class Dispatch:
    drivers: list[str]
    stranded: bool


def _state_for(phase: str, status: str) -> dict:
    """A state file parked at (phase, status), as a crashed run would leave it."""
    top = TOP_LEVEL_STATUS_OVERRIDES.get((phase, status), status)
    # A 'running' state at resume time belongs to a dead process — a live one is
    # kept out by the book lock. Age it past the staleness threshold so the
    # dispatcher's own auto-recovery downgrades it, which is what really happens.
    stale = datetime.now(timezone.utc) - timedelta(seconds=STALE_RUNNING_SEC + 60)
    idx = PHASES.index(phase)
    # `update_phase` advances last_completed_phase when a phase completes, and
    # several dispatcher branches key off it rather than off the phase id. A
    # fixture that left it pointing at the previous phase would send completed
    # states down branches production never sends them down.
    last = phase if status == "completed" else (PHASES[idx - 1] if idx else None)
    return {
        "schema_version": 1,
        "book_slug": "flow-harness-book",
        "category": "books",
        "phase": phase,
        "phase_status": top,
        "ts_updated": stale.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_completed_phase": last,
        "phases": {p: {"status": "completed" if PHASES.index(p) < idx else "pending"} for p in PHASES}
        | {phase: {"status": status}},
        "config": {},
    }


def _dispatch(phase: str, status: str, *, retry_phase: str | None = None) -> Dispatch:
    """Run the real dispatcher against (phase, status) and report what it did.

    The book directory is a real temporary one with `REPO_ROOT` pointed at its
    parent: the dispatcher's fall-through branch prints the state path relative to
    the repo root, so a fabricated path outside it raises ValueError and a
    stranded state would crash the harness instead of being reported as stranded.
    """
    args = argparse.Namespace(resume="flow-harness-book", stop_after=None, retry_phase=retry_phase, unattended=False)
    state = _state_for(phase, status)
    called: list[str] = []
    with TemporaryDirectory() as td:
        root = Path(td)
        book_dir = root / "flow-harness-book"
        (book_dir / "_system" / "source").mkdir(parents=True)
        # A retry of 0a re-runs Azure ingest, which needs exactly one PDF present.
        (book_dir / "_system" / "source" / "source.pdf").write_bytes(b"%PDF-1.4 stub")
        # The state goes to disk rather than through a mocked reader: the 0a and
        # cost-ceiling branches call the real `update_phase`, which refuses to run
        # without a state file, and a stubbed reader would hide that from the harness.
        # Written as raw JSON on purpose — `write_state` restamps `ts_updated` to
        # now, which would make every 'running' fixture look fresh and so skip the
        # staleness recovery that is the whole reason a crashed run can resume.
        state_path(book_dir).parent.mkdir(parents=True, exist_ok=True)
        state_path(book_dir).write_text(json.dumps(state, indent=2), encoding="utf-8")
        with ExitStack() as stack:
            enter = stack.enter_context
            enter(mock.patch.object(resume_dispatcher, "REPO_ROOT", root))
            enter(mock.patch.object(resume_dispatcher, "preflight_resume", return_value=(book_dir, [])))
            enter(mock.patch.object(resume_dispatcher, "cost_ceiling_check", return_value={"action": "ok"}))
            enter(mock.patch("phases.scaffold.phase_0a_ingest"))
            enter(mock.patch("phases.scaffold.phase_git_commit"))
            enter(
                mock.patch(
                    "phases.book_driver._drive_book_branch",
                    side_effect=lambda *a, **k: called.append("_drive_book_branch") or 0,
                )
            )
            for name in DRIVERS:
                enter(
                    mock.patch.object(
                        resume_dispatcher, name, side_effect=lambda *a, _n=name, **k: called.append(_n) or 0
                    )
                )
            out = io.StringIO()
            enter(redirect_stdout(out))
            enter(redirect_stderr(out))
            resume_dispatcher.run_resume(args)
    return Dispatch(drivers=called, stranded=FALL_THROUGH in out.getvalue())


# ── the harness ──────────────────────────────────────────────────────────────


class ReachabilityScanTests(unittest.TestCase):
    """The derivation itself has to be trustworthy before its verdict means anything."""

    def test_every_dynamic_call_site_is_declared(self) -> None:
        _, computed = _module_pairs()
        self.assertEqual(
            computed,
            set(DYNAMIC_SITES),
            "a call site with a computed phase or status is not declared in DYNAMIC_SITES — "
            "the scanner cannot read it, so the states it can reach would go unchecked",
        )

    def test_no_phase_id_outside_the_canonical_list_is_ever_written(self) -> None:
        literal, _ = _module_pairs()
        self.assertEqual(
            sorted(set(literal) - set(PHASES)),
            [],
            "update_phase raises on an unknown phase id, so this would be a crash in production",
        )

    def test_the_scan_finds_the_whole_pipeline_and_not_a_handful(self) -> None:
        # Guards against the scan silently matching nothing — an empty derivation
        # would make every assertion below pass while checking absolutely nothing.
        reached = {phase for phase, _ in _reachable_pairs()}
        self.assertGreaterEqual(len(reached), 25, f"only {len(reached)} of {len(PHASES)} phases scanned")


class EveryReachableStateResumesTests(unittest.TestCase):
    """The point of the file: no reachable state may fall through the dispatcher."""

    def test_no_reachable_state_falls_through_to_no_automated_action(self) -> None:
        stranded = [
            f"{phase}/{status}"
            for phase, status in sorted(_reachable_pairs())
            if (phase, status) not in NON_RESUMABLE and _dispatch(phase, status).stranded
        ]
        self.assertEqual(
            stranded,
            [],
            "these states can be reached but not resumed — the orchestrator answers "
            '"No automated action" and the watchdog burns its whole attempt budget: ' + ", ".join(stranded),
        )

    def test_every_resumable_state_reaches_exactly_one_driver(self) -> None:
        # A state that dispatches to two drivers has one of them running against
        # work the other already did — the 2026-08-07 publish cascade in miniature.
        multiples: list[str] = []
        for phase, status in sorted(_reachable_pairs()):
            if (phase, status) in NON_RESUMABLE:
                continue
            result = _dispatch(phase, status)
            if len(result.drivers) > 1:
                multiples.append(f"{phase}/{status} -> {result.drivers}")
        self.assertEqual(multiples, [], "; ".join(multiples))


class NonResumableAllowlistTests(unittest.TestCase):
    """The allowlist must stay small, honest, and about states that really exist."""

    def test_every_entry_names_a_state_that_is_actually_reachable(self) -> None:
        unreachable = sorted(pair for pair in NON_RESUMABLE if pair not in _reachable_pairs())
        self.assertEqual(
            unreachable,
            [],
            f"NON_RESUMABLE excuses states nothing can reach: {unreachable} — delete them, "
            "or the list stops describing the pipeline",
        )

    def test_every_entry_carries_a_reason(self) -> None:
        for pair, reason in NON_RESUMABLE.items():
            self.assertGreater(len(reason.strip()), 30, f"{pair} needs a real reason, got {reason!r}")

    def test_the_chapter_lane_is_not_on_the_list(self) -> None:
        # The three states this harness was written to find. They are inside the
        # most expensive lane in the pipeline, where a stranded book costs hours,
        # so closing them is never the same decision as excusing publish.
        for pair in (
            ("per-chapter", "completed"),
            ("per-chapter-optimize", "failed"),
            ("per-chapter-slides", "skipped"),
        ):
            self.assertNotIn(pair, NON_RESUMABLE, f"{pair} must dispatch, not be excused")


class ChapterLaneRecoveryTests(unittest.TestCase):
    """Named tests for the three defects, so a regression says which one broke."""

    def _assert_bounded(self, phase: str, status: str) -> None:
        result = _dispatch(phase, status)
        self.assertFalse(result.stranded, f"{phase}/{status} still has no dispatch")
        self.assertEqual(
            result.drivers,
            ["_drive_per_chapter_and_after"],
            f"{phase}/{status} must re-enter the BOUNDED chapter driver — routing a mid-run "
            "retry into the publish driver is the 2026-08-07 cascade, and publish deploys",
        )

    def test_a_blocked_optimize_can_be_resumed_as_its_error_message_promises(self) -> None:
        # chapter_driver prints "Fix P0s and --resume" on this exact state.
        self._assert_bounded("per-chapter-optimize", "failed")

    def test_a_crash_during_optimize_can_be_resumed(self) -> None:
        self._assert_bounded("per-chapter-optimize", "running")

    def test_a_skipped_optimize_can_be_resumed(self) -> None:
        self._assert_bounded("per-chapter-optimize", "skipped")

    def test_a_completed_optimize_can_be_resumed(self) -> None:
        self._assert_bounded("per-chapter-optimize", "completed")

    def test_a_crash_in_the_gap_after_the_chapter_loop_can_be_resumed(self) -> None:
        self._assert_bounded("per-chapter", "completed")

    def test_a_book_whose_slide_phase_was_skipped_can_be_resumed(self) -> None:
        self._assert_bounded("per-chapter-slides", "skipped")

    def test_a_notebooklm_book_whose_audio_phases_were_skipped_can_be_resumed(self) -> None:
        # The common case: a manual audio engine stamps both phases skipped.
        # audio-script already dispatched on any status; audio-render did not.
        self._assert_bounded("audio-render", "skipped")


class SourceReviewGateRecoveryTests(unittest.TestCase):
    """The approved source-review gate has a window with no branch either."""

    def test_a_crash_after_the_gate_was_approved_can_be_resumed(self) -> None:
        result = _dispatch("06a", "completed")
        self.assertFalse(result.stranded, "06a/completed has no dispatch")
        self.assertEqual(result.drivers, ["_drive_authoring_through_0f"])

    def test_the_gate_still_waits_for_a_human_rather_than_dispatching(self) -> None:
        # The fix must not turn an unapproved gate into an automatic advance. A
        # book at the gate reports awaiting_human_review and dispatches nothing.
        result = _dispatch("06a", "halted")
        self.assertEqual(result.drivers, [], "an unapproved source-review gate must not advance")
        self.assertFalse(result.stranded, "waiting for a human is not the same as being stranded")


class RetryPhaseRecoveryTests(unittest.TestCase):
    """The pre-0a excuses claim a recovery; this proves the claim."""

    def test_a_book_stranded_before_ingest_recovers_via_retry_phase_0a(self) -> None:
        for phase in ("pre-flight", "branch", "scaffold"):
            result = _dispatch(phase, "completed", retry_phase="0a")
            self.assertFalse(result.stranded, f"--retry-phase 0a does not recover {phase}/completed")
            self.assertTrue(result.drivers, f"--retry-phase 0a dispatched nothing for {phase}/completed")


class PublishIsNeverReachedByAccidentTests(unittest.TestCase):
    """The one thing this harness must not make easier: an unattended publish."""

    def test_no_chapter_or_book_lane_state_reaches_the_publish_driver(self) -> None:
        leaks: list[str] = []
        lane = ("per-chapter", "per-chapter-optimize", "per-chapter-slides") + _BOOK_LANE
        for phase, status in sorted(_reachable_pairs()):
            if phase not in lane or (phase, status) in NON_RESUMABLE:
                continue
            if "_drive_publish_through_done" in _dispatch(phase, status).drivers:
                leaks.append(f"{phase}/{status}")
        self.assertEqual(
            leaks,
            [],
            "a mid-run state routed into the publish driver, which flips the book live "
            f"and deploys without any re-check that a human approved finalize: {leaks}",
        )


if __name__ == "__main__":
    unittest.main()
