#!/usr/bin/env python3
"""P2.2 sunny-day end-to-end pipeline test.

Drives `_drive_authoring_through_0f()` against the tiny-book fixture with
the four `author_phase_0X` functions mocked. Verifies:

  • State machine advances 0b → 0c → 0d → 0e in order
  • Each phase produces its expected artifacts
  • Pipeline halts cleanly at the Phase 0f human-review gate
  • No 'NO ARTIFACT' log line escapes (P5.2 regression-protective)
  • numeric-disambiguation-register.md (P4 register) is produced

The mock strategy patches `author_phase_0b/c/d/e` at the `_authoring`
module level — replacing each with a stub that writes the artifacts the
real function would have written. This tests the ORCHESTRATION (state-
machine + commit cadence + halt semantics) without spending Azure / LLM
budget. The real phase prompts are tested separately under P19.2's
phase_prompts regression fixtures.

Uses stdlib `unittest` — no pytest dependency yet (P8.1).
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import orchestrate_book  # noqa: E402
import phases.initial_driver as initial_driver  # noqa: E402
import _authoring  # noqa: E402
import _progress  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "tiny-book"


class SunnyDayE2ETests(unittest.TestCase):
    """The pipeline's state machine advances cleanly through 0b → 0c → 0d → 0e → 0f-halt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "tiny-test-book"
        self._build_book_dir()
        self._track_log_lines: list[str] = []

    def tearDown(self):
        self.tmp.cleanup()

    # ── fixture scaffold ─────────────────────────────────────────────────────

    def _build_book_dir(self) -> None:
        """Initialize the tmp book dir with raw-extract + state.json at 0a-completed."""
        (self.book_dir / "_system" / "source" / "text").mkdir(parents=True)

        # Copy the canonical tiny-book raw-extract.md (post-OCR/translate state).
        raw = FIXTURES_DIR / "raw-extract.md"
        if not raw.exists():
            self.skipTest(
                f"tiny-book fixture missing at {raw} — P2.1 must ship before P2.2 runs."
            )
        (self.book_dir / "_system" / "source" / "text" / "raw-extract.md").write_text(
            raw.read_text()
        )

        # Initial state.json: pre-flight + branch + scaffold + 0a all completed;
        # 0b..0g pending. This is the canonical resume-from-0a state shape.
        state = {
            "schema_version": 1,
            "book_slug": "tiny-test-book",
            "category": "books",
            "branch": "book/tiny-test-book",
            "phase": "0b",
            "phase_status": "pending",
            "last_completed_phase": "0a",
            "next_phase": "0b",
            "last_error": None,
            "phases": {
                "pre-flight": {"status": "completed"},
                "branch":     {"status": "completed"},
                "scaffold":   {"status": "completed", "book_dir": str(self.book_dir)},
                "0a":         {"status": "completed"},
                "0b":         {"status": "pending"},
                "0c":         {"status": "pending"},
                "0d":         {"status": "pending"},
                "0e":         {"status": "pending"},
                "0f":         {"status": "pending"},
            },
            "config": {"length_tier": "extended", "unit_mode": "auto"},
        }
        _progress.write_state(self.book_dir, state)

    # ── deterministic mocks for the four LLM-authoring phases ────────────────
    # Each mock writes the artifacts the real phase would have written.
    # No mock returns a "NO ARTIFACT" pseudo-failure — that's the P2.3 territory.

    def _mock_0b(self, book_dir: Path, log=print, **_kw) -> str:
        text_dir = book_dir / "_system" / "source" / "text"
        # refined-english.md must be >100 words per P2.2 acceptance
        (text_dir / "refined-english.md").write_text(
            "Refined English narration produced by mocked Phase 0b. " * 30
        )
        # _chunks/0b/win-NNN.in.md must each have a non-zero matching .out.md
        chunks_dir = text_dir / "_chunks" / "0b"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, 3):
            (chunks_dir / f"win-{i:03d}.in.md").write_text("input chunk " * 25)
            (chunks_dir / f"win-{i:03d}.out.md").write_text("refined output " * 25)
        return "refined-english.md authored by mock 0b"

    def _mock_0c(self, book_dir: Path, log=print, **_kw) -> str:
        text_dir = book_dir / "_system" / "source" / "text"
        # _phonetics.md must be >100 words per P2.2 acceptance
        (text_dir / "_phonetics.md").write_text(
            "Arabic phonetic annotations produced by mocked Phase 0c. " * 30
        )
        # Lexicon sidecar
        (text_dir / "_lexicon.md").write_text("ilm: ILM\nsabr: SAH-br\n")
        return "_phonetics.md authored by mock 0c"

    def _mock_0d(self, book_dir: Path, length_tier: str = "extended",
                 unit_mode: str = "auto", log=print, **_kw) -> str:
        text_dir = book_dir / "_system" / "source" / "text"
        # Per-chapter contracts (P2.2 asserts ≥1)
        cc_dir = book_dir / "chapter-contracts"
        cc_dir.mkdir(parents=True, exist_ok=True)
        # FIX 14: contract must pass the Phase-0d post-write gate
        # (_contract_validation.validate_contract_full) like real 0d output.
        (cc_dir / "encounter.yml").write_text(
            "schema_version: 1\n"
            "chapter_ref: ch01-encounter\n"
            "slug: encounter\n"
            "source_type: book-chapter\n"
            "episode_number: 1\n"
            "title: The Encounter\n"
            "audience: Listeners new to the tiny test book.\n"
            "angle: faithful_exposition\n"
            "episode_format: deep_dive\n"
            "host_dynamic: curious_mind + scholar_companion\n"
            "adaptation_mode: faithful\n"
            "key_tensions:\n"
            "  - The first tension of the tiny book.\n"
        )
        # Chapter txt files (P2.2 asserts ≥1)
        ch_dir = book_dir / "chapters"
        ch_dir.mkdir(parents=True, exist_ok=True)
        # ~2000 words so the post-0d chapter-set check's P4 word band
        # (default_deep_dive: 1800-2800) stays clean, like real 0d output.
        (ch_dir / "ch01-encounter.txt").write_text(
            "# The Encounter\n\n"
            + ("Mocked chapter content produced by Phase 0d. " * 250)
        )
        # Required Phase 0d sidecars
        (text_dir / "chapters-rationale.md").write_text(
            "Single chapter chosen because the tiny-book fixture has 3 sections.\n"
        )
        (book_dir / "_system" / "source-chapter-map.md").write_text(
            "ch01-encounter ← source.md (ch1 + ch2 + ch3, combined)\n"
        )
        # P4 numeric-disambiguation-register.md — P2.2 acceptance line:
        # "numeric-disambiguation-register.md present"
        (text_dir / "numeric-disambiguation-register.md").write_text(
            "| Item | Chapter | Status | Source | Instruction |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| seven stations of the soul | ch01-encounter | NEEDS HUMAN REVIEW | — | "
            "Flag for editorial review; do not invent enumeration. |\n"
            "| seven principles of the path | ch01-encounter | NEEDS HUMAN REVIEW | — | "
            "Flag for editorial review; do not invent enumeration. |\n"
            "| twelve marks of the true seeker | ch01-encounter | NEEDS HUMAN REVIEW | — | "
            "Flag for editorial review; do not invent enumeration. |\n"
        )
        return "phase 0d produced 1 chapter contract + 1 chapter txt + register"

    def _mock_0e(self, book_dir: Path, log=print, **_kw) -> str:
        (book_dir / "_system" / "enrichment-log.md").write_text(
            "- ch01-encounter: ENRICHED at 2026-05-19 12:00:00 (in-place rewrite by mock 0e)\n"
        )
        return "enrichment log produced"

    def _mock_literary(self, book_dir: Path, log=print, **_kw) -> str:
        # The real literary phase (Gemini) rewrites chapters in place; the mock is
        # a no-op — this test only asserts phase ADVANCEMENT through to 0f, not the
        # literary content. (Without this mock the real author_literary_phase runs
        # and fails on the absence of real chapter files in the fixture.)
        return "literary transformation produced by mock"

    def _mock_0f_write_series_plan(self, book_dir: Path, title: str) -> Path:
        plan = book_dir / "_system" / "series-plan.md"
        plan.write_text(
            f"# Series plan — {title}\n\n## Episodes\n- EP01-encounter\n\n"
            "## Halted at Phase 0f for human review.\n"
        )
        return plan

    def _mock_git_commit(self, *args, **kwargs):
        """No-op git commit — the tmpdir isn't a git repo."""
        self._track_log_lines.append(f"phase_git_commit({args!r}, {kwargs!r})")

    def _capture_log(self, msg):
        self._track_log_lines.append(str(msg))

    # ── the actual sunny-day test ────────────────────────────────────────────

    def test_full_pipeline_advances_through_0b_0c_0d_0e_halts_at_0f(self):
        """Drives the full authoring chain; verifies state + artifacts + halt."""
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        tmp_root = Path(self.tmp.name)  # tmpdir is the "repo root" for relative_to() calls
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf), \
             mock.patch.object(initial_driver, "REPO_ROOT", tmp_root), \
             mock.patch.multiple(
                initial_driver,
                author_phase_0b=self._mock_0b,
                author_phase_0c=self._mock_0c,
                author_phase_0d=self._mock_0d,
                author_phase_0e=self._mock_0e), \
             mock.patch.object(initial_driver, "phase_0f_write_series_plan",
                               self._mock_0f_write_series_plan), \
             mock.patch.object(initial_driver, "phase_git_commit",
                               self._mock_git_commit), \
             mock.patch.object(initial_driver, "run_source_review_gate",
                               lambda bd: __import__(
                                   "phases.source_review_gate",
                                   fromlist=["ReviewGate"]
                               ).ReviewGate(approved=True, warnings=[])):
            rc = initial_driver._drive_authoring_through_0f(
                self.book_dir, "Tiny Test Book"
            )

        self.assertEqual(rc, 0, "drive should return 0 (halted-clean at 0f)")

        # ── State assertions ─────────────────────────────────────────────
        state = _progress.read_state(self.book_dir)
        self.assertIsNotNone(state)
        for phase in ("0b", "0c", "0d", "0e"):
            self.assertEqual(
                state["phases"][phase]["status"], "completed",
                f"phase {phase} should be completed after sunny-day drive"
            )
        self.assertEqual(
            state["phases"]["0f"]["status"], "halted",
            "phase 0f should be halted (waiting for human review)"
        )

        # ── Artifact assertions ──────────────────────────────────────────
        text_dir = self.book_dir / "_system" / "source" / "text"

        refined = text_dir / "refined-english.md"
        self.assertTrue(refined.exists(), "refined-english.md missing")
        self.assertGreater(len(refined.read_text().split()), 100,
                           "refined-english.md must be >100 words")

        phonetics = text_dir / "_phonetics.md"
        self.assertTrue(phonetics.exists(), "_phonetics.md missing")
        self.assertGreater(len(phonetics.read_text().split()), 100,
                           "_phonetics.md must be >100 words")

        # _chunks/0b/win-*.in.md ↔ win-*.out.md parity
        chunks_dir = text_dir / "_chunks" / "0b"
        in_files = sorted(chunks_dir.glob("win-*.in.md"))
        out_files = sorted(chunks_dir.glob("win-*.out.md"))
        self.assertGreater(len(in_files), 0, "expected ≥1 win-*.in.md")
        self.assertEqual(
            [p.name.replace(".in.md", "") for p in in_files],
            [p.name.replace(".out.md", "") for p in out_files],
            "every win-*.in.md must have a matching win-*.out.md (P5.2 invariant)"
        )
        for out_path in out_files:
            self.assertGreater(out_path.stat().st_size, 0,
                               f"{out_path.name} must be non-empty (P5.2)")

        # ≥1 chapter contract + ≥1 chapter txt
        contracts = list((self.book_dir / "chapter-contracts").glob("*.yml"))
        self.assertGreater(len(contracts), 0, "expected ≥1 chapter contract")
        chapters = list((self.book_dir / "chapters").glob("*.txt"))
        self.assertGreater(len(chapters), 0, "expected ≥1 chapter txt")

        # P4 numeric-disambiguation-register.md
        register = text_dir / "numeric-disambiguation-register.md"
        self.assertTrue(register.exists(),
                        "numeric-disambiguation-register.md required by P4")
        self.assertGreater(register.stat().st_size, 0)

        # Phase 0f series-plan.md
        plan = self.book_dir / "_system" / "series-plan.md"
        self.assertTrue(plan.exists(), "0f halt should leave series-plan.md")

        # ── P5.2 regression: no silent 'NO ARTIFACT' continuation ────────
        combined_log = stdout_buf.getvalue() + stderr_buf.getvalue() + "\n".join(self._track_log_lines)
        self.assertNotIn(
            "NO ARTIFACT", combined_log,
            "no 'NO ARTIFACT' log line should appear — P5.2 hardening would have raised"
        )

    def test_stop_after_halts_after_named_phase(self):
        """--stop-after 0c halts the moment 0c completes; 0d/0e/0f never run.

        Locks the per-step review cadence: the stopped phase block stays
        'completed' while the top-level phase_status flips to 'halted', so the
        dispatcher re-enters and skips it on the next resume.
        """
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        tmp_root = Path(self.tmp.name)
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf), \
             mock.patch.object(initial_driver, "REPO_ROOT", tmp_root), \
             mock.patch.multiple(
                initial_driver,
                author_phase_0b=self._mock_0b,
                author_phase_0c=self._mock_0c,
                author_phase_0d=self._mock_0d,
                author_phase_0e=self._mock_0e), \
             mock.patch.object(initial_driver, "phase_0f_write_series_plan",
                               self._mock_0f_write_series_plan), \
             mock.patch.object(initial_driver, "phase_git_commit",
                               self._mock_git_commit), \
             mock.patch.object(initial_driver, "run_source_review_gate",
                               lambda bd: __import__(
                                   "phases.source_review_gate",
                                   fromlist=["ReviewGate"]
                               ).ReviewGate(approved=True, warnings=[])):
            rc = initial_driver._drive_authoring_through_0f(
                self.book_dir, "Tiny Test Book", stop_after="0c"
            )

        self.assertEqual(rc, 0, "stop-after halt should return 0 (clean)")
        state = _progress.read_state(self.book_dir)
        self.assertEqual(state["phases"]["0b"]["status"], "completed")
        self.assertEqual(state["phases"]["0c"]["status"], "completed",
                         "stopped phase block stays 'completed' so resume skips it")
        self.assertEqual(state["phase"], "0c")
        self.assertEqual(state["phase_status"], "halted",
                         "top-level status flips to 'halted' after --stop-after")
        # 0d/0e never ran; 0f never reached.
        self.assertEqual(state["phases"].get("0d", {}).get("status", "pending"), "pending")
        self.assertFalse(
            (self.book_dir / "_system" / "series-plan.md").exists(),
            "0f series plan must NOT be written when halted early via --stop-after"
        )


