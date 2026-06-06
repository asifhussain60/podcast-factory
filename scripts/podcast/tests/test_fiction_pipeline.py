"""
Tests for the Wave-Fiction pipeline wiring (Journey to the West).

Covers the prerequisite customizations that make a non-Islamic, non-Arabic novel
flow through the pipeline correctly:
  - 0b refine routes fiction to the narrative prompt (not Arabic-scholarly).
  - 0c phonetics + 0e enrichment SKIP cleanly for fiction.
  - 0d consolidation flag is driven by content_profile / episode_planning_mode.
  - scenic video style is config-driven (no hardcoded Islamic border).
  - the cost estimator reuses _cost_ledger rate constants (no duplicated prices).
  - the Chinese Gutenberg parser numbers chapters by sequence (robust to the
    edition's mixed numeral convention).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_book(tmp: Path, **cfg) -> Path:
    book = tmp / "book"
    (book / "_system").mkdir(parents=True)
    import yaml
    (book / "_system" / "series-config.yaml").write_text(yaml.dump(cfg))
    return book


class TestPhaseGating(unittest.TestCase):
    def test_0e_skips_for_fiction(self):
        from _authoring._enrichment import author_phase_0e
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction")
            msg = author_phase_0e(book, log=lambda *a, **k: None, category="books")
            self.assertIn("fiction", msg.lower())
            self.assertIn("skip", msg.lower())

    def test_0c_skips_for_fiction(self):
        from _authoring._refine import author_phase_0c
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction")
            msg = author_phase_0c(book, log=lambda *a, **k: None, category="books")
            self.assertIn("skip", msg.lower())

    def test_0e_still_runs_for_islamic_books(self):
        # An islamic_scholarly book (category=books) must NOT hit the fiction skip;
        # it should proceed past the gate and fail only on missing chapters.
        from _authoring._enrichment import author_phase_0e
        from _authoring._core import AuthoringError
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="islamic_scholarly")
            with self.assertRaises(AuthoringError):  # no chapters/ to enrich
                author_phase_0e(book, log=lambda *a, **k: None, category="books")


class TestRefinePromptVariants(unittest.TestCase):
    def test_narrative_prompt_has_no_arabic_preservation(self):
        from _authoring._refine import (
            build_phase_0b_window_prompt_narrative,
            build_phase_0b_window_prompt,
        )
        narr = build_phase_0b_window_prompt_narrative("slug", 1, 3, Path("i"), Path("o"))
        scholarly = build_phase_0b_window_prompt("slug", 1, 3, Path("i"), Path("o"))
        self.assertNotIn("Arabic-derived term", narr)
        self.assertIn("narrative", narr.lower())
        # The scholarly prompt DOES preserve Arabic — confirms the two are distinct.
        self.assertIn("Arabic", scholarly)


class TestConsolidationFlag(unittest.TestCase):
    def test_fiction_triggers_consolidation(self):
        from _authoring._chapter_design import _read_profile_and_planning
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction",
                              episode_planning_mode="chronological")
            profile, planning = _read_profile_and_planning(book)
            self.assertEqual(profile, "fiction")
            self.assertEqual(planning, "chronological")

    def test_default_book_does_not_consolidate(self):
        from _authoring._chapter_design import _read_profile_and_planning
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "book"
            (book / "_system").mkdir(parents=True)
            profile, planning = _read_profile_and_planning(book)
            self.assertEqual(profile, "islamic_scholarly")
            self.assertEqual(planning, "")


class TestScenicStyleConfigDriven(unittest.TestCase):
    def test_scenic_style_reads_config_override(self):
        import generate_video_layer as gv
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction",
                              scenic_style="Ming-dynasty ink-and-color shan-shui landscape.")
            self.assertIn("Ming-dynasty", gv._read_scenic_style(book))

    def test_scenic_style_default_has_no_islamic_border(self):
        import generate_video_layer as gv
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction")
            style = gv._read_scenic_style(book)
            self.assertNotIn("Islamic", style)
            self.assertNotIn("scholarly", style.lower())


class TestCostEstimatorSingleSourceOfTruth(unittest.TestCase):
    def test_estimator_reuses_ledger_rate_constants(self):
        # The estimator MUST import live rate tables from _cost_ledger — never
        # re-hardcode prices. Assert object identity.
        import estimate_cost
        import _cost_ledger
        self.assertIs(estimate_cost.GEMINI_PRICING_USD, _cost_ledger.GEMINI_PRICING_USD)
        self.assertIs(estimate_cost.AZURE_PRICING_USD, _cost_ledger.AZURE_PRICING_USD)
        self.assertIs(estimate_cost.PRICING_USD_PER_MILLION_TOKENS,
                      _cost_ledger.PRICING_USD_PER_MILLION_TOKENS)

    def test_estimate_separates_notional_from_real(self):
        import estimate_cost
        with tempfile.TemporaryDirectory() as tmp:
            book = _make_book(Path(tmp), content_profile="fiction",
                              source_language="zh-Hant", enable_video=True)
            est = estimate_cost.estimate(book, episodes=12)
            self.assertIn("notional_max_total_usd", est)
            self.assertIn("real_metered_total_usd", est)
            # Fiction with video → real spend is Gemini images (> 0); notional > 0.
            self.assertGreater(est["real_metered_total_usd"], 0)
            self.assertGreater(est["notional_max_total_usd"], 0)


class TestChineseGutenbergParser(unittest.TestCase):
    def test_sequence_numbering_and_mixed_numerals(self):
        from ingest_gutenberg_zh import parse_chapters
        # Two chapters using INCONSISTENT numerals: standard 一 then positional ○.
        html = (
            "*** START OF THE PROJECT GUTENBERG EBOOK ***"
            '<p>第一回　Opening</p><p>body one</p>'
            '<p>第一○回　Tenth</p><p>body ten</p>'
            "*** END OF THE PROJECT GUTENBERG EBOOK ***"
        )
        chs = parse_chapters(html)
        self.assertEqual([c["num"] for c in chs], [1, 2])  # sequence, not 1 then 10
        self.assertEqual(chs[1]["label"], "一○")           # printed numeral kept
        self.assertEqual(chs[0]["title"], "Opening")


if __name__ == "__main__":
    unittest.main()
