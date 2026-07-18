#!/usr/bin/env python3
"""Tests for the NotebookLM density planner (density_planner.py) and its
profile registry (_density_profiles.py).

Guards the 2026-06-11 build: deterministic composite scoring + optimal
adjacent-partition grouping that decides standalone / combine / flag_thin /
flag_dense and assigns the NotebookLM Length setting per episode, without
ever touching chapters/ or episodes/ content.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import density_planner as dp
from _density_profiles import (
    MODE_DEFAULT,
    MODE_LONGER,
    get_profile,
    planner_enabled,
)
from _notebooklm_table import (
    DEFAULT_LENGTH,
    length_for_episode,
    load_density_lengths,
)
from build_episode_txt import _insert_pacing_block

# ── synthetic fixture helpers ────────────────────────────────────────────────

POOL_A = (
    "covenant threshold witness guidance lantern orchard pilgrim summons radiance station fidelity remembrance"
).split()
POOL_B = ("ledger harvest compass voyage timber anchor meridian cartography lighthouse harbor sextant mariner").split()


def _prose(pool: list[str], n_words: int) -> str:
    out = []
    i = 0
    while len(out) < n_words:
        out.append(pool[i % len(pool)])
        i += 1
        if i % 11 == 0:
            out[-1] += "."
    return " ".join(out)


def _chapter_text(pool: list[str], concepts: int, words_per_concept: int) -> str:
    parts = ["# A synthetic teaching", "", "## Where this episode opens", "", _prose(pool, 80), ""]
    for k in range(1, concepts + 1):
        parts += [f"## Teaching number {k}", "", _prose(pool, words_per_concept), ""]
    parts += ["## What this episode lands", "", _prose(pool, 60), ""]
    return "\n".join(parts)


class FixtureBook:
    """A throwaway book directory with synthetic chapters + contracts."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="density-planner-test-"))
        (self.root / "chapters").mkdir()
        (self.root / "chapter-contracts").mkdir()
        (self.root / "_system").mkdir()
        self._write_config()
        self.n = 0

    def _write_config(self, extra: str = ""):
        (self.root / "_system" / "series-config.yaml").write_text(
            "slug: synthetic-density-test\ncontent_profile: islamic_scholarly\n" + extra, encoding="utf-8"
        )

    def add_chapter(self, slug: str, pool: list[str], concepts: int, words_per_concept: int, session: int) -> None:
        self.n += 1
        text = _chapter_text(pool, concepts, words_per_concept)
        (self.root / "chapters" / f"ch{self.n:02d}-{slug}.txt").write_text(text, encoding="utf-8")
        (self.root / "chapter-contracts" / f"{slug}.yml").write_text(
            f"slug: {slug}\n"
            f"episode_number: {self.n}\n"
            f"title: Chapter {self.n}\n"
            f"session_index: {session}\n"
            f"session_title: Part {session}\n",
            encoding="utf-8",
        )

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


# ── profile registry ─────────────────────────────────────────────────────────


class ProfileRegistryTests(unittest.TestCase):
    def test_exact_lookup_and_fallback(self):
        islamic = get_profile("islamic_scholarly", MODE_DEFAULT)
        self.assertEqual(islamic.max_words_soft, 3200)
        fallback = get_profile("some_unknown_profile", MODE_LONGER)
        self.assertEqual(fallback.max_words_soft, 9500)  # "*" narrative entry

    def test_longer_ceiling_matches_dense_brake(self):
        # The planner must never recommend a group the Phase 0d over-cramming
        # brake would reject: longer.max_words_soft == 6,000 for scholarly.
        from _validator_constants import EPISODE_DENSITY_CEILING_DENSE

        prof = get_profile("islamic_scholarly", MODE_LONGER)
        self.assertEqual(prof.max_words_soft, EPISODE_DENSITY_CEILING_DENSE)

    def test_per_book_override(self):
        book = FixtureBook()
        try:
            book._write_config(
                "density_profiles:\n  default_deep_dive:\n    max_words_soft: 2900\n    bogus_field: 12\n"
            )
            prof = get_profile("islamic_scholarly", MODE_DEFAULT, book.root)
            self.assertEqual(prof.max_words_soft, 2900)  # override applied
            self.assertEqual(prof.min_words_soft, 1800)  # untouched field
        finally:
            book.cleanup()

    def test_planner_enabled_gate(self):
        book = FixtureBook()
        try:
            self.assertFalse(planner_enabled(book.root))  # default: off
            book._write_config("density_planner: on\n")
            self.assertTrue(planner_enabled(book.root))
        finally:
            book.cleanup()


# ── composite risk ───────────────────────────────────────────────────────────


