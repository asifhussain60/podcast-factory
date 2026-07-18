#!/usr/bin/env python3
"""Regression tests for the root denoise contract.

The denoise stage must strip non-teaching front matter and book-object apparatus
while preserving Arabic script for the downstream Arabic/pronunciation review.
These tests inspect the prompt/rule contract only; they make no network calls.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _rules
import full_book_denoise as fbd
import gemini_refine as gr


class DenoiseContractTests(unittest.TestCase):
    def test_authorial_apparatus_directive_strips_front_matter(self):
        directive = _rules.R_NOISE_APPARATUS_DIRECTIVE.lower()
        for phrase in (
            "who should read",
            "prefaces",
            "descriptions of the book",
            "author biography",
            "chain of narrations",
            "permission-to-read",
        ):
            self.assertIn(phrase, directive)

    def test_authorial_apparatus_has_frontmatter_patterns(self):
        labels = {label for _pattern, label in _rules.R_NOISE_APPARATUS_PATTERNS}
        self.assertIn("NZ-FRONTMATTER", labels)

    def test_preserve_arabic_directive_is_in_root_denoise_prompts(self):
        self.assertIn("R-PRESERVE-ARABIC-SOURCE", gr.DENOISE_SYS)
        self.assertIn("Arabic script", gr.DENOISE_SYS)
        prompts = fbd.build_system_prompts("missing-slug-ok")
        for source in ("arabic", "english", "scholarly"):
            self.assertIn("R-PRESERVE-ARABIC-SOURCE", prompts[source])
            self.assertIn("PRESERVE Arabic script", prompts[source])

    def test_english_full_book_prompt_no_longer_removes_arabic_script(self):
        prompts = fbd.build_system_prompts("missing-slug-ok")
        self.assertNotIn("Arabic script inserted for comparison", prompts["english"])
        self.assertIn("Arabic\nscript attached to authorial terms", prompts["english"])

    def test_terminus_guard_preserves_script_instead_of_stripping_it(self):
        guard = gr.sn7_guard(["tawil"])
        self.assertIn("Arabic SCRIPT when present", guard)
        self.assertNotIn("Arabic SCRIPT itself is stripped", guard)

    def test_version_bumped_for_noise_taxonomy_change(self):
        self.assertEqual(_rules.NOISE_AUDITOR_VERSION, "1.1")
        self.assertEqual(_rules.CHALLENGER_VERSION, "2.6")


if __name__ == "__main__":
    unittest.main()
