#!/usr/bin/env python3
"""Tests for the Phase 0d over-cramming brake (episode density ceiling).

Guards the 2026-06-04 fix: a source chapter that maps to episodes far above the
per-episode density ceiling must be flagged for a split, profile-aware (dense
doctrinal caps tighter than narrative). Root-caused by Ayyuhal Walad, whose two
8,500–9,000-word episodes each packed ~24 distinct teachings.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _validator_constants import (
    EPISODE_DENSITY_CEILING_DENSE,
    EPISODE_DENSITY_CEILING_NARRATIVE,
    episode_overcrammed,
)


class EpisodeDensityTests(unittest.TestCase):
    def test_dense_8500_word_single_episode_flags_split(self):
        # A doctrinal chapter shipped as ONE episode at 8,500w is over-crammed.
        self.assertGreaterEqual(episode_overcrammed(8500, 1, EPISODE_DENSITY_CEILING_DENSE), 2)

    def test_ayyuhal_walad_actual_case(self):
        # ch02 = 8,955w as one episode → must split.
        self.assertGreaterEqual(episode_overcrammed(8955, 1, EPISODE_DENSITY_CEILING_DENSE), 2)

    def test_in_band_episode_passes(self):
        # 4,000w as one episode is within the dense ceiling → not flagged.
        self.assertEqual(episode_overcrammed(4000, 1, EPISODE_DENSITY_CEILING_DENSE), 0)

    def test_narrative_9000_word_episode_passes(self):
        # The narrative ceiling is wider — a 9,000w low-density episode is fine.
        self.assertEqual(episode_overcrammed(9000, 1, EPISODE_DENSITY_CEILING_NARRATIVE), 0)

    def test_already_split_passes(self):
        # 9,000w over 2 episodes = 4,500/episode ≤ 6,000 → not flagged.
        self.assertEqual(episode_overcrammed(9000, 2, EPISODE_DENSITY_CEILING_DENSE), 0)

    def test_split_count_is_ceil(self):
        # 13,000w / 6,000 ceiling → ceil = 3 episodes.
        self.assertEqual(episode_overcrammed(13000, 1, EPISODE_DENSITY_CEILING_DENSE), 3)

    def test_dense_ceiling_is_tighter_than_narrative(self):
        self.assertLess(EPISODE_DENSITY_CEILING_DENSE, EPISODE_DENSITY_CEILING_NARRATIVE)


class SkippedUnitsAreNotMeasuredTests(unittest.TestCase):
    """A source chapter that yields no episodes has no episode to over-cram.

    Degrees of Excellence marked its back matter — bibliography, both indexes,
    and a complete duplicate translation of the treatise, 30,662 words — as
    `essential: skip` with `episode_count: 0`. Correct. The density brake still
    measured it, because the gate's caller passed 0 straight into a function
    whose `max(1, ...)` reads "no episodes" as "one episode", and phase 0d died
    demanding the bibliography be split into six episodes.
    """

    def _gate(self, source_chapters, ceiling=EPISODE_DENSITY_CEILING_DENSE):
        """What phase 0d does with each source chapter — no extra predicate.

        The exemption lives in `episode_overcrammed` itself, not in the caller,
        so every caller inherits it and none can forget it.
        """
        return [
            sc.get("sc_index")
            for sc in source_chapters
            if episode_overcrammed(sc["word_count"], int(sc.get("episode_count", 1)), ceiling)
        ]

    def test_zero_episodes_is_exempt_at_the_function_itself(self):
        self.assertEqual(episode_overcrammed(30662, 0, EPISODE_DENSITY_CEILING_DENSE), 0)

    def test_the_degrees_of_excellence_back_matter_is_not_flagged(self):
        back_matter = {
            "sc_index": 5,
            "word_count": 30662,
            "episode_count": 0,
            "essential": "skip",
        }
        self.assertEqual(self._gate([back_matter]), [])

    def test_zero_episodes_alone_is_enough_to_exempt(self):
        # Not every skipped unit carries the `essential` key.
        self.assertEqual(self._gate([{"sc_index": 1, "word_count": 30662, "episode_count": 0}]), [])

    def test_a_real_episode_is_still_flagged(self):
        # The brake must not have been defanged for units that DO ship.
        self.assertEqual(self._gate([{"sc_index": 4, "word_count": 24102, "episode_count": 1}]), [4])

    def test_a_skip_unit_beside_a_crammed_one_does_not_mask_it(self):
        chapters = [
            {"sc_index": 5, "word_count": 30662, "episode_count": 0, "essential": "skip"},
            {"sc_index": 4, "word_count": 24102, "episode_count": 2},
        ]
        self.assertEqual(self._gate(chapters), [4])


if __name__ == "__main__":
    unittest.main()