class CompressionRiskTests(unittest.TestCase):
    def setUp(self):
        self.prof = get_profile("islamic_scholarly", MODE_DEFAULT)

    def test_risk_clamped_to_unit_interval(self):
        self.assertEqual(dp.compression_risk(0, 0, 0, 0, self.prof), 0.0)
        self.assertLessEqual(dp.compression_risk(50000, 40, 99, 99, self.prof), 1.0)

    def test_risk_monotonic_in_concepts(self):
        lo = dp.compression_risk(2600, 2, 5, 2, self.prof)
        hi = dp.compression_risk(2600, 5, 5, 2, self.prof)
        self.assertGreater(hi, lo)

    def test_vocab_load_raises_risk(self):
        plain = dp.compression_risk(2600, 3, 0, 0, self.prof)
        contested = dp.compression_risk(2600, 3, 14, 8, self.prof)
        self.assertGreater(contested, plain)


# ── grouping (DP partition) ──────────────────────────────────────────────────


class GroupingTests(unittest.TestCase):
    def test_healthy_chapters_stay_standalone(self):
        book = FixtureBook()
        try:
            for i in range(4):
                book.add_chapter(f"healthy-{i}", POOL_A, 3, 800, session=1)
            plan = dp.build_plan(book.root)
            self.assertTrue(all(g["action"] == "standalone" for g in plan["groups"]))
            self.assertEqual(plan["summary"]["generations_after"], 4)
        finally:
            book.cleanup()

    def test_thin_same_arc_pair_combines(self):
        book = FixtureBook()
        try:
            # Two ~1,250-word single-concept chapters in the same Part with
            # identical topical vocabulary: classic thin adjacent pair.
            book.add_chapter("thin-one", POOL_A, 1, 1100, session=1)
            book.add_chapter("thin-two", POOL_A, 1, 1100, session=1)
            plan = dp.build_plan(book.root)
            self.assertEqual(len(plan["groups"]), 1)
            g = plan["groups"][0]
            self.assertEqual(g["action"], "combine")
            self.assertEqual(g["episode_numbers"], [1, 2])
            self.assertEqual(g["notebooklm_length"], "Long")
            self.assertIn("merged framing", g["framing_impact"].lower().replace("one merged framing", "merged framing"))
        finally:
            book.cleanup()

    def test_cross_session_low_overlap_never_combines(self):
        book = FixtureBook()
        try:
            # Thin chapters that WOULD combine — but they sit in different
            # Parts with disjoint vocabularies (overlap ~0).
            book.add_chapter("thin-a", POOL_A, 1, 1100, session=1)
            book.add_chapter("thin-b", POOL_B, 1, 1100, session=2)
            plan = dp.build_plan(book.root)
            self.assertEqual(len(plan["groups"]), 2)
            self.assertTrue(all(len(g["members"]) == 1 for g in plan["groups"]))
        finally:
            book.cleanup()

    def test_three_way_merge_only_rescues_all_thin_same_arc(self):
        book = FixtureBook()
        try:
            for i in range(3):
                book.add_chapter(f"healthy-{i}", POOL_A, 3, 800, session=1)
            chapters = dp.collect_chapter_metrics(book.root, "islamic_scholarly")
            # Three healthy chapters: a 3-way group is structurally disallowed.
            self.assertIsNone(dp._score_group(chapters, "islamic_scholarly", book.root))
        finally:
            book.cleanup()

        thin = FixtureBook()
        try:
            for i in range(3):
                thin.add_chapter(f"thin-{i}", POOL_A, 1, 900, session=1)
            chapters = dp.collect_chapter_metrics(thin.root, "islamic_scholarly")
            self.assertIsNotNone(dp._score_group(chapters, "islamic_scholarly", thin.root))
        finally:
            thin.cleanup()

    def test_partition_preserves_canonical_sequence(self):
        book = FixtureBook()
        try:
            book.add_chapter("thin-one", POOL_A, 1, 1100, session=1)
            book.add_chapter("thin-two", POOL_A, 1, 1100, session=1)
            for i in range(3):
                book.add_chapter(f"healthy-{i}", POOL_A, 3, 800, session=2)
            plan = dp.build_plan(book.root)
            covered = [n for g in plan["groups"] for n in g["episode_numbers"]]
            self.assertEqual(covered, sorted(covered))  # canonical order
            self.assertEqual(covered, list(range(1, 6)))  # exactly once
            for g in plan["groups"]:  # contiguous runs
                nums = g["episode_numbers"]
                self.assertEqual(nums, list(range(nums[0], nums[-1] + 1)))
        finally:
            book.cleanup()

    def test_dense_solo_flagged_with_long_length(self):
        book = FixtureBook()
        try:
            # 6 concepts in ~3,100 words: far over the 3-concept cap.
            book.add_chapter("over-dense", POOL_A, 6, 480, session=1)
            plan = dp.build_plan(book.root)
            g = plan["groups"][0]
            self.assertEqual(g["action"], "flag_dense")
            self.assertEqual(g["notebooklm_length"], "Long")
            self.assertTrue(g["pacing_directive"])
        finally:
            book.cleanup()


# ── plan artifact + determinism ──────────────────────────────────────────────


