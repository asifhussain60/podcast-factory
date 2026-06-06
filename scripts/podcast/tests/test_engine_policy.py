"""tests/test_engine_policy.py — unit tests for the central engine-selection policy.

Tests assert the locked hierarchy (Asif, 2026-06-06):
  Tier 1 — Claude Max ($0 marginal): default for all reasoning + text generation
  Tier 2 — Azure (committed services): OCR, bulk-translate, speech, language NLP, DALL-E
  Tier 3 — Gemini (pay-as-you-go): tasks where Gemini genuinely wins today
  Exception — Anthropic SDK: windowed 0b/0c parallelism the CLI cannot do
"""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _engine as E


class TestEngineConstants(unittest.TestCase):
    def test_engine_constants_distinct(self):
        engines = [E.ENGINE_CLAUDE_MAX, E.ENGINE_AZURE, E.ENGINE_GEMINI, E.ENGINE_ANTHROPIC_SDK]
        self.assertEqual(len(engines), len(set(engines)), "Engine constants must be distinct")

    def test_all_tasks_in_policy(self):
        """Every TASK_* constant must have an entry in _POLICY (no silent gaps)."""
        task_consts = {v for k, v in vars(E).items() if k.startswith("TASK_")}
        policy_keys = set(E._POLICY)
        missing = task_consts - policy_keys
        self.assertFalse(missing, f"TASK_* constants with no policy entry: {missing}")

    def test_all_rationale_covered(self):
        """Every task in _POLICY should have a rationale entry."""
        missing = set(E._POLICY) - set(E._RATIONALE)
        self.assertFalse(missing, f"Tasks with no rationale: {missing}")


class TestTier1ClaudeMax(unittest.TestCase):
    """All reasoning / text generation tasks default to Claude Max (tier 1, $0 marginal)."""

    def test_literary_translation(self):
        self.assertEqual(E.select_engine(E.TASK_TRANSLATE_LITERARY), E.ENGINE_CLAUDE_MAX)

    def test_chapter_design(self):
        self.assertEqual(E.select_engine(E.TASK_CHAPTER_DESIGN), E.ENGINE_CLAUDE_MAX)

    def test_enrich(self):
        self.assertEqual(E.select_engine(E.TASK_ENRICH), E.ENGINE_CLAUDE_MAX)

    def test_author(self):
        self.assertEqual(E.select_engine(E.TASK_AUTHOR), E.ENGINE_CLAUDE_MAX)

    def test_image_prompt_is_max_not_gemini(self):
        """Storyboard / slide-manifest text generation was swapped from Gemini to Max (Max-first)."""
        self.assertEqual(E.select_engine(E.TASK_IMAGE_PROMPT), E.ENGINE_CLAUDE_MAX)

    def test_augment(self):
        self.assertEqual(E.select_engine(E.TASK_AUGMENT), E.ENGINE_CLAUDE_MAX)


class TestTier2Azure(unittest.TestCase):
    """Attached Azure committed services handle their specific jobs."""

    def test_ocr(self):
        self.assertEqual(E.select_engine(E.TASK_OCR), E.ENGINE_AZURE)

    def test_translate_bulk(self):
        self.assertEqual(E.select_engine(E.TASK_TRANSLATE_BULK), E.ENGINE_AZURE)

    def test_transcribe(self):
        self.assertEqual(E.select_engine(E.TASK_TRANSCRIBE), E.ENGINE_AZURE)

    def test_tts(self):
        self.assertEqual(E.select_engine(E.TASK_TTS), E.ENGINE_AZURE)

    def test_ner_is_azure_language(self):
        self.assertEqual(E.select_engine(E.TASK_NER), E.ENGINE_AZURE)

    def test_key_phrases_is_azure_language(self):
        self.assertEqual(E.select_engine(E.TASK_KEY_PHRASES), E.ENGINE_AZURE)

    def test_sentiment_is_azure_language(self):
        self.assertEqual(E.select_engine(E.TASK_SENTIMENT), E.ENGINE_AZURE)

    def test_image_gen_is_gemini(self):
        """Image generation stays on Gemini: Azure DALL-E 3 deprecated Mar 2026, gpt-image-1 not yet
        available in eastus. Route is through _engine so the swap to Azure is one-line when it lands."""
        self.assertEqual(E.select_engine(E.TASK_IMAGE_GEN), E.ENGINE_GEMINI)