class StateMachineOrderingTests(unittest.TestCase):
    """Tighter assertion: phase update-order is the canonical 0b → 0c → 0d → 0e → 0f.

    Captures every `update_phase` call and verifies the sequence.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "ordering-book"
        (self.book_dir / "_system" / "source" / "text").mkdir(parents=True)
        _progress.write_state(self.book_dir, {
            "schema_version": 1,
            "book_slug": "ordering-book",
            "category": "books",
            "branch": "book/ordering-book",
            "phase": "0b",
            "phase_status": "pending",
            "last_completed_phase": "0a",
            "next_phase": "0b",
            "last_error": None,
            "phases": {p: {"status": "completed" if p in ("pre-flight", "branch", "scaffold", "0a") else "pending"}
                       for p in ("pre-flight", "branch", "scaffold", "0a", "0b", "0c", "0d", "0e", "0f")},
            "config": {"length_tier": "extended", "unit_mode": "auto"},
        })
        # Seed minimal raw-extract so the mocks have an input shape
        (self.book_dir / "_system" / "source" / "text" / "raw-extract.md").write_text(
            "# Tiny\n\nSeed content for ordering test.\n"
        )
        self.phase_transitions: list[tuple[str, str]] = []

    def tearDown(self):
        self.tmp.cleanup()

    def _record_update_phase(self, book_dir: Path, phase: str, status: str, **kwargs):
        """Wrap real update_phase to capture the sequence."""
        self.phase_transitions.append((phase, status))
        return _progress.update_phase.__wrapped__(book_dir, phase=phase, status=status, **kwargs) \
            if hasattr(_progress.update_phase, "__wrapped__") \
            else _progress.update_phase(book_dir, phase=phase, status=status, **kwargs)

    def test_phase_transitions_are_strictly_ordered(self):
        sentinel = mock.MagicMock()
        sentinel.side_effect = self._record_update_phase

        def mock_phase(book_dir, **kwargs):
            return "ok"

        def mock_series_plan(book_dir, title):
            plan = book_dir / "_system" / "series-plan.md"
            plan.write_text("# plan\n")
            return plan

        from phases.source_review_gate import ReviewGate
        approved_gate = ReviewGate(approved=True, warnings=[])

        tmp_root = Path(self.tmp.name)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
             mock.patch.object(initial_driver, "REPO_ROOT", tmp_root), \
             mock.patch.object(initial_driver, "update_phase", side_effect=self._record_update_phase), \
             mock.patch.multiple(
                initial_driver,
                author_phase_0b=mock_phase,
                author_phase_0c=mock_phase,
                author_phase_0ci=mock_phase,
                author_phase_0d=mock_phase,
                author_phase_0e=mock_phase), \
             mock.patch.object(initial_driver, "phase_0f_write_series_plan", mock_series_plan), \
             mock.patch.object(initial_driver, "phase_git_commit", lambda *a, **k: None), \
             mock.patch.object(initial_driver, "_guard_before_phase", lambda *a, **k: None), \
             mock.patch.object(initial_driver, "run_source_review_gate", lambda bd: approved_gate):
            # _guard_before_phase is a no-op here: the stub phases write no
            # artifacts and this test asserts UPDATE ORDERING only. The
            # sunny-day test above keeps the guards live against real files.
            initial_driver._drive_authoring_through_0f(self.book_dir, "Test")

        # Extract the phase identifiers in the order they were updated to "running" or "completed"
        seq = [(p, s) for p, s in self.phase_transitions if s in ("running", "completed", "halted")]

        # Expected: 0b → 0c → 0ci → 0d → 0e → 06a (approved, Wave I gate) → 0f halted
        # (0ci book-intelligence gap analysis inserted after 0c 2026-06-07;
        #  0literary retired from the active flow 2026-06-04 — revoice is PDF path now)
        expected = [
            ("0b", "running"), ("0b", "completed"),
            ("0c", "running"), ("0c", "completed"),
            ("0ci", "running"), ("0ci", "completed"),
            ("0d", "running"), ("0d", "completed"),
            ("0e", "running"), ("0e", "completed"),
            ("06a", "running"), ("06a", "completed"),
            ("0f", "running"), ("0f", "halted"),
        ]
        self.assertEqual(seq, expected)


if __name__ == "__main__":
    unittest.main()
