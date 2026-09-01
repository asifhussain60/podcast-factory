#!/usr/bin/env python3
"""The spoken lane's prose cleanup, and the review that decides readiness.

Two rules were candidates for auto-repair and BOTH were rejected after measuring
them against books already on disk. Those measurements are the tests that matter
here, because in each case the auto-repair looked obviously right:

  * ALL-CAPS as a heading. True in White Nights. In `surah-al-fateha` the caps
    are `AM YOUR KING` and `BOW DOWN BEFORE ME` — emphatic speech inside a
    quotation, and promoting them would put a divine utterance in a heading.

  * A space before a comma as loose typing. In these books it is the residue of
    a MISSING ARABIC TERM ("The word  , which is also used in Urdu"). Closing it
    would conceal a content gap rather than fix one.

And one rule was rejected for a subtler reason: the first version of the spacing
repair used `\\w` and `\\s+`, which Python treats as Unicode-aware, so it edited
Arabic inside a Qur'anic blockquote. The character classes are ASCII-only now and
`test_arabic_is_never_touched` is why they must stay that way.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _sessions_prose_format as spf  # noqa: E402
from spoken_lane import prose_review as R  # noqa: E402


class TestEchoedHeading(unittest.TestCase):
    """The one defect safe to fix unaided: zero occurrences in any shipped book."""

    def test_a_repeated_title_is_dropped(self):
        out, ch = spf.strip_echoed_heading("First Night It was a beautiful night.", "First Night")
        self.assertEqual(out, "It was a beautiful night.")
        self.assertEqual(ch[0]["rule"], "echoed_heading")

    def test_it_matches_regardless_of_case(self):
        out, _ = spf.strip_echoed_heading("SECOND NIGHT Well, you've made it.", "Second Night")
        self.assertEqual(out, "Well, you've made it.")

    def test_trailing_punctuation_from_inflection_is_absorbed(self):
        out, _ = spf.strip_echoed_heading("Morning? My night gave way.", "Morning")
        self.assertEqual(out, "My night gave way.")

    def test_a_title_appearing_later_is_left_alone(self):
        body = "It was a beautiful night. First Night was the name he gave it."
        self.assertEqual(spf.strip_echoed_heading(body, "First Night")[0], body)

    def test_a_chapter_that_merely_starts_with_the_same_word_survives(self):
        body = "Morningside Park was empty."
        self.assertEqual(spf.strip_echoed_heading(body, "Morning")[0], body)

    def test_no_heading_is_a_no_op(self):
        self.assertEqual(spf.strip_echoed_heading("Anything at all.", "")[0], "Anything at all.")


class TestSpacingRepair(unittest.TestCase):
    def test_an_orphaned_hyphen_is_rejoined(self):
        self.assertEqual(spf.repair_spacing("a dark -haired girl")[0], "a dark-haired girl")
        self.assertEqual(spf.repair_spacing("twenty -four hours")[0], "twenty-four hours")

    def test_an_em_dash_aside_is_untouched(self):
        for body in ("furniture—tables, chairs", "a pause - and then silence"):
            self.assertEqual(spf.repair_spacing(body)[0], body)

    def test_arabic_is_never_touched(self):
        """The bug that edited a Qur'anic blockquote.

        `\\w` and `\\s` are Unicode-aware in Python, so the first version of this
        rule matched around Arabic script. The classes are ASCII-only now.
        """
        body = "> And He taught Adam all the names , then He showed them\n\nرَسُولُ اللَّهِ , he said"
        self.assertEqual(spf.repair_spacing(body)[0], body)

    def test_a_newline_is_never_closed_up(self):
        """`\\s+` matched newlines, so a comma opening a line would have been
        pulled onto the previous one and a paragraph break lost."""
        body = "the end of a line\n\n, and a comma opening the next"
        self.assertEqual(spf.repair_spacing(body)[0], body)


class TestTheEntryPointStaysCompatible(unittest.TestCase):
    def test_without_a_heading_the_echo_rule_cannot_fire(self):
        """Every existing caller omits `heading`, and must be byte-identical."""
        body = "First Night It was a beautiful night."
        self.assertEqual(spf.normalize_sessions_prose(body)[0], body)

    def test_with_a_heading_it_does(self):
        body = "First Night It was a beautiful night."
        self.assertEqual(spf.normalize_sessions_prose(body, heading="First Night")[0], "It was a beautiful night.")


class TestTheShippedBooksDoNotMove(unittest.TestCase):
    """The check that caught the Qur'anic-blockquote regression."""

    def test_every_sessions_book_normalizes_to_itself(self):
        import _paths

        moved = []
        for *_r, d in _paths.iter_content():
            book_md = Path(d) / "book" / "book.md"
            if "Sessions" not in str(d) or not book_md.exists():
                continue
            text = book_md.read_text(encoding="utf-8")
            if spf.normalize_sessions_prose(text)[0] != text:
                moved.append(Path(d).name)
        self.assertEqual(moved, [], f"normalizing changed a shipped Sessions book: {moved}")


