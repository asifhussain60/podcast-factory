#!/usr/bin/env python3
"""Audio Engine v2 dual-path e2e (Step 8).

Drives `_drive_per_chapter_and_after()` — the post-0f driver — end to end
for BOTH engines against the audio-engine fixture book, with every LLM /
network / git boundary mocked (no spend, no repo mutation):

  NotebookLM path:  per-chapter -> 0g -> (slides off) -> audio phases
                    SKIPPED -> finalize HALT with the manual NotebookLM
                    upload ritual — byte-for-byte the pre-v2 behavior.

  ElevenLabs path:  per-chapter -> 0g -> audio-script (author+gate) ->
                    audio-render HALT at H1 with the exact credit
                    estimate -> --resume approval -> render -> finalize
                    HALT WITHOUT the NotebookLM ritual.

This is the orchestration contract test: state-machine ordering, halt
semantics, engine routing, H1 approval, and the zero-regression guarantee
that the manual path is untouched.
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _progress  # noqa: E402
import _dialogue_convergence as dconv  # noqa: E402
import _dialogue_script as dscript  # noqa: E402
from _convergence import ChapterOutcome  # noqa: E402
from phases import chapter_driver, audio_driver  # noqa: E402

FIXTURE_BOOK = Path(__file__).resolve().parents[1] / "fixtures" / "audio-engine-book"
EPISODE_ID = "EP01-the-lamp-and-the-wick"
CHAPTER_SLUG = "the-lamp-and-the-wick"

SCRIPT = """\
HOST_A: Welcome. We are with the teaching on the lamp and the wick tonight.

