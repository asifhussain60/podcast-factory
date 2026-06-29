"""tests/test_augment_registry.py — Unit tests for _augment_registry.py.

Tests the profile-keyed registry + need-detector without any LLM calls.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _augment_registry as R


# ─── Registry coverage ────────────────────────────────────────────────────────

class TestRegistryCoverage:
    def test_all_strategies_registered(self):
        expected = {R.STRATEGY_ISLAMIC, R.STRATEGY_TECHNICAL, R.STRATEGY_FICTION,
                    R.STRATEGY_GUIDES, R.STRATEGY_SKIP}
        assert set(R.all_strategies()) == expected

    def test_every_category_maps_to_a_strategy(self):
        for cat, strat_name in R._CATEGORY_TO_STRATEGY.items():
            assert strat_name in R._REGISTRY, f"category {cat!r} maps to unknown strategy {strat_name!r}"

    def test_every_profile_maps_to_a_strategy(self):
        for prof, strat_name in R._PROFILE_TO_STRATEGY.items():
            assert strat_name in R._REGISTRY, f"profile {prof!r} maps to unknown strategy {strat_name!r}"

    def test_placement_modes_are_valid(self):
        valid = {R.PLACEMENT_INLINE, R.PLACEMENT_SIDECAR}
        for name, strat in R._REGISTRY.items():
            assert strat.placement in valid, f"strategy {name!r} has invalid placement {strat.placement!r}"


# ─── strategy_for_category ────────────────────────────────────────────────────

class TestStrategyForCategory:
    def test_books_is_islamic(self):
        assert R.strategy_for_category("books").name == R.STRATEGY_ISLAMIC

    def test_letters_is_islamic(self):
        assert R.strategy_for_category("letters").name == R.STRATEGY_ISLAMIC

    def test_explainers_is_technical(self):
        assert R.strategy_for_category("explainers").name == R.STRATEGY_TECHNICAL

    def test_fiction_is_fiction(self):
        assert R.strategy_for_category("fiction").name == R.STRATEGY_FICTION

    def test_novels_is_fiction(self):
        assert R.strategy_for_category("novels").name == R.STRATEGY_FICTION

    def test_sites_is_skip(self):
        assert R.strategy_for_category("sites").name == R.STRATEGY_SKIP

    def test_guides_is_guides(self):
        assert R.strategy_for_category("guides").name == R.STRATEGY_GUIDES

    def test_unknown_category_is_skip(self):
        assert R.strategy_for_category("unknown-xyz").name == R.STRATEGY_SKIP

    def test_case_insensitive(self):
        assert R.strategy_for_category("BOOKS").name == R.STRATEGY_ISLAMIC
        assert R.strategy_for_category("Fiction").name == R.STRATEGY_FICTION


# ─── strategy_for_profile ─────────────────────────────────────────────────────

class TestStrategyForProfile:
    def test_islamic_scholarly(self):
        assert R.strategy_for_profile("islamic_scholarly").name == R.STRATEGY_ISLAMIC

    def test_technical(self):
        assert R.strategy_for_profile("technical").name == R.STRATEGY_TECHNICAL

    def test_fiction(self):
        assert R.strategy_for_profile("fiction").name == R.STRATEGY_FICTION

    def test_guides(self):
        assert R.strategy_for_profile("guides").name == R.STRATEGY_GUIDES

    def test_unknown_profile_is_skip(self):
        assert R.strategy_for_profile("unknown-xyz").name == R.STRATEGY_SKIP


# ─── needs_augmentation routing ───────────────────────────────────────────────

class TestNeedsAugmentationRouting:
    def test_requires_category_or_profile(self):
        with pytest.raises(ValueError):
            R.needs_augmentation("text")

    def test_skip_strategy_always_false(self):
        long_text = "This product must always be configured. " * 50
        assert R.needs_augmentation(long_text, category="sites") is False

    def test_fiction_category_routes_to_fiction_detector(self):
        # Text with many proper nouns + mythological terms → True
        dense = (
            "The Great Sage Sun Wukong and the Jade Emperor clashed in the Celestial Palace. "
            "The Dragon King fled to his underwater kingdom. The Heavenly Army marched. "
            "Guanyin Bodhisattva descended from the Western Heaven with the Iron Fan. "
            "The Demon King of Confusion summoned his celestial dragon generals. "
            "Zhu Bajie and Sha Wujing carried the sacred scriptures through the mountains. "
        ) * 3
        assert R.needs_augmentation(dense, category="fiction") is True

    def test_plain_fiction_text_no_augmentation(self):
        # Plain prose with no culture density
        plain = "He walked down the road and saw a house. She opened the door. They spoke." * 20
        assert R.needs_augmentation(plain, category="fiction") is False

    def test_category_and_profile_both_work(self):
        text = "He walked down the road." * 20
        r1 = R.needs_augmentation(text, category="fiction")
        r2 = R.needs_augmentation(text, content_profile="fiction")
        assert r1 == r2


# ─── Islamic need-detector ────────────────────────────────────────────────────

class TestIslamicNeedDetector:
    def test_no_quotes_needs_augmentation(self):
        # No quotations → doctrinal claims without citations → needs enrichment
        text = "The soul must strive for purification through remembrance of God. " * 20
        assert R._needs_islamic(text) is True

    def test_quoted_text_with_citation_does_not_need(self):
        text = (
            'As the tradition states: "Whoever knows himself knows his Lord." '
            "(Surah 59:19; also narrated by Ibn Abbas) " * 10
        )
        assert R._needs_islamic(text) is False

    def test_quoted_text_without_citation_needs_augmentation(self):
        text = (
            '"Knowledge is the foundation of all worship." '
            "This teaching is central to the spiritual path. " * 10
        )
        assert R._needs_islamic(text) is True


# ─── Technical need-detector ─────────────────────────────────────────────────

class TestTechnicalNeedDetector:
    def test_abstract_heavy_needs_augmentation(self):
        text = (
            "The tool typically helps developers. It usually enables faster workflows. "
            "It can often improve code quality. It may sometimes handle edge cases. " * 10
        )
        assert R._needs_technical(text) is True

    def test_concrete_heavy_does_not_need(self):
        text = (
            "Run `npm install`. ```bash\nnpm run dev\n``` "
            "Available since v2.1.59+. Version 3.0 adds the `--watch` flag. "
            "```python\nimport foo\nfoo.run()\n```\n"
        ) * 5
        assert R._needs_technical(text) is False


# ─── Fiction need-detector ────────────────────────────────────────────────────

class TestFictionNeedDetector:
    def test_culture_dense_needs_augmentation(self):
        text = (
            "Sun Wukong, the Great Sage, fought the Jade Emperor's celestial army. "
            "The Dragon King of the Eastern Sea trembled before the divine spirit. "
            "The Monkey King transformed into seventy-two different shapes. "
            "The Buddha's immortal palm descended from the heavenly palace. "
            "General Erlang and his divine dog pursued the demon king. "
        ) * 4
        assert R._needs_fiction(text) is True

    def test_sparse_text_does_not_need(self):
        text = "She walked along the river. The water was cold. He waited." * 30
        assert R._needs_fiction(text) is False


# ─── Guides need-detector ─────────────────────────────────────────────────────

class TestGuidesNeedDetector:
    def test_absolute_unsourced_needs_augmentation(self):
        text = (
            "You must always back up your data. Never skip this step. "
            "This will always work in production. Every developer needs this. " * 10
        )
        assert R._needs_guides(text) is True

    def test_sourced_claims_do_not_need(self):
        text = (
            "According to the study, 80% of teams report success. "
            "Research found that structured backups reduce data loss by 70%. "
            "Evidence shows that code review catches 60% of bugs. "
            "Data from the 2024 survey cited three key practices. " * 5
        )
        assert R._needs_guides(text) is False


# ─── Placement modes ──────────────────────────────────────────────────────────

class TestPlacementModes:
    def test_fiction_is_sidecar(self):
        assert R.strategy_for_category("fiction").placement == R.PLACEMENT_SIDECAR
        assert R.strategy_for_category("novels").placement == R.PLACEMENT_SIDECAR

    def test_islamic_is_inline(self):
        assert R.strategy_for_category("books").placement == R.PLACEMENT_INLINE

    def test_technical_is_inline(self):
        assert R.strategy_for_category("explainers").placement == R.PLACEMENT_INLINE

    def test_guides_is_inline(self):
        assert R.strategy_for_category("guides").placement == R.PLACEMENT_INLINE
