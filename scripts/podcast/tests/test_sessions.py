#!/usr/bin/env python3
"""Tests for _sessions.py — deterministic session grouping (2026-06-10).

Pins the locked decisions: sessions derive from source Parts, apply only
above the episode threshold (with config override), stamp contracts
append-only and idempotently, and stay completely absent for flat books.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _sessions as S


def _plan(counts):
    """Build TOC source_chapters with the given per-chapter episode counts."""
    out, ep = [], 1
    for i, n in enumerate(counts, start=1):
        eps = [{"ep_num": ep + j, "episode_slug": f"e{ep + j}"} for j in range(n)]
        out.append(
            {
                "sc_index": i,
                "source_title": f"Part {('One', 'Two', 'Three', 'Four', 'Five')[i - 1]} — Theme {i}",
                "episode_count": n,
                "episodes": eps,
            }
        )
        ep += n
    return out


class DeriveSessionsTest(unittest.TestCase):
    def test_mnd_shape_gets_five_sessions(self):
        sessions = S.derive_sessions(_plan([3, 4, 4, 5, 4]))
        self.assertEqual(len(sessions), 5)
        self.assertEqual(sessions[0]["episode_numbers"], [1, 2, 3])
        self.assertEqual(sessions[3]["episode_numbers"], [12, 13, 14, 15, 16])
        self.assertEqual(sessions[1]["session_title"], "Theme 2")
        self.assertEqual(sessions[1]["session_slug"], "theme-2")

    def test_small_book_stays_flat(self):
        self.assertIsNone(S.derive_sessions(_plan([2, 3, 3])))  # 8 <= threshold

    def test_single_source_chapter_stays_flat_even_when_long(self):
        self.assertIsNone(S.derive_sessions(_plan([12])))

    def test_force_on_overrides_threshold(self):
        self.assertIsNotNone(S.derive_sessions(_plan([2, 3]), force=True))

    def test_force_off_overrides_eligibility(self):
        self.assertIsNone(S.derive_sessions(_plan([5, 5, 5]), force=False))

    def test_session_for_episode(self):
        sessions = S.derive_sessions(_plan([3, 4, 4, 5, 4]))
        self.assertEqual(S.session_for_episode(sessions, 8)["session_index"], 3)
        self.assertIsNone(S.session_for_episode(sessions, 99))
        self.assertIsNone(S.session_for_episode(None, 1))


class TitleStrippingTest(unittest.TestCase):
    def test_strips_part_prefixes(self):
        cases = {
            "Part One — The True Sources of Knowledge": "The True Sources of Knowledge",
            "Part Two — Spiritual Symbols: The Architecture of Creation": "Spiritual Symbols: The Architecture of Creation",
            "Part 3: Knowledge versus Action": "Knowledge versus Action",
            "Book II - On the Imamate": "On the Imamate",
        }
        for raw, want in cases.items():
            self.assertEqual(S.session_title_from_source(raw), want)

    def test_passthrough_without_prefix(self):
        self.assertEqual(S.session_title_from_source("The Living Witness"), "The Living Witness")


class StampingTest(unittest.TestCase):
    def _book(self, tmp, counts):
        import json

        book = Path(tmp) / "Islamic" / "fixture"
        chunks = book / "_system" / "source" / "text" / "_chunks" / "0d"
        chunks.mkdir(parents=True)
        (chunks / "source-toc.json").write_text(json.dumps({"source_chapters": _plan(counts)}), encoding="utf-8")
        cc = book / "chapter-contracts"
        cc.mkdir(parents=True)
        ep = 1
        for n in counts:
            for _ in range(n):
                (cc / f"ep{ep:02d}.yml").write_text(
                    f"slug: ep{ep:02d}\nepisode_number: {ep}\ntitle: T{ep}\n", encoding="utf-8"
                )
                ep += 1
        return book

    def test_stamp_book_appends_fields_idempotently(self):
        import yaml

        with tempfile.TemporaryDirectory() as tmp:
            book = self._book(tmp, [3, 4, 4, 5, 4])
            n = S.stamp_book(book, log=lambda *a: None)
            self.assertEqual(n, 20)
            data = yaml.safe_load((book / "chapter-contracts" / "ep12.yml").read_text())
            self.assertEqual(data["session_index"], 4)
            self.assertEqual(data["session_episode"], 1)
            self.assertEqual(data["session_episode_count"], 5)
            self.assertEqual(data["session_title"], "Theme 4")
            # second run is a no-op
            self.assertEqual(S.stamp_book(book, log=lambda *a: None), 0)

    def test_flat_book_never_stamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book(tmp, [2, 3])  # 5 episodes — flat
            self.assertEqual(S.stamp_book(book, log=lambda *a: None), 0)
            text = (book / "chapter-contracts" / "ep01.yml").read_text()
            self.assertNotIn("session_index", text)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book(tmp, [3, 4, 4, 5, 4])
            n = S.stamp_book(book, dry_run=True, log=lambda *a: None)
            self.assertEqual(n, 20)
            text = (book / "chapter-contracts" / "ep01.yml").read_text()
            self.assertNotIn("session_index", text)


if __name__ == "__main__":
    unittest.main()
