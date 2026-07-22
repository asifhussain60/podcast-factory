"""Tests for deterministic Quran recitation + render-layer Arabic injection.

Covers _quran_recitation.py (citation -> verbatim KQur Arabic) and the
pronunciation_compiler render-layer integration. Verse-Arabic assertions that
need the wisdom-corpus mirror are guarded by skipUnless so the suite stays
portable on machines without content/knowledge-base/mirror.db.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _quran_recitation as qr
import pronunciation_compiler as pc
from _dialogue_script import Turn

MIRROR = SCRIPTS_PODCAST.parents[1] / "content" / "knowledge-base" / "mirror.db"
HAS_MIRROR = MIRROR.exists() and bool(qr.verse_record(14, 7))


class TestSurahResolution(unittest.TestCase):
    def test_canonical_names(self):
        self.assertEqual(qr.surah_number("Abraham"), 14)
        self.assertEqual(qr.surah_number("Joseph"), 12)
        self.assertEqual(qr.surah_number("The Cow"), 2)
        self.assertEqual(qr.surah_number("Al-Fatihah"), 1)
        self.assertEqual(qr.surah_number("Ya-Sin"), 36)

    def test_prefix_stripping(self):
        self.assertEqual(qr.surah_number("the chapter of Joseph"), 12)
        self.assertEqual(qr.surah_number("surah Al-Baqarah"), 2)

    def test_unknown_name_is_none(self):
        self.assertIsNone(qr.surah_number("nonsense surah"))
        self.assertIsNone(qr.surah_number("Genesis"))


class TestNumberParser(unittest.TestCase):
    def test_words_and_digits(self):
        self.assertEqual(qr.parse_number("seven"), 7)
        self.assertEqual(qr.parse_number("twenty-seven"), 27)
        self.assertEqual(qr.parse_number("one hundred"), 100)
        self.assertEqual(qr.parse_number("255"), 255)
        self.assertEqual(qr.parse_number("4"), 4)

    def test_garbage_is_none(self):
        self.assertIsNone(qr.parse_number("garbage"))
        self.assertIsNone(qr.parse_number(""))


class TestCitationFinding(unittest.TestCase):
    def test_numeric(self):
        c = qr.find_citations("as in (chapter 14, verse 7).")
        self.assertEqual([(x.surah, x.ayat) for x in c], [(14, 7)])

    def test_prose_forward(self):
        c = qr.find_citations("the chapter of Abraham, verse seven teaches gratitude")
        self.assertEqual([(x.surah, x.ayat) for x in c], [(14, 7)])

    def test_prose_reverse(self):
        c = qr.find_citations("verse four of the chapter on Joseph, in Arberry")
        self.assertEqual([(x.surah, x.ayat) for x in c], [(12, 4)])

    def test_no_citation(self):
        self.assertEqual(qr.find_citations("a normal sentence with no citation"), [])

    def test_no_overlap_double_count(self):
        # one citation, not double-matched by two patterns
        c = qr.find_citations("chapter 14, verse 7")
        self.assertEqual(len(c), 1)


class TestProperNameSkip(unittest.TestCase):
    def test_person_name_detected(self):
        self.assertTrue(pc._is_proper_name("Jafar ibn Mansur al-Yaman"))
        self.assertTrue(pc._is_proper_name("Abu Bakr"))

    def test_doctrinal_term_not_a_name(self):
        self.assertFalse(pc._is_proper_name("Tawhid"))
        self.assertFalse(pc._is_proper_name("Sayyidina"))


@unittest.skipUnless(HAS_MIRROR, "wisdom-corpus mirror.db not present")
class TestVerifiedArabic(unittest.TestCase):
    def test_known_verse_arabic(self):
        rec = qr.verse_record(14, 7)
        self.assertIn("arabic", rec)
        self.assertTrue(rec["arabic"].strip())

    def test_inject_adds_arabic_after_citation(self):
        out = qr.inject_recitations("he cites the chapter of Abraham, verse seven here")
        self.assertIn("«", out)
        self.assertNotEqual(out, "he cites the chapter of Abraham, verse seven here")

    def test_nonexistent_verse_skipped(self):
        out = qr.inject_recitations("see chapter 14, verse 999 there")
        self.assertNotIn("«", out)


class TestCompileLayer(unittest.TestCase):
    def _book(self, cfg: str, glossary: str | None = None) -> Path:
        tmp = tempfile.mkdtemp()
        bk = Path(tmp) / "bk"
        (bk / "_system").mkdir(parents=True)
        (bk / "_system" / "series-config.yaml").write_text(cfg, encoding="utf-8")
        if glossary is not None:
            (bk / "_system" / "glossary.yml").write_text(glossary, encoding="utf-8")
        return bk

    def test_flag_off_is_identity(self):
        bk = self._book("audio_engine: elevenlabs\n")
        turns = [Turn("HOST_A", "the chapter of Abraham, verse seven, invoking Tawhid")]
        out = pc.compile_turns_for_render(bk, turns)
        self.assertEqual(out[0].text, turns[0].text)

    def test_flag_on_substitutes_term_skips_name(self):
        gloss = (
            "schema_version: 1\nentries:\n"
            "  - phonetic: Tawhid\n    arabic_script: توحيد\n"
            "  - phonetic: Jafar ibn Mansur\n    arabic_script: جعفر\n"
        )
        bk = self._book("audio_engine: elevenlabs\nelevenlabs_arabic_recitation: true\n", gloss)
        turns = [Turn("HOST_A", "Tawhid is taught by Jafar ibn Mansur here")]
        out = pc.compile_turns_for_render(bk, turns)
        self.assertIn("توحيد", out[0].text)  # term recited
        self.assertIn("Jafar ibn Mansur", out[0].text)  # name left ASCII

    @unittest.skipUnless(HAS_MIRROR, "mirror.db not present")
    def test_flag_on_injects_verse(self):
        bk = self._book(
            "audio_engine: elevenlabs\nelevenlabs_arabic_recitation: true\n", "schema_version: 1\nentries: []\n"
        )
        turns = [Turn("HOST_A", "he recites the chapter of Abraham, verse seven on gratitude")]
        out = pc.compile_turns_for_render(bk, turns)
        self.assertIn("«", out[0].text)


class TestIntakeRecitationStamp(unittest.TestCase):
    def test_islamic_book_defaults_to_notebooklm_without_recitation_flag(self):
        # Locked 2026-06-13: islamic_scholarly defaults to NotebookLM, not ElevenLabs.
        # The ElevenLabs Arabic-recitation flag is therefore NOT stamped unless the
        # operator explicitly selects the (quarantined) ElevenLabs engine.
        import yaml
        from intake_launch import _write_series_config

        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(d, "bk", "T", {"content_profile": "islamic_scholarly"}, None)
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertEqual(cfg.get("audio_engine"), "notebooklm")
            self.assertNotIn("elevenlabs_arabic_recitation", cfg)

    def test_explicit_elevenlabs_islamic_book_gets_recitation_flag(self):
        # When ElevenLabs is explicitly chosen, the engine still works end-to-end
        # (it is quarantined/dormant, not deleted) — the recitation flag is stamped.
        import yaml
        from intake_launch import _write_series_config

        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(
                d, "bk", "T", {"content_profile": "islamic_scholarly", "audio_engine": "elevenlabs"}, None
            )
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertEqual(cfg.get("audio_engine"), "elevenlabs")
            self.assertTrue(cfg.get("elevenlabs_arabic_recitation"))

    def test_fiction_book_no_recitation_flag(self):
        import yaml
        from intake_launch import _write_series_config

        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "bk"
            (d / "_system").mkdir(parents=True)
            _write_series_config(d, "bk", "T", {"content_profile": "fiction"}, None)
            cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text())
            self.assertNotIn("elevenlabs_arabic_recitation", cfg)


if __name__ == "__main__":
    unittest.main()
