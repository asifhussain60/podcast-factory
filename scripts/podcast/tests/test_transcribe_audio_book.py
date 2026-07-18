#!/usr/bin/env python3
"""Stage-4 regression — deterministic transcription-quality helpers in
transcribe_audio_book.py (P2 normalization, P4 block-dup, P5 short-guard,
P7 native-script leak). These are pure functions: no Gemini/credentials needed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import transcribe_audio_book as T


class NormalizeTranscriptTests(unittest.TestCase):
    """P2 — typographic folding + curated whole-word garble map, idempotent."""

    def test_typographic_fold_to_ascii(self):
        out, n = T.normalize_transcript("‘quote’ “double” en–dash em—dash")
        self.assertNotIn("‘", out)
        self.assertNotIn("“", out)
        self.assertNotIn("–", out)
        self.assertNotIn("—", out)
        self.assertEqual(out, "'quote' \"double\" en-dash em-dash")
        self.assertGreater(n, 0)

    def test_garble_map_whole_word_only(self):
        out, _ = T.normalize_transcript("recited in Mumbai today")
        self.assertIn("Munba'ith", out)
        # Must NOT corrupt a larger word that merely contains the token.
        out2, _ = T.normalize_transcript("a Mumbaikar spoke")
        self.assertIn("Mumbaikar", out2)
        self.assertNotIn("Munba'ith", out2)

    def test_idempotent(self):
        once, _ = T.normalize_transcript("‘Mumbai’ — the term")
        twice, _ = T.normalize_transcript(once)
        self.assertEqual(once, twice)


class BlockDupTests(unittest.TestCase):
    """P4 — boundary-agnostic verbatim block-repetition detection."""

    def test_clean_text_zero(self):
        clean = " ".join(f"u{i}" for i in range(300))
        self.assertEqual(T._block_dup_ratio(clean), 0.0)

    def test_repeated_large_block_flagged(self):
        block = " ".join(f"w{i}" for i in range(50))  # > window (40 words)
        clean = " ".join(f"u{i}" for i in range(200))
        txt = f"{clean} {block} interstitial content B {block} {clean}"
        self.assertGreater(T._block_dup_ratio(txt), T.BLOCK_DUP_LOOP_THRESHOLD)

    def test_short_refrain_not_flagged(self):
        refrain = "praise be to god"  # << window; a legitimate refrain
        txt = " ".join([refrain] * 10 + [f"x{i}" for i in range(300)])
        self.assertEqual(T._block_dup_ratio(txt), 0.0)


class ShortTranscriptGuardTests(unittest.TestCase):
    """P5 — empty / implausibly-short transcript detection."""

    def test_zero_words_always_flagged(self):
        self.assertTrue(T._is_empty_or_short(0, 10))

    def test_real_audio_near_empty_flagged(self):
        self.assertTrue(T._is_empty_or_short(10, 2_500_000))

    def test_dense_audio_not_flagged(self):
        self.assertFalse(T._is_empty_or_short(5000, 2_500_000))

    def test_tiny_clip_short_ok(self):
        # below the size floor, a short transcript is plausible
        self.assertFalse(T._is_empty_or_short(30, 1_000))


class NativeScriptLeakTests(unittest.TestCase):
    """P7 — detect (not auto-fix) native-script tokens leaked into romanized prose."""

    def test_clean_english(self):
        self.assertEqual(T._native_script_tokens("clean english only here"), [])

    def test_arabic_and_devanagari_leak(self):
        leaked = T._native_script_tokens("hello البعث world अरे there")
        self.assertEqual(len(leaked), 2)


if __name__ == "__main__":
    unittest.main()