HOST_B: Why praise a lamp that eats itself? Light is paid for in the self that carries it.
"""


def _ship_ready_outcome(book_dir, slug, **kw):
    return ChapterOutcome(
        chapter_slug=slug, final_verdict="SHIP-READY",
        outer_iterations=1, fixer_attempts=0,
        p0_remaining=0, p1_remaining=0, p2_remaining=0)


class AudioEnginePathE2E(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "audio-engine-fixture-book"
        shutil.copytree(FIXTURE_BOOK, self.book)
        (self.book / "chapter-contracts").mkdir()
        (self.book / "chapter-contracts" / f"{CHAPTER_SLUG}.yml").write_text(
            "title: The Lamp and the Wick\nepisode_format: deep_dive\n",
            encoding="utf-8")
        # Slides off via the series plan so the e2e exercises the audio seam.
        (self.book / "_system" / "series-plan.md").write_text(
            "# Series plan\n\n**Enable Slide Decks:** false\n", encoding="utf-8")
        # The built episode txt (the per-chapter loop produces this in the real
        # flow; the finalize NotebookLM table discovers episodes from it).
        (self.book / "episodes").mkdir()
        framing = (self.book / "_system" / "episode-drafts" / EPISODE_ID
                   / "00-framing.md").read_text(encoding="utf-8")
        (self.book / "episodes" / f"{EPISODE_ID}.txt").write_text(
            framing, encoding="utf-8")
        _progress.write_state(self.book, _progress.initial_state(
            "audio-engine-fixture-book", "books"))
        _progress.update_phase(self.book, phase="0f", status="halted")

    def _set_engine(self, engine: str):
        cfg = self.book / "_system" / "series-config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + f"audio_engine: {engine}\n",
                       encoding="utf-8")

    def _drive(self, *, approve_audio_render=False,
               converge_side_effect=None, render_side_effect=None):
        """Run the post-0f driver with all spend/git boundaries mocked.

        Returns (rc, stdout_text)."""
        out = io.StringIO()
        patches = [
            mock.patch.object(chapter_driver, "smoke_check_book", return_value=[]),
            mock.patch.object(chapter_driver, "per_chapter_pass",
                              side_effect=_ship_ready_outcome),
            mock.patch.object(chapter_driver, "phase_git_commit"),
            mock.patch.object(chapter_driver, "phase_0g_register"),
            mock.patch.object(chapter_driver, "phase_0g_audit_bundles",
                              return_value={CHAPTER_SLUG: "PASS"}),
            mock.patch.object(chapter_driver, "_run", return_value=(0, "G1-G7 OK", "")),
            mock.patch.object(audio_driver, "phase_git_commit"),
            mock.patch("phases.per_chapter_optimize.run_book_optimize",
                       return_value={"skipped": True, "reason": "test"}),
        ]
        if converge_side_effect is not None:
            patches.append(mock.patch(
                "_dialogue_convergence.converge_dialogue_script",
                side_effect=converge_side_effect))
        if render_side_effect is not None:
            patches.append(mock.patch(
                "render_dialogue_audio.render_episode",
                side_effect=render_side_effect))
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            for p in patches:
                p.start()
                self.addCleanup(p.stop)
            try:
                rc = chapter_driver._drive_per_chapter_and_after(
                    self.book, approve_audio_render=approve_audio_render)
            finally:
                for p in patches:
                    p.stop()
                # addCleanup will call stop again; make it harmless.
                patches.clear()
        return rc, out.getvalue()

    def _phase(self, phase):
        return (_progress.read_state(self.book) or {})["phases"][phase]

    # ── NotebookLM path: byte-identical manual ritual ─────────────────────────

    def test_notebooklm_path_skips_audio_and_keeps_manual_ritual(self):
        # Default engine — no audio_engine field at all.
        rc, stdout = self._drive()
        self.assertEqual(rc, 0)
        self.assertEqual(self._phase("per-chapter")["status"], "completed")
        self.assertEqual(self._phase("0g")["status"], "completed")
        self.assertEqual(self._phase("audio-script")["status"], "skipped")
        self.assertEqual(self._phase("audio-render")["status"], "skipped")
        self.assertEqual(self._phase("finalize")["status"], "halted")
        # The manual NotebookLM ritual is present, verbatim anchors:
        self.assertIn("NOTEBOOKLM UPLOAD TABLE", stdout)
        self.assertIn("normalize_m4a.py", stdout)
        self.assertIn("transcribe_notebooklm.py", stdout)

    # ── ElevenLabs path: autonomous with ONE H1 halt ──────────────────────────

    def test_elevenlabs_path_halts_at_h1_then_renders_to_finalize(self):
        self._set_engine("elevenlabs")

        def fake_converge(book_dir, slug, **kw):
            sp = dscript.script_path_for(book_dir, EPISODE_ID)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(SCRIPT, encoding="utf-8")
            vp = dconv.verdict_path(book_dir, EPISODE_ID)
            vp.parent.mkdir(parents=True, exist_ok=True)
            vp.write_text("SHIP-READY\n", encoding="utf-8")
            return dconv.DialogueConvergenceResult(
                chapter_slug=slug, episode_id=EPISODE_ID,
                verdict="SHIP-READY", credit_estimate=200)

        # Pass 1: drives through per-chapter + 0g + audio-script, halts at H1.
        rc, stdout = self._drive(converge_side_effect=fake_converge)
        self.assertEqual(rc, 0)
        self.assertEqual(self._phase("audio-script")["status"], "completed")
        self.assertEqual(self._phase("audio-render")["status"], "halted")
        self.assertGreater(self._phase("audio-render")["credit_estimate"], 0)
        # The H1 halt is the MANDATORY pre-audio review gate: it stops before any
        # spend, points at the Astro reader, and still shows the exact estimate.
        self.assertIn("MANDATORY review", stdout)
        self.assertIn("/arabic-review", stdout)
        self.assertIn("EXACT credit estimate", stdout)
        # Finalize NOT reached yet.
        self.assertEqual(self._phase("finalize")["status"], "pending")

        # Pass 2: H1 approved (--resume) — render runs, finalize halts.
        def fake_render(book_dir, ep, **kw):
            from render_dialogue_audio import RenderResult
            stem = "ch01-the-lamp-and-the-wick"
            (book_dir / "m4a").mkdir(exist_ok=True)
            (book_dir / "m4a" / f"{stem}.m4a").write_bytes(b"AUDIO")
            tx = book_dir / "m4a" / "transcripts" / f"{stem}.transcript.txt"
            tx.parent.mkdir(parents=True, exist_ok=True)
            tx.write_text("HOST_A: Welcome.\n", encoding="utf-8")
            return RenderResult(episode_id=ep, ch_stem=stem,
                                verdict="SHIP-READY", rendered=True,
                                credits_metered=187)

        rc2, stdout2 = self._drive(approve_audio_render=True,
                                   converge_side_effect=fake_converge,
                                   render_side_effect=fake_render)
        self.assertEqual(rc2, 0)
        self.assertEqual(self._phase("audio-render")["status"], "completed")
        self.assertEqual(self._phase("audio-render")["credits_metered"], 187)
        self.assertEqual(self._phase("finalize")["status"], "halted")
        # Engine-aware halt card: NO NotebookLM ritual on the autonomous path.
        self.assertNotIn("NOTEBOOKLM UPLOAD TABLE", stdout2)
        self.assertNotIn("normalize_m4a.py", stdout2)
        self.assertIn("ALREADY rendered", stdout2)
        # Canonical audio artifact present.
        self.assertTrue((self.book / "m4a" / "ch01-the-lamp-and-the-wick.m4a").exists())

    def test_elevenlabs_script_failure_halts_before_any_render(self):
        self._set_engine("elevenlabs")

        def failing_converge(book_dir, slug, **kw):
            return dconv.DialogueConvergenceResult(
                chapter_slug=slug, episode_id=EPISODE_ID, verdict="FAILED")

        render_spy = mock.Mock()
        rc, _ = self._drive(converge_side_effect=failing_converge,
                            render_side_effect=render_spy)
        self.assertEqual(rc, 2)
        self.assertEqual(self._phase("audio-script")["status"], "failed")
        render_spy.assert_not_called()  # nothing renders before a passing verdict
        self.assertEqual(self._phase("finalize")["status"], "pending")

    # ── Per-episode override: ElevenLabs book, one episode flipped to NotebookLM ─

    def test_episode_override_skips_render_and_emits_notebooklm_table(self):
        self._set_engine("elevenlabs")
        cfg = self.book / "_system" / "series-config.yaml"
        cfg.write_text(
            cfg.read_text(encoding="utf-8")
            + f"episode_engine_overrides:\n  {EPISODE_ID}: notebooklm\n",
            encoding="utf-8")

        render_spy = mock.Mock()
        rc, stdout = self._drive(render_side_effect=render_spy)
        self.assertEqual(rc, 0)
        # The only episode is overridden -> authored script skipped, nothing renders.
        render_spy.assert_not_called()
        self.assertEqual(self._phase("audio-script")["status"], "completed")
        self.assertEqual(self._phase("finalize")["status"], "halted")
        # Mixed-routing finalize: the NotebookLM ritual IS printed for the
        # overridden episode (and the transcribe step follows it).
        self.assertIn("NOTEBOOKLM UPLOAD TABLE", stdout)
        self.assertIn("transcribe_notebooklm.py", stdout)


if __name__ == "__main__":
    unittest.main()
