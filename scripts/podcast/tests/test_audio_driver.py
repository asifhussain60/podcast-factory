"""Tests for phases/audio_driver.py (Step 6) — engine routing, the H1 spend

halt, idempotent re-entry, and render approval. All LLM/network/git mocked."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _progress  # noqa: E402
import _dialogue_convergence as dc  # noqa: E402
import _dialogue_script as ds  # noqa: E402
from phases import audio_driver  # noqa: E402

FIXTURE_BOOK = Path(__file__).resolve().parent / "fixtures" / "audio-engine-book"
EPISODE_ID = "EP01-the-lamp-and-the-wick"
CHAPTER_SLUG = "the-lamp-and-the-wick"

SCRIPT = """\
HOST_A: Welcome. We are with the teaching on the lamp and the wick tonight.

HOST_B: Why praise a lamp that eats itself? Light is paid for in the self that carries it.
"""


class AudioDriverTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "book"
        shutil.copytree(FIXTURE_BOOK, self.book)
        (self.book / "chapter-contracts").mkdir()
        (self.book / "chapter-contracts" / f"{CHAPTER_SLUG}.yml").write_text(
            "title: The Lamp and the Wick\n", encoding="utf-8")
        _progress.write_state(self.book, _progress.initial_state(
            "audio-engine-fixture-book", "books"))
        # git commits are repo-relative — neutralize for tmp books.
        self._git_patch = mock.patch.object(audio_driver, "phase_git_commit")
        self._git_patch.start()
        self.addCleanup(self._git_patch.stop)

    def _set_engine(self, engine: str):
        cfg = self.book / "_system" / "series-config.yaml"
        body = cfg.read_text(encoding="utf-8")
        body = "\n".join(l for l in body.splitlines()
                         if not l.startswith("audio_engine:"))
        cfg.write_text(body + f"\naudio_engine: {engine}\n", encoding="utf-8")

    def _write_gated_script(self, verdict="SHIP-READY"):
        p = ds.script_path_for(self.book, EPISODE_ID)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(SCRIPT, encoding="utf-8")
        vp = dc.verdict_path(self.book, EPISODE_ID)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(verdict + "\n", encoding="utf-8")

    def _phase_status(self, phase):
        return (_progress.read_state(self.book) or {})["phases"][phase]["status"]


class TestManualEngineSkips(AudioDriverTestCase):
    def test_notebooklm_book_skips_both_phases(self):
        self._set_engine("notebooklm")
        outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("skipped", 0))
        self.assertEqual(self._phase_status("audio-script"), "skipped")
        self.assertEqual(self._phase_status("audio-render"), "skipped")

    def test_default_engine_book_skips(self):
        # No audio_engine field at all — the pre-existing-book case.
        outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("skipped", 0))


class TestAutonomousFlow(AudioDriverTestCase):
    def setUp(self):
        super().setUp()
        self._set_engine("elevenlabs")

    def test_script_phase_runs_then_h1_halt(self):
        def fake_converge(book_dir, slug, **kw):
            self._write_gated_script()
            return dc.DialogueConvergenceResult(
                chapter_slug=slug, episode_id=EPISODE_ID,
                verdict="SHIP-READY", credit_estimate=1234)

        with mock.patch.object(audio_driver, "_drive_audio_script",
                               wraps=audio_driver._drive_audio_script), \
             mock.patch("_dialogue_convergence.converge_dialogue_script",
                        side_effect=fake_converge):
            outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("halted", 0))
        self.assertEqual(self._phase_status("audio-script"), "completed")
        self.assertEqual(self._phase_status("audio-render"), "halted")
        extras = (_progress.read_state(self.book))["phases"]["audio-render"]
        self.assertGreater(extras["credit_estimate"], 0)
        self.assertEqual(extras["episodes_pending"], [EPISODE_ID])

    def test_already_converged_script_skips_authorship(self):
        self._write_gated_script()
        with mock.patch("_dialogue_convergence.converge_dialogue_script") as cv:
            outcome, _ = audio_driver.drive_audio_phases(self.book)
        cv.assert_not_called()
        self.assertEqual(outcome, "halted")

    def test_failed_convergence_fails_phase(self):
        def fake_converge(book_dir, slug, **kw):
            return dc.DialogueConvergenceResult(
                chapter_slug=slug, episode_id=EPISODE_ID, verdict="FAILED")

        with mock.patch("_dialogue_convergence.converge_dialogue_script",
                        side_effect=fake_converge):
            outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("failed", 2))
        self.assertEqual(self._phase_status("audio-script"), "failed")

    def test_approved_resume_renders_and_completes(self):
        self._write_gated_script()

        def fake_render(book_dir, ep, **kw):
            stem = "ch01-the-lamp-and-the-wick"
            (book_dir / "m4a").mkdir(exist_ok=True)
            (book_dir / "m4a" / f"{stem}.m4a").write_bytes(b"AUDIO")
            from render_dialogue_audio import RenderResult
            return RenderResult(episode_id=ep, ch_stem=stem,
                                verdict="SHIP-READY", rendered=True,
                                credits_metered=2200)

        with mock.patch("render_dialogue_audio.render_episode",
                        side_effect=fake_render):
            outcome, rc = audio_driver.drive_audio_phases(
                self.book, approve_render=True)
        self.assertEqual((outcome, rc), ("done", 0))
        self.assertEqual(self._phase_status("audio-render"), "completed")
        extras = (_progress.read_state(self.book))["phases"]["audio-render"]
        self.assertEqual(extras["credits_metered"], 2200)

    def test_rendered_episode_drops_out_of_plan(self):
        self._write_gated_script()
        (self.book / "m4a").mkdir(exist_ok=True)
        (self.book / "m4a" / "ch01-the-lamp-and-the-wick.m4a").write_bytes(b"A")
        outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("done", 0))
        self.assertEqual(self._phase_status("audio-render"), "completed")

    def test_render_failure_fails_phase(self):
        self._write_gated_script()
        with mock.patch("render_dialogue_audio.render_episode",
                        side_effect=RuntimeError("boom")):
            outcome, rc = audio_driver.drive_audio_phases(
                self.book, approve_render=True)
        self.assertEqual((outcome, rc), ("failed", 2))
        self.assertEqual(self._phase_status("audio-render"), "failed")

    def test_reentry_after_completion_is_idempotent(self):
        self._write_gated_script()
        (self.book / "m4a").mkdir(exist_ok=True)
        (self.book / "m4a" / "ch01-the-lamp-and-the-wick.m4a").write_bytes(b"A")
        audio_driver.drive_audio_phases(self.book)
        outcome, rc = audio_driver.drive_audio_phases(self.book)
        self.assertEqual((outcome, rc), ("done", 0))


class TestPhaseRegistry(unittest.TestCase):
    def test_audio_phases_between_slides_and_finalize(self):
        order = list(_progress.PHASES)
        self.assertLess(order.index("per-chapter-slides"), order.index("audio-script"))
        self.assertLess(order.index("audio-script"), order.index("audio-render"))
        self.assertLess(order.index("audio-render"), order.index("finalize"))


if __name__ == "__main__":
    unittest.main()
