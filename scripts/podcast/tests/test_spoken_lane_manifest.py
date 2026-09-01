#!/usr/bin/env python3
"""Unit tests for spoken_lane.manifest — the audiobook chapter-manifest reader.

Every case here is a defect that actually occurred while building this, or a
property the split step depends on. Two are worth naming, because both failed
SILENTLY — they returned a plausible answer rather than an error:

  * `(The_Devils)`. Some titles in the Dostoyevsky collection carry a trailing
    annotation, so `01_TheDouble_OpeningCredits(The_Devils)` does not END with
    "OpeningCredits". A suffix test misses that one boundary and folds The Double
    into Poor Folk — nineteen works come back, all of them looking right.

  * The dropped Introduction. Deriving the first work's start from "the first
    track saying Part or Chapter" swallowed that work's own `Introduction`
    track: 284 tracks instead of 285, with every work still present and
    plausible. Front matter is COUNTED by the caller for this reason.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from spoken_lane import manifest as M  # noqa: E402


def rows(*titles: str, length: int = 1000) -> list[M.Chapter]:
    """Chapters with contiguous offsets, so extent arithmetic is checkable."""
    return [M.Chapter(index=i, title=t, start_ms=i * length, length_ms=length) for i, t in enumerate(titles)]


class TestWorkName(unittest.TestCase):
    def test_plain_prefix(self):
        self.assertEqual(M.work_name("01_WhiteNights_OpeningCredits"), "WhiteNights")

    def test_annotated_suffix_still_matches(self):
        # The regression that merged The Double into Poor Folk.
        self.assertEqual(M.work_name("01_TheDouble_OpeningCredits(The_Devils)"), "TheDouble")

    def test_non_boundary_track_has_no_work(self):
        self.assertIsNone(M.work_name("Part 1 Chapter 01"))
        self.assertIsNone(M.work_name("Opening Credits"))


class TestSplitWorks(unittest.TestCase):
    def test_boundaries_and_full_coverage(self):
        chapters = rows(
            "Opening Credits",  # container front matter
            "Title",
            "Introduction",  # belongs to the FIRST work, not the container
            "Part 1 Chapter 01",
            "01_WhiteNights_OpeningCredits",
            "02_WhiteNights_FirstNight",
            "01_TheDouble_OpeningCredits(The_Devils)",
            "02_TheDouble_Chapter01",
            "End Credits",  # container trailing
        )
        works = M.split_works(chapters, first_work_name="NotesFromUnderground", front_matter=2, trailing=1)
        self.assertEqual([w.name for w in works], ["NotesFromUnderground", "WhiteNights", "TheDouble"])
        # Nothing is lost and nothing is double-counted.
        self.assertEqual(sum(len(w.chapters) for w in works) + 2 + 1, len(chapters))

    def test_first_work_keeps_its_own_introduction(self):
        chapters = rows("Opening Credits", "Introduction", "Part 1 Chapter 01", "01_X_OpeningCredits")
        works = M.split_works(chapters, first_work_name="First", front_matter=1)
        self.assertEqual(len(works[0].chapters), 2, "the work's Introduction must survive")

    def test_trailing_track_is_not_attached_to_the_last_work(self):
        chapters = rows("01_X_OpeningCredits", "02_X_Chapter1", "End Credits")
        works = M.split_works(chapters, trailing=1)
        self.assertEqual(len(works), 1)
        self.assertNotIn("End Credits", [c.title for c in works[0].chapters])

    def test_no_boundaries_returns_nothing(self):
        self.assertEqual(M.split_works(rows("A", "B")), [])

    def test_empty_input(self):
        self.assertEqual(M.split_works([]), [])

    def test_extent_spans_first_start_to_last_end(self):
        works = M.split_works(rows("01_X_OpeningCredits", "02_X_Chapter1"))
        self.assertEqual(works[0].start_ms, 0)
        self.assertEqual(works[0].end_ms, 2000)
        self.assertEqual(works[0].duration_ms, 2000)


class TestReconcile(unittest.TestCase):
    def test_agrees_within_tolerance(self):
        ok, diff = M.reconcile(rows("a", "b"), 2000 + 40)
        self.assertTrue(ok)
        self.assertEqual(diff, 40)

    def test_rejects_a_manifest_for_a_different_file(self):
        ok, _ = M.reconcile(rows("a", "b"), 9_000_000)
        self.assertFalse(ok)

    def test_unreadable_duration_does_not_block(self):
        # A probe failure is not evidence against the manifest.
        ok, diff = M.reconcile(rows("a"), None)
        self.assertTrue(ok)
        self.assertIsNone(diff)

    def test_empty_manifest_is_never_ok(self):
        ok, _ = M.reconcile([], 1000)
        self.assertFalse(ok)


class TestSlugify(unittest.TestCase):
    def test_camel_case(self):
        self.assertEqual(M.slugify("TheBrothersKaramazov"), "the-brothers-karamazov")

    def test_underscores(self):
        self.assertEqual(M.slugify("A_Faint_Heart"), "a-faint-heart")

    def test_override_repairs_a_typo_in_the_source_metadata(self):
        self.assertEqual(
            M.slugify("TheDreamOfaRidiculousMan", {"TheDreamOfaRidiculousMan": "the-dream-of-a-ridiculous-man"}),
            "the-dream-of-a-ridiculous-man",
        )

    def test_override_does_not_leak_to_other_names(self):
        self.assertEqual(M.slugify("WhiteNights", {"Other": "x"}), "white-nights")


class TestFromLog(unittest.TestCase):
    def test_picks_the_largest_array(self):
        import tempfile

        log = (
            '{"chapters":[{"index":0,"length_ms":10,"start_offset_ms":0,"title":"solo"}]}\n'
            '{"chapters":[{"index":0,"length_ms":10,"start_offset_ms":0,"title":"a"},'
            '{"index":1,"length_ms":10,"start_offset_ms":10,"title":"b"}]}\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "librocore.log"
            p.write_text(log)
            self.assertEqual([c.title for c in M.from_log(p)], ["a", "b"])

    def test_malformed_rows_are_skipped_not_fatal(self):
        import tempfile

        log = '{"chapters":[{"title":"no offsets"},{"length_ms":5,"start_offset_ms":0,"title":"ok"}]}'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "librocore.log"
            p.write_text(log)
            self.assertEqual([c.title for c in M.from_log(p)], ["ok"])


if __name__ == "__main__":
    unittest.main()
