"""Tests for _audio_engines.py — the pluggable audio-engine registry (Step 1).

Covers:
  - registry shape + capability flags for both engines
  - config resolution (absent file / absent field / explicit / unknown)
  - credit estimation determinism
  - voice casting defaults + per-book override
  - GOLDEN-FIXTURE BYTE-IDENTITY: a book with no `audio_engine` field (and one
    with the explicit default) builds its NotebookLM episode txt byte-identical
    to the committed golden file — proving the registry's existence changes
    nothing on the default path.
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

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _audio_engines as ae  # noqa: E402

FIXTURE_BOOK = Path(__file__).resolve().parent / "fixtures" / "audio-engine-book"
EPISODE_ID = "EP01-the-lamp-and-the-wick"
GOLDEN = FIXTURE_BOOK / "golden" / f"{EPISODE_ID}.txt"


class TestRegistry(unittest.TestCase):
    def test_registry_has_both_engines(self):
        self.assertIn(ae.ENGINE_NOTEBOOKLM, ae.AUDIO_ENGINE_REGISTRY)
        self.assertIn(ae.ENGINE_ELEVENLABS, ae.AUDIO_ENGINE_REGISTRY)

    def test_default_is_notebooklm(self):
        self.assertEqual(ae.DEFAULT_AUDIO_ENGINE, ae.ENGINE_NOTEBOOKLM)

    def test_notebooklm_capabilities(self):
        card = ae.get_engine(ae.ENGINE_NOTEBOOKLM)
        self.assertEqual(card.render_mode, ae.RENDER_MODE_MANUAL)
        self.assertFalse(card.supports_arabic_script)
        self.assertFalse(card.supports_audio_tags)
        self.assertEqual(card.credit_rate, 0.0)
        self.assertFalse(ae.is_autonomous(card))

    def test_elevenlabs_capabilities(self):
        card = ae.get_engine(ae.ENGINE_ELEVENLABS)
        self.assertEqual(card.render_mode, ae.RENDER_MODE_API)
        self.assertTrue(card.supports_arabic_script)
        self.assertTrue(card.supports_audio_tags)
        self.assertEqual(card.model_id, "eleven_v3")
        # Documented reliability limit — the experiment's 2,500 was lowered.
        self.assertLessEqual(card.max_chunk_chars, 2000)
        self.assertGreater(card.credit_rate, 0.0)
        self.assertTrue(ae.is_autonomous(card))
        # R-HOST-ROLE-PARITY voice casting present for both hosts.
        self.assertIn("host_a", card.default_voices)
        self.assertIn("host_b", card.default_voices)

    def test_unknown_engine_raises(self):
        with self.assertRaises(ValueError):
            ae.get_engine("polly")

    def test_every_engine_declares_required_capabilities(self):
        for name, card in ae.AUDIO_ENGINE_REGISTRY.items():
            self.assertEqual(card.name, name)
            self.assertIn(card.render_mode, (ae.RENDER_MODE_MANUAL, ae.RENDER_MODE_API))
            self.assertIsInstance(card.supports_arabic_script, bool)
            self.assertIsInstance(card.supports_audio_tags, bool)
            self.assertIsInstance(card.max_chunk_chars, int)
            self.assertIsInstance(card.credit_rate, float)


class TestResolution(unittest.TestCase):
    def _book(self, config_text: str | None) -> Path:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        book = Path(tmp) / "book"
        (book / "_system").mkdir(parents=True)
        if config_text is not None:
            (book / "_system" / "series-config.yaml").write_text(
                config_text, encoding="utf-8")
        return book

    def test_missing_config_file_defaults(self):
        book = self._book(None)
        self.assertEqual(ae.resolve_audio_engine(book), ae.ENGINE_NOTEBOOKLM)

    def test_missing_field_defaults(self):
        book = self._book("slug: x\ntitle: X\n")
        self.assertEqual(ae.resolve_audio_engine(book), ae.ENGINE_NOTEBOOKLM)

    def test_explicit_notebooklm(self):
        book = self._book("audio_engine: notebooklm\n")
        self.assertEqual(ae.resolve_audio_engine(book), ae.ENGINE_NOTEBOOKLM)

    def test_explicit_elevenlabs(self):
        book = self._book("audio_engine: elevenlabs\n")
        self.assertEqual(ae.resolve_audio_engine(book), ae.ENGINE_ELEVENLABS)
        self.assertTrue(ae.is_autonomous(ae.audio_engine_for_book(book)))

    def test_unknown_value_raises_loudly(self):
        book = self._book("audio_engine: pollly\n")
        with self.assertRaises(ValueError):
            ae.resolve_audio_engine(book)

    def test_voices_default_and_override(self):
        # voice library (2026-06-12): with no override, the deterministic
        # per-slug pair from the approved pools supersedes card defaults.
        from _voice_library import pair_for_slug
        book = self._book("audio_engine: elevenlabs\n")
        voices = ae.voices_for_book(book)
        self.assertEqual(voices, pair_for_slug(book.name))
        book2 = self._book(
            "audio_engine: elevenlabs\n"
            "elevenlabs_voices:\n  host_a: AAA111\n")
        voices2 = ae.voices_for_book(book2)
        self.assertEqual(voices2["host_a"], "AAA111")
        self.assertEqual(voices2["host_b"], pair_for_slug(book2.name)["host_b"])

    def test_notebooklm_book_has_no_voice_casting(self):
        book = self._book("audio_engine: notebooklm\n")
        self.assertEqual(ae.voices_for_book(book), {})


class TestCreditEstimate(unittest.TestCase):
    def test_notebooklm_is_unmetered(self):
        self.assertEqual(ae.credit_estimate(ae.ENGINE_NOTEBOOKLM, 50_000), 0)

    def test_elevenlabs_one_credit_per_char_rounded_up(self):
        self.assertEqual(ae.credit_estimate(ae.ENGINE_ELEVENLABS, 12_345), 12_345)
        self.assertEqual(ae.credit_estimate(ae.ENGINE_ELEVENLABS, 0), 0)

    def test_estimate_is_deterministic(self):
        a = ae.credit_estimate(ae.ENGINE_ELEVENLABS, 7_777)
        b = ae.credit_estimate(ae.ENGINE_ELEVENLABS, 7_777)
        self.assertEqual(a, b)

    def test_credits_to_usd(self):
        self.assertAlmostEqual(
            ae.credits_to_usd(100_000), 22.0, places=2)


class TestGoldenFixtureByteIdentity(unittest.TestCase):
    """The NotebookLM default path is byte-identical with the registry present.

    Builds the fixture book's episode txt (a) with NO audio_engine field and
    (b) with the explicit default, and compares both against the committed
    golden file byte-for-byte.
    """

    def _build(self, config_append: str = "") -> bytes:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        book = Path(tmp) / "audio-engine-book"
        shutil.copytree(FIXTURE_BOOK, book)
        if config_append:
            cfg = book / "_system" / "series-config.yaml"
            cfg.write_text(cfg.read_text(encoding="utf-8") + config_append,
                           encoding="utf-8")
        import build_episode_txt
        # Section-depth minting touches the shared DB — keep tests hermetic.
        fake_mint = mock.Mock()
        fake_mint.mint_section_depths_for_chapter = mock.Mock()
        with mock.patch.dict(sys.modules, {"mint_section_depths": fake_mint}):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                build_episode_txt.build(book, EPISODE_ID)
        return (book / "episodes" / f"{EPISODE_ID}.txt").read_bytes()

    def test_no_field_matches_golden(self):
        self.assertEqual(self._build(), GOLDEN.read_bytes())

    def test_explicit_default_matches_golden(self):
        self.assertEqual(
            self._build("audio_engine: notebooklm\n"), GOLDEN.read_bytes())


if __name__ == "__main__":
    unittest.main()