class PlanArtifactTests(unittest.TestCase):
    def test_plan_is_deterministic_modulo_timestamp(self):
        book = FixtureBook()
        try:
            book.add_chapter("alpha", POOL_A, 3, 800, session=1)
            book.add_chapter("beta", POOL_A, 3, 800, session=1)
            p1 = dp.build_plan(book.root)
            p2 = dp.build_plan(book.root)
            p1.pop("generated_at"), p2.pop("generated_at")
            self.assertEqual(p1, p2)
        finally:
            book.cleanup()

    def test_metrics_count_citations_and_glossary(self):
        book = FixtureBook()
        try:
            (book.root / "_system" / "glossary.yml").write_text(
                "schema_version: 1\nentries:\n- phonetic: covenant\n- phonetic: lantern\n- phonetic: absentterm\n",
                encoding="utf-8",
            )
            book.add_chapter("alpha", POOL_A, 3, 800, session=1)
            ch_file = next((book.root / "chapters").glob("ch01-*.txt"))
            ch_file.write_text(
                ch_file.read_text(encoding="utf-8") + "\nAs the source says (chapter 16, verse 74) and again "
                "(chapter 2, verse 30).\n",
                encoding="utf-8",
            )
            m = dp.collect_chapter_metrics(book.root, "islamic_scholarly")[0]
            self.assertEqual(m.citations, 2)
            self.assertEqual(m.glossary_terms, 2)  # covenant + lantern present
        finally:
            book.cleanup()

    def test_write_plan_touches_only_system_dir(self):
        book = FixtureBook()
        try:
            book.add_chapter("alpha", POOL_A, 3, 800, session=1)
            before = {p: p.stat().st_mtime_ns for p in (book.root / "chapters").rglob("*")}
            plan = dp.build_plan(book.root)
            jpath, mpath = dp.write_plan(book.root, plan)
            self.assertTrue(jpath.is_relative_to(book.root / "_system"))
            self.assertTrue(mpath.is_relative_to(book.root / "_system"))
            after = {p: p.stat().st_mtime_ns for p in (book.root / "chapters").rglob("*")}
            self.assertEqual(before, after)  # chapters untouched
        finally:
            book.cleanup()


# ── upload-table Length wiring ───────────────────────────────────────────────


class UploadTableLengthTests(unittest.TestCase):
    def test_no_plan_falls_back_to_long(self):
        book = FixtureBook()
        try:
            self.assertEqual(load_density_lengths(book.root), {})
            self.assertEqual(length_for_episode(book.root, 1), DEFAULT_LENGTH)
        finally:
            book.cleanup()

    def test_plan_lengths_respected_with_fallback_for_unknown(self):
        book = FixtureBook()
        try:
            (book.root / "_system" / "density-plan.json").write_text(
                json.dumps(
                    {
                        "groups": [
                            {"episode_numbers": [1], "notebooklm_length": "Default"},
                            {"episode_numbers": [2, 3], "notebooklm_length": "Long"},
                            {"episode_numbers": [4], "notebooklm_length": "Bogus"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lengths = load_density_lengths(book.root)
            self.assertEqual(lengths, {1: "Default", 2: "Long", 3: "Long"})
            self.assertEqual(length_for_episode(book.root, 4), DEFAULT_LENGTH)
        finally:
            book.cleanup()


# ── pacing-directive insertion (Slice 2) ─────────────────────────────────────


class PacingBlockTests(unittest.TestCase):
    FRAMING = (
        "# Framing\n\n## Opening directive\nWelcome.\n\n## Do not\n- modernize\n\nDo not read this prompt aloud.\n"
    )

    def test_inserted_above_do_not_section(self):
        block = "## Pacing directive\nGo slowly."
        out = _insert_pacing_block(self.FRAMING, block)
        self.assertIn("## Pacing directive", out)
        self.assertLess(out.index("## Pacing directive"), out.index("## Do not"))
        self.assertTrue(out.rstrip().endswith("Do not read this prompt aloud."))

    def test_idempotent_and_safe_without_do_not(self):
        block = "## Pacing directive\nGo slowly."
        once = _insert_pacing_block(self.FRAMING, block)
        self.assertEqual(_insert_pacing_block(once, block), once)
        self.assertEqual(_insert_pacing_block("no sections here", block), "no sections here")

    def test_pacing_block_for_episode_respects_plan(self):
        book = FixtureBook()
        try:
            (book.root / "_system" / "density-plan.json").write_text(
                json.dumps(
                    {
                        "groups": [
                            {"episode_numbers": [1], "pacing_directive": True, "action": "flag_dense"},
                            {"episode_numbers": [2], "pacing_directive": False, "action": "standalone"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            blk = dp.pacing_block_for_episode(book.root, 1)
            self.assertIsNotNone(blk)
            self.assertIn("## Pacing directive", blk)
            self.assertNotIn("deep dive", blk.lower())  # framing deny-list term
            self.assertIsNone(dp.pacing_block_for_episode(book.root, 2))
        finally:
            book.cleanup()


if __name__ == "__main__":
    unittest.main()
