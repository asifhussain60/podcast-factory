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


if __name__ == "__main__":
    unittest.main()