class TestTier3Gemini(unittest.TestCase):
    """Gemini remains for tasks where it genuinely wins today."""

    def test_revoice(self):
        self.assertEqual(E.select_engine(E.TASK_REVOICE), E.ENGINE_GEMINI)

    def test_denoise(self):
        self.assertEqual(E.select_engine(E.TASK_DENOISE), E.ENGINE_GEMINI)

    def test_audit(self):
        self.assertEqual(E.select_engine(E.TASK_AUDIT), E.ENGINE_GEMINI)

    def test_reconcile(self):
        self.assertEqual(E.select_engine(E.TASK_RECONCILE), E.ENGINE_GEMINI)

    def test_review_helper(self):
        self.assertEqual(E.select_engine(E.TASK_REVIEW_HELPER), E.ENGINE_GEMINI)


class TestRegisteredException(unittest.TestCase):
    """The Anthropic SDK exception: windowed parallelism the CLI cannot do."""

    def test_refine_windowed(self):
        self.assertEqual(E.select_engine(E.TASK_REFINE_WINDOWED), E.ENGINE_ANTHROPIC_SDK)

    def test_sdk_tier_is_exception(self):
        self.assertEqual(E.engine_tier(E.ENGINE_ANTHROPIC_SDK), "exception")


class TestOverrides(unittest.TestCase):
    """Per-task overrides always win over the default policy."""

    def test_override_max_to_gemini(self):
        # e.g. a book pinning Gemini for a task it does better
        result = E.select_engine(E.TASK_REVOICE, override=E.ENGINE_GEMINI)
        self.assertEqual(result, E.ENGINE_GEMINI)

    def test_override_gemini_to_azure(self):
        result = E.select_engine(E.TASK_IMAGE_GEN, override=E.ENGINE_AZURE)
        self.assertEqual(result, E.ENGINE_AZURE)

    def test_override_to_claude_max(self):
        result = E.select_engine(E.TASK_AUDIT, override=E.ENGINE_CLAUDE_MAX)
        self.assertEqual(result, E.ENGINE_CLAUDE_MAX)

    def test_invalid_override_raises(self):
        with self.assertRaises(ValueError):
            E.select_engine(E.TASK_AUTHOR, override="bad_engine_name")


class TestErrorHandling(unittest.TestCase):
    """Unknown tasks raise ValueError — typos cannot silently route to the wrong engine."""

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            E.select_engine("unknown_task")

    def test_empty_task_raises(self):
        with self.assertRaises(ValueError):
            E.select_engine("")

    def test_misspelled_task_raises(self):
        with self.assertRaises(ValueError):
            E.select_engine("image_gen_typo")

    def test_error_message_mentions_policy(self):
        try:
            E.select_engine("not_a_real_task")
        except ValueError as e:
            self.assertIn("_engine.py", str(e))
            self.assertIn("_POLICY", str(e))


class TestHelpers(unittest.TestCase):
    def test_rationale_returns_string(self):
        r = E.rationale(E.TASK_IMAGE_GEN)
        self.assertIsInstance(r, str)
        self.assertIn("DALL-E", r)

    def test_rationale_unknown_task_returns_fallback(self):
        r = E.rationale("totally_unknown")
        self.assertIn("no rationale", r)

    def test_engine_tier_known(self):
        self.assertEqual(E.engine_tier(E.ENGINE_CLAUDE_MAX), 1)
        self.assertEqual(E.engine_tier(E.ENGINE_AZURE), 2)
        self.assertEqual(E.engine_tier(E.ENGINE_GEMINI), 3)

    def test_engine_tier_unknown_raises(self):
        with self.assertRaises(ValueError):
            E.engine_tier("phantom_engine")

    def test_all_tasks_is_sorted_list(self):
        tasks = E.all_tasks()
        self.assertIsInstance(tasks, list)
        self.assertEqual(tasks, sorted(tasks))
        self.assertGreater(len(tasks), 15, "Expected at least 15+ tasks in the policy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