class TestReviewReportsRatherThanRewrites(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.d = Path(self._td.name)
        (self.d / "book").mkdir(parents=True)

    def tearDown(self):
        self._td.cleanup()

    def _write(self, body: str, heading: str = "A Chapter") -> None:
        (self.d / "book" / "book.md").write_text(f"# Book\n\n## {heading}\n\n{body}\n", encoding="utf-8")

    def test_caps_are_reported_never_edited(self):
        self._write("A line. AM YOUR KING, he said. And then more.")
        codes = {f.code for f in R.review_book(self.d)}
        self.assertIn("SPOKEN_HEADING", codes)
        self.assertNotIn("SPOKEN_HEADING", R.BLOCKING, "capitals must never block or be auto-fixed")
        self.assertIn("AM YOUR KING", (self.d / "book" / "book.md").read_text(encoding="utf-8"))

    def test_a_gap_before_a_comma_is_advisory(self):
        self._write("The word  , which is also used in Urdu, means this.")
        found = [f for f in R.review_book(self.d) if f.code == "GAP_BEFORE_COMMA"]
        self.assertTrue(found)
        self.assertFalse(found[0].blocking)

    def test_publisher_credits_are_flagged(self):
        self._write("This is White Nights, translated by Tim Zengerink, narrated by Zeke Ring.")
        self.assertIn("FRONT_MATTER", {f.code for f in R.review_book(self.d)})


class TestComposerReadiness(unittest.TestCase):
    """Asif, 2026-09-01: do not send a person to the Composer before this passes."""

    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.d = Path(self._td.name)
        (self.d / "book").mkdir(parents=True)

    def tearDown(self):
        self._td.cleanup()

    def _write(self, body: str, heading: str = "First Night") -> None:
        (self.d / "book" / "book.md").write_text(f"# Book\n\n## {heading}\n\n{body}\n", encoding="utf-8")

    def test_an_echoed_heading_blocks(self):
        self._write("First Night It was a beautiful night.")
        self.assertFalse(R.is_composer_ready(self.d))

    def test_an_orphaned_hyphen_blocks(self):
        self._write("It was a dark -haired girl.")
        self.assertFalse(R.is_composer_ready(self.d))

    def test_advisory_findings_alone_do_not_block(self):
        """A gate waiting on human judgement never opens."""
        self._write("A line. AM YOUR KING, he said. Translated by someone.")
        self.assertTrue(R.is_composer_ready(self.d))

    def test_a_book_with_no_composed_edition_is_not_ready(self):
        self.assertFalse(R.is_composer_ready(self.d))

    def test_the_real_audiobook_is_ready_and_clean(self):
        import _paths

        found = _paths.find_content("white-nights")
        if not found:
            self.skipTest("white-nights not on disk")
        book = Path(found[-1])
        blocking = [str(f) for f in R.review_book(book) if f.blocking]
        self.assertEqual(blocking, [], f"white-nights has blocking findings: {blocking}")
        self.assertTrue(R.is_composer_ready(book))


if __name__ == "__main__":
    unittest.main()


class TestParagraphsBreakWhereSentencesDo(unittest.TestCase):
    """The defect Asif circled twice: a sentence split across a paragraph break.

    The rule replaced was `lines[i:i+12]` — a new paragraph every twelfth cue,
    counted without looking at the words — which put 168 of White Nights' 359
    paragraphs (46%) mid-sentence. Fixed at the source rather than detected
    after: a check that reports a self-inflicted wound on every book is noise.
    """

    def _cues(self, text: str) -> list[str]:
        return text.split("|")

    def test_a_paragraph_never_ends_mid_sentence(self):
        from spoken_lane.scaffold import group_into_paragraphs

        cues = self._cues("He meets Nastenka, a young woman weeping on|a bench. " + "word " * 80 + "End here.")
        out = group_into_paragraphs(cues, target_words=10)
        for para in out.split("\n\n"):
            self.assertRegex(para.rstrip(), r"[.!?][\"'’”)\]]*$", f"paragraph ends mid-sentence: {para[-60:]!r}")

    def test_no_paragraph_starts_mid_sentence(self):
        from spoken_lane.scaffold import group_into_paragraphs

        cues = ["The night was long.", "It ended.", "Then came morning.", "She left."] * 6
        out = group_into_paragraphs(cues, target_words=8)
        for para in out.split("\n\n"):
            self.assertRegex(para, r"^[\"'(\[A-Z0-9]", f"paragraph starts mid-sentence: {para[:60]!r}")

    def test_the_words_are_never_altered(self):
        """Only WHERE a paragraph ends is decided. Read-along depends on this."""
        from spoken_lane.scaffold import group_into_paragraphs

        cues = ["One two three.", "Four five six.", "Seven eight nine."]
        out = group_into_paragraphs(cues, target_words=4)
        self.assertEqual(out.replace("\n\n", " ").split(), " ".join(cues).split())

    def test_a_tail_with_no_sentence_end_is_not_orphaned(self):
        from spoken_lane.scaffold import group_into_paragraphs

        out = group_into_paragraphs(["A full sentence here.", "and a trailing fragment"], target_words=3)
        self.assertIn("trailing fragment", out)
        self.assertEqual(len(out.split("\n\n")), 1, "the fragment joins the paragraph, it does not become one")

    def test_a_transcript_with_no_punctuation_at_all_still_returns_its_words(self):
        from spoken_lane.scaffold import group_into_paragraphs

        cues = ["no punctuation anywhere"] * 5
        self.assertEqual(group_into_paragraphs(cues, target_words=3).split(), " ".join(cues).split())

    def test_mid_sentence_breaks_now_block(self):
        """Advisory while the grouping manufactured it; blocking now it cannot."""
        self.assertIn("MID_SENTENCE_BREAKS", R.BLOCKING)

    def test_the_real_book_has_none(self):
        import _paths

        found = _paths.find_content("white-nights")
        if not found:
            self.skipTest("white-nights not on disk")
        import re as _re

        text = (Path(found[-1]) / "book" / "book.md").read_text(encoding="utf-8")
        paras = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
        bad = [p for p in paras if not _re.match(r"^[\"'(\[A-Z0-9]", p)]
        self.assertEqual(bad, [], f"{len(bad)}/{len(paras)} paragraphs start mid-sentence")
