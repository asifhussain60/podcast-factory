#!/usr/bin/env python3
"""Tests for the SN-7 terminus-technicus guard (K6-pre / Slice 2-fix).

Covers gemini_refine.load_protect_terms (per-book glossary.yml -> protect-list) and
gemini_refine.sn7_guard (the prompt clause), plus the _rules.R_TERMINUS_PRESERVE constant.
Pure unit tests — no Gemini/LLM calls.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import gemini_refine as gr  # noqa: E402
import _rules  # noqa: E402

_GLOSSARY = """\
# header comment ignored
entries:
  - phonetic: Ghazali
    transliteration: al-Ghazali
    arabic_script: الغزالي
  - phonetic: tawil
    transliteration: ta'wil
    arabic_script: تأويل
  - phonetic: Ghazali
    transliteration: al-Ghazali
"""


class LoadProtectTermsTests(unittest.TestCase):
    def _book_dir(self, root: Path, slug: str) -> Path:
        d = root / "content" / "drafts" / "books" / slug / "_system"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_reads_phonetic_and_transliteration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (self._book_dir(root, "demo") / "glossary.yml").write_text(_GLOSSARY, encoding="utf-8")
            old = gr.REPO_ROOT
            try:
                gr.REPO_ROOT = root
                terms = gr.load_protect_terms("demo")
            finally:
                gr.REPO_ROOT = old
            self.assertIn("Ghazali", terms)
            self.assertIn("al-Ghazali", terms)
            self.assertIn("tawil", terms)
            self.assertIn("ta'wil", terms)

    def test_dedupes_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (self._book_dir(root, "demo") / "glossary.yml").write_text(_GLOSSARY, encoding="utf-8")
            old = gr.REPO_ROOT
            try:
                gr.REPO_ROOT = root
                terms = gr.load_protect_terms("demo")
            finally:
                gr.REPO_ROOT = old
            # "Ghazali" appears twice in the glossary -> one entry in the protect-list
            self.assertEqual(sum(1 for t in terms if t.lower() == "ghazali"), 1)

    def test_missing_glossary_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = gr.REPO_ROOT
            try:
                gr.REPO_ROOT = Path(tmp)
                self.assertEqual(gr.load_protect_terms("no-such-book"), [])
            finally:
                gr.REPO_ROOT = old


class Sn7GuardTests(unittest.TestCase):
    def test_guard_states_phonetic_and_first_use_gloss(self):
        g = gr.sn7_guard(["tawil"])
        self.assertIn("PHONETIC", g)
        self.assertIn("FIRST occurrence", g)
        self.assertIn("R_TERMINUS_PRESERVE", g)

    def test_guard_forbids_english_only_reduction(self):
        g = gr.sn7_guard(["tawil"])
        # the forbidden flattening is named explicitly
        self.assertIn("FORBIDDEN", g)
        self.assertIn("esoteric interpretation", g)

    def test_guard_enumerates_known_terms_when_present(self):
        g = gr.sn7_guard(["tawil", "zuhd"])
        self.assertIn("tawil", g)
        self.assertIn("zuhd", g)
        self.assertIn("Known terms for this book", g)

    def test_guard_degrades_gracefully_without_terms(self):
        g = gr.sn7_guard([])
        self.assertNotIn("Known terms for this book", g)
        # still carries the general rule
        self.assertIn("TERMINUS-TECHNICUS GUARD", g)

    def test_guard_is_orthogonal_to_phonetics_out(self):
        g = gr.sn7_guard([])
        self.assertIn("SCRIPT", g)  # Arabic script itself is stripped; phonetic carries the term


class RulesConstantTests(unittest.TestCase):
    def test_r_terminus_preserve_present_and_true(self):
        self.assertTrue(hasattr(_rules, "R_TERMINUS_PRESERVE"))
        self.assertIs(_rules.R_TERMINUS_PRESERVE, True)


if __name__ == "__main__":
    unittest.main()
