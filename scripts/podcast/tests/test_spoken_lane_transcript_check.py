#!/usr/bin/env python3
"""Unit tests for spoken_lane.transcript_check.

Every case is a failure that HAS happened or was one keystroke away, and each is
written so it FAILS when the check is removed -- the point of a guard is that it
can fire, and a guard nobody proved could fire is decoration.

Two of these are bugs in the CHECKER rather than in a transcript, kept because
both made it useless in opposite directions:

  * It looked only for `.m4a`. Sessions books hold `.mp3`, so every one of their
    transcripts came back ORPHAN -- 339 findings, almost all noise. A checker
    that cries wolf is worse than no checker.

  * `--all` swept in every book with a `transcripts/` folder, including podcast
    books whose transcripts are of NotebookLM's GENERATED episodes and answer to
    none of this contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from spoken_lane import transcript_check as T  # noqa: E402

VTT = "WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\nHello there friend\n"


def book(tmp: Path, *, audio: dict[int, str] | None = None, vtts: dict[int, str] | None = None) -> Path:
    """A book dir with the flat spoken-lane layout. `audio` maps ep -> extension."""
    d = tmp / "bk"
    (d / "m4a" / "Episodes").mkdir(parents=True, exist_ok=True)
    (d / "transcripts").mkdir(parents=True, exist_ok=True)
    (d / "_system").mkdir(parents=True, exist_ok=True)
    for n, ext in (audio or {}).items():
        (d / "m4a" / "Episodes" / f"ep{n:02d}{ext}").write_bytes(b"\0")
    for n, body in (vtts or {}).items():
        (d / "transcripts" / f"ep{n:02d}.vtt").write_text(body, encoding="utf-8")
    return d


def lengths(d: Path, mapping: dict[int, int]) -> None:
    """Write the chapter index the drift check reads."""
    import json

    (d / "_system" / "audiobook-chapters.json").write_text(
        json.dumps({"chapters": [{"episode": n, "length_ms": ms} for n, ms in mapping.items()]}),
        encoding="utf-8",
    )


def codes(findings) -> set[str]:
    return {f.code for f in findings}


class TestCleanBookPasses(unittest.TestCase):
    def test_matched_audio_and_transcript_is_clean(self):
        d = book(Path(self.tmp), audio={1: ".m4a"}, vtts={1: VTT})
        self.assertEqual(T.check_book(d), [])
        self.assertTrue(T.is_complete(d))

    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()


class TestChecks(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_corruption_is_caught(self):
        """The 138 replacement characters in White Nights' fifth chapter."""
        broken = VTT.replace("friend", "don�t")
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: broken})
        self.assertIn("CORRUPTION", codes(T.check_book(d)))
        self.assertFalse(T.is_complete(d))

    def test_an_srt_saved_as_vtt_is_caught(self):
        """A comma instead of a period parses to zero cues, silently."""
        srt = "WEBVTT\n\n1\n00:00:00,000 --> 00:00:05,000\nHello there\n"
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: srt})
        self.assertIn("UNPARSEABLE", codes(T.check_book(d)))

    def test_a_missing_transcript_is_caught(self):
        d = book(self.tmp, audio={1: ".m4a", 2: ".m4a"}, vtts={1: VTT})
        found = [f for f in T.check_book(d) if f.code == "MISSING"]
        self.assertEqual([f.episode for f in found], [2])

    def test_a_transcript_with_no_recording_is_caught(self):
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: VTT, 2: VTT})
        found = [f for f in T.check_book(d) if f.code == "ORPHAN"]
        self.assertEqual([f.episode for f in found], [2])

    def test_a_transcript_of_a_different_chapter_is_caught(self):
        """Cues ending 5s in, against a 40-minute recording."""
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: VTT})
        lengths(d, {1: 40 * 60 * 1000})
        self.assertIn("MISPAIRED", codes(T.check_book(d)))

    def test_a_correct_pairing_does_not_trip_the_drift_check(self):
        """The real margin is under a second; this must not fire on that."""
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: VTT})
        lengths(d, {1: 5_400})  # 400ms of trailing silence, as White Nights has
        self.assertNotIn("MISPAIRED", codes(T.check_book(d)))

    def test_an_empty_transcript_is_caught(self):
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: "WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.000\n \n"})
        self.assertTrue(codes(T.check_book(d)) & {"EMPTY", "UNPARSEABLE"})


class TestTheCheckerSOwnBugs(unittest.TestCase):
    """Both of these made the checker useless, in opposite directions."""

    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_mp3_recordings_are_recognised(self):
        """Sessions books hold .mp3. Looking only for .m4a reported every one of
        their transcripts as an orphan -- 339 findings, almost all this bug."""
        d = book(self.tmp, audio={1: ".mp3"}, vtts={1: VTT})
        self.assertEqual(T.check_book(d), [])
        self.assertEqual(T.episode_numbers(d), [1])

    def test_both_extensions_at_once(self):
        d = book(self.tmp, audio={1: ".m4a", 2: ".mp3"}, vtts={1: VTT, 2: VTT})
        self.assertEqual(T.episode_numbers(d), [1, 2])
        self.assertEqual(T.check_book(d), [])

    def test_a_podcast_book_s_nested_audio_is_not_read_as_chapters(self):
        """`m4a/Episodes/Session 2 - X/EP-01-....m4a` is a different layout for a
        different thing; reading it here would invent chapters."""
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: VTT})
        nested = d / "m4a" / "Episodes" / "Session 2 - Something"
        nested.mkdir(parents=True)
        (nested / "EP-01-Title.m4a").write_bytes(b"\0")
        self.assertEqual(T.episode_numbers(d), [1])

    def test_only_spoken_lane_books_are_swept_by_all(self):
        import json

        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: VTT})
        state = d / "_system" / "orchestrator-state.json"
        self.assertFalse(T._is_spoken_lane(d), "no state file is not the spoken lane")
        state.write_text(json.dumps({"pipeline_mode": "orchestrated"}), encoding="utf-8")
        self.assertFalse(T._is_spoken_lane(d), "a podcast book is not the spoken lane")
        state.write_text(json.dumps({"pipeline_mode": "sessions_lane"}), encoding="utf-8")
        self.assertTrue(T._is_spoken_lane(d))

    def test_a_book_with_no_recordings_is_not_complete(self):
        """Otherwise `all([])` is True and an empty book claims the step."""
        d = book(self.tmp, vtts={1: VTT})
        self.assertFalse(T.is_complete(d))


class TestCorrectTypographyIsNotFlagged(unittest.TestCase):
    """A check that fired on these would train its reader to ignore it."""

    def setUp(self):
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_em_dashes_accents_and_cedillas_pass(self):
        body = VTT.replace("Hello there friend", "a cliché façade—tables, chairs")
        d = book(self.tmp, audio={1: ".m4a"}, vtts={1: body})
        self.assertEqual(T.check_book(d), [])


class TestTheRealBooks(unittest.TestCase):
    """The three transcribed books on disk must be clean, and stay clean."""

    def test_every_transcribed_spoken_book_passes(self):
        import _paths

        dirty = []
        for *_r, d in _paths.iter_content():
            book_dir = Path(d)
            if not T._is_spoken_lane(book_dir):
                continue
            findings = [f for f in T.check_book(book_dir) if f.code != "MISSING"]
            if findings:
                dirty.append((book_dir.name, [str(f) for f in findings]))
        self.assertEqual(dirty, [], f"spoken books with unusable transcripts: {dirty}")


if __name__ == "__main__":
    unittest.main()
