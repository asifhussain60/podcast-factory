"""Tests for _dialogue_script.py (format/chunker/seeds) and _authoring/_dialogue.py

(script authorship with a mocked `claude -p`). Steps 2 + 5 pure parts.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _dialogue_script as ds  # noqa: E402

FIXTURE_BOOK = Path(__file__).resolve().parent / "fixtures" / "audio-engine-book"

SAMPLE = """\
# EP01-test — dialogue script
# engine: elevenlabs

HOST_A: [warm] Welcome. We're with the teaching on the lamp and the wick.

HOST_B: And the question the chapter opens with: why praise a lamp that eats itself?

HOST_A: Light is paid for. Every hour of clarity costs an hour of the self
  that produced it.
"""


class TestParse(unittest.TestCase):
    def test_parse_basic(self):
        turns = ds.parse_dialogue_script(SAMPLE)
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[0].speaker, "HOST_A")
        self.assertTrue(turns[0].text.startswith("[warm] Welcome."))
        self.assertEqual(turns[1].speaker, "HOST_B")

    def test_continuation_lines_join(self):
        turns = ds.parse_dialogue_script(SAMPLE)
        self.assertIn("an hour of the self that produced it.", turns[2].text)

    def test_comments_and_blanks_ignored(self):
        turns = ds.parse_dialogue_script("# c\n\nHOST_A: hello there friend.\n# x\n")
        self.assertEqual(len(turns), 1)

    def test_no_turns_raises(self):
        with self.assertRaises(ds.DialogueScriptError):
            ds.parse_dialogue_script("# only a comment\n")

    def test_orphan_continuation_raises(self):
        with self.assertRaises(ds.DialogueScriptError):
            ds.parse_dialogue_script("stray text\nHOST_A: hi.\n")

    def test_round_trip(self):
        turns = ds.parse_dialogue_script(SAMPLE)
        text = ds.serialize_dialogue_script(turns, "EP01-test", "elevenlabs")
        self.assertEqual(ds.parse_dialogue_script(text), turns)

    def test_char_and_tag_counts(self):
        turns = ds.parse_dialogue_script(SAMPLE)
        self.assertEqual(ds.script_char_count(turns),
                         sum(len(t.text) for t in turns))
        self.assertEqual(ds.audio_tag_count(turns), 1)


class TestSoftBands(unittest.TestCase):
    def test_known_tiers(self):
        for tier in ("brief", "default_deep_dive", "longer", "extended"):
            lo, hi = ds.soft_char_band(tier)
            self.assertLess(lo, hi)

    def test_unknown_tier_falls_back_to_default(self):
        self.assertEqual(ds.soft_char_band("bogus"),
                         ds.SOFT_CHAR_BANDS["default_deep_dive"])
        self.assertEqual(ds.soft_char_band(None),
                         ds.SOFT_CHAR_BANDS["default_deep_dive"])


class TestChunker(unittest.TestCase):
    def _turns(self, sizes: list[int], speaker: str = "HOST_A") -> list[ds.Turn]:
        out = []
        for i, n in enumerate(sizes):
            spk = "HOST_A" if i % 2 == 0 else "HOST_B"
            words = ("w" * 7 + " ") * (n // 8)
            out.append(ds.Turn(speaker=spk, text=words.strip()[:n].ljust(n, "x")))
        return out

    def test_chunks_respect_max_chars(self):
        turns = self._turns([800, 900, 700, 600, 1200])
        chunks = ds.chunk_turns(turns, 2000)
        for c in chunks:
            self.assertLessEqual(sum(len(t.text) for t in c), 2000)

    def test_boundaries_at_turn_boundaries(self):
        turns = self._turns([800, 900, 700])
        chunks = ds.chunk_turns(turns, 2000)
        flat = [t for c in chunks for t in c]
        self.assertEqual(flat, turns)  # nothing reordered, nothing split

    def test_deterministic(self):
        turns = self._turns([500, 1500, 900, 300, 1999, 42])
        a = ds.chunk_turns(turns, 2000)
        b = ds.chunk_turns(turns, 2000)
        self.assertEqual(a, b)

    def test_long_turn_split_at_sentences_same_speaker(self):
        sentence = "This is a sentence that carries some weight. "
        long_text = (sentence * 80).strip()  # ~3,600 chars
        turns = [ds.Turn(speaker="HOST_B", text=long_text)]
        chunks = ds.chunk_turns(turns, 2000)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            for t in c:
                self.assertEqual(t.speaker, "HOST_B")
                self.assertLessEqual(len(t.text), 2000)
        rejoined = " ".join(t.text for c in chunks for t in c)
        self.assertEqual(rejoined, long_text)

    def test_degenerate_single_giant_sentence(self):
        turns = [ds.Turn(speaker="HOST_A", text="word " * 1000)]  # no sentence breaks
        chunks = ds.chunk_turns(turns, 500)
        for c in chunks:
            for t in c:
                self.assertLessEqual(len(t.text), 500)

    def test_zero_max_chars_raises(self):
        with self.assertRaises(ValueError):
            ds.chunk_turns([ds.Turn("HOST_A", "hi.")], 0)


class TestHashesAndSeeds(unittest.TestCase):
    def test_hash_stable_and_sensitive(self):
        chunk = [ds.Turn("HOST_A", "alpha."), ds.Turn("HOST_B", "beta.")]
        h1 = ds.chunk_content_hash(chunk, model_id="eleven_v3",
                                   voices={"host_a": "X", "host_b": "Y"},
                                   dictionary_version="v1")
        h2 = ds.chunk_content_hash(chunk, model_id="eleven_v3",
                                   voices={"host_b": "Y", "host_a": "X"},
                                   dictionary_version="v1")
        self.assertEqual(h1, h2)  # voice-map order does not matter
        h3 = ds.chunk_content_hash(chunk, model_id="eleven_v3",
                                   voices={"host_a": "X", "host_b": "Y"},
                                   dictionary_version="v2")
        self.assertNotEqual(h1, h3)  # dictionary version is pinned into the hash
        h4 = ds.chunk_content_hash([ds.Turn("HOST_B", "alpha."),
                                    ds.Turn("HOST_A", "beta.")],
                                   model_id="eleven_v3",
                                   voices={"host_a": "X", "host_b": "Y"},
                                   dictionary_version="v1")
        self.assertNotEqual(h1, h4)  # speaker assignment matters

    def test_seed_in_elevenlabs_range(self):
        chunk = [ds.Turn("HOST_A", "alpha.")]
        h = ds.chunk_content_hash(chunk)
        seed = ds.chunk_seed(h)
        self.assertGreaterEqual(seed, 0)
        self.assertLessEqual(seed, 4294967295)
        self.assertEqual(seed, ds.chunk_seed(h))  # derived, not random


class TestAuthorDialogueScript(unittest.TestCase):
    """author_dialogue_script with `claude -p` mocked — no LLM spend."""

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "book"
        shutil.copytree(FIXTURE_BOOK, self.book)
        # The fixture has no contract — add a minimal one + elevenlabs engine.
        (self.book / "chapter-contracts").mkdir()
        (self.book / "chapter-contracts" / "the-lamp-and-the-wick.yml").write_text(
            "title: The Lamp and the Wick\n"
            "episode_format: deep_dive\n"
            "key_tensions:\n"
            "  - light is paid for in the self that carries it\n",
            encoding="utf-8")
        cfg = self.book / "_system" / "series-config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + "audio_engine: elevenlabs\n",
                       encoding="utf-8")

    def _author(self, fake_script: str | None):
        import _authoring._dialogue as dlg

        def fake_run(prompt, *, timeout, book_dir, phase, step, **kw):
            if fake_script is not None:
                p = ds.script_path_for(self.book, "EP01-the-lamp-and-the-wick")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(fake_script, encoding="utf-8")
            return 0, "ok", ""

        with mock.patch.object(dlg, "_run_claude_p_with_retry", side_effect=fake_run):
            return dlg.author_dialogue_script(self.book, "the-lamp-and-the-wick")

    def test_authors_and_parses(self):
        self._author(SAMPLE)
        p = ds.script_path_for(self.book, "EP01-the-lamp-and-the-wick")
        self.assertTrue(p.exists())
        self.assertEqual(len(ds.parse_dialogue_script(p.read_text())), 3)

    def test_missing_artifact_raises(self):
        from _authoring._core import AuthoringError
        with self.assertRaises(AuthoringError):
            self._author(None)

    def test_unparseable_artifact_raises(self):
        from _authoring._core import AuthoringError
        with self.assertRaises(AuthoringError):
            self._author("just prose with no speaker turns\n")

    def test_missing_framing_raises(self):
        from _authoring._core import AuthoringError
        shutil.rmtree(self.book / "_system" / "episode-drafts")
        with self.assertRaises(AuthoringError):
            self._author(SAMPLE)


if __name__ == "__main__":
    unittest.main()
