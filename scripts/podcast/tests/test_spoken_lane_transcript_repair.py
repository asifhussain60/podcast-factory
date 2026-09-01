#!/usr/bin/env python3
"""Repairing what an exporter mangled, and refusing to guess when it cannot.

The case that produced this module is pinned by
`test_it_reproduces_the_hand_repair_exactly`: the 138 replacement characters
TurboScribe left in White Nights' fifth chapter were fixed by hand with a
throwaway script, and this module must reach the same 138 characters — 28
apostrophes and 110 quotes — from the committed original.

The other half of the contract is the refusal. A replacement character whose
context does not say what it was stays exactly where it is, so `transcript_check`
keeps reporting CORRUPTION and the book keeps refusing to advance. A guessed
character in a book is worse than a blocked book.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from spoken_lane import transcript_check as T  # noqa: E402
from spoken_lane.transcript_repair import repair_book, repair_text  # noqa: E402

BAD = T.REPLACEMENT_CHAR


class TestClassification(unittest.TestCase):
    def test_between_two_letters_is_an_apostrophe(self):
        out, apo, quo, unres = repair_text(f"I do{BAD}t know")
        self.assertEqual(out, "I do't know")
        self.assertEqual((apo, quo, unres), (1, 0, 0))

    def test_after_punctuation_is_an_opening_quote(self):
        out, apo, quo, _ = repair_text(f"she said, {BAD}Nastenka, go")
        self.assertEqual(out, 'she said, "Nastenka, go')
        self.assertEqual((apo, quo), (0, 1))

    def test_after_a_word_and_before_a_space_is_a_closing_quote(self):
        out, _, quo, _ = repair_text(f"a bench.{BAD} Over the course")
        self.assertEqual(out, 'a bench." Over the course')
        self.assertEqual(quo, 1)

    def test_clean_text_is_returned_untouched(self):
        text = "Nothing wrong here at all."
        self.assertEqual(repair_text(text), (text, 0, 0, 0))

    def test_it_is_idempotent(self):
        once, *_ = repair_text(f"do{BAD}t")
        twice, apo, quo, unres = repair_text(once)
        self.assertEqual(once, twice)
        self.assertEqual((apo, quo, unres), (0, 0, 0))


class TestItRefusesToGuess(unittest.TestCase):
    """The half that matters more: damage it cannot explain stays visible."""

    def test_unclassifiable_damage_is_left_in_place(self):
        # Replacement character flanked by other replacement characters: nothing
        # in the context says what any of them were.
        out, apo, quo, unres = repair_text(f"{BAD}{BAD}{BAD}")
        self.assertIn(BAD, out)
        self.assertGreater(unres, 0)
        self.assertEqual((apo, quo), (0, 0))

    def test_the_check_still_blocks_after_a_partial_repair(self):
        with tempfile.TemporaryDirectory() as d:
            book = Path(d) / "bk"
            (book / "m4a" / "Episodes").mkdir(parents=True)
            (book / "transcripts").mkdir(parents=True)
            (book / "m4a" / "Episodes" / "ep01.m4a").write_bytes(b"\0")
            (book / "transcripts" / "ep01.vtt").write_text(
                f"WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\nI do{BAD}t know {BAD}{BAD}{BAD} here\n",
                encoding="utf-8",
            )
            repair_book(book, apply=True)
            text = (book / "transcripts" / "ep01.vtt").read_text(encoding="utf-8")
            self.assertIn("do't", text, "the resolvable damage was repaired")
            self.assertIn(BAD, text, "the unresolvable damage was kept")
            self.assertIn("CORRUPTION", {f.code for f in T.check_book(book)})
            self.assertFalse(T.is_complete(book), "a book with unexplained damage must not advance")


class TestTheRealDamage(unittest.TestCase):
    def test_it_reproduces_the_hand_repair_exactly(self):
        """The 138 characters in ep05, from the committed original."""
        repo = SCRIPTS_PODCAST.parents[1]
        rel = "content/Audiobook/white-nights/transcripts/ep05.vtt"
        proc = subprocess.run(["git", "show", f"46c1492e:{rel}"], capture_output=True, text=True, cwd=repo)
        if proc.returncode != 0:
            self.skipTest("the commit holding the damaged original is not present")
        damaged = proc.stdout
        self.assertEqual(damaged.count(BAD), 138, "the fixture is the real damage")

        repaired, apo, quo, unres = repair_text(damaged)
        self.assertEqual((apo, quo, unres), (28, 110, 0))
        self.assertEqual(repaired, (repo / rel).read_text(encoding="utf-8"))

    def test_no_transcript_on_disk_still_carries_damage(self):
        import _paths

        dirty = []
        for *_r, d in _paths.iter_content():
            for vtt in (Path(d) / "transcripts").glob("ep*.vtt"):
                if BAD in vtt.read_text(encoding="utf-8"):
                    dirty.append(str(vtt))
        self.assertEqual(dirty, [], f"transcripts still holding replacement characters: {dirty}")


if __name__ == "__main__":
    unittest.main()
