#!/usr/bin/env python3
"""Tests for Wave L-4 — Quranic etymology weaving.

Covers augmenter._fetch_matching_etymology (conservative term match, 3-cap,
phonetic-required) and _build_etymology_block (spoken form, no Arabic script,
varied-phrasing header). Uses a throwaway DB seeded with etymology atoms — no
Gemini, no live writes to the canonical knowledge.db.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))

import _db  # noqa: E402
import augmenter  # noqa: E402

_ARABIC = re.compile(r"[؀-ۿ]")


def _seed_etymology(conn) -> None:
    atoms = [
        ("etymology:ans", {
            "root_transliteration": "ANS", "root_arabic": "أنيس",
            "root_phonetic": "AH-nas", "meaning_en": "companion, closeness",
            "derivatives": [
                {"term": "INSAAN", "arabic": "إنسان", "phonetic": "in-SAAN",
                 "meaning_en": "human"},
            ],
        }),
        ("etymology:amn", {
            "root_transliteration": "AMN", "root_arabic": "أمن",
            "root_phonetic": "AH-man", "meaning_en": "safety, peace",
            "derivatives": [
                {"term": "IMAN", "arabic": "إيمان", "phonetic": "ee-MAAN",
                 "meaning_en": "faith"},
            ],
        }),
        ("etymology:ilm", {
            "root_transliteration": "ILM", "root_arabic": "علم",
            "root_phonetic": "ilm", "meaning_en": "a sign, to know",
            "derivatives": [
                {"term": "ALAM", "arabic": "عالم", "phonetic": "AA-lam",
                 "meaning_en": "world"},
            ],
        }),
        ("etymology:nophon", {  # missing root_phonetic — must be skipped
            "root_transliteration": "TAQWA", "root_arabic": "تقوى",
            "root_phonetic": "", "meaning_en": "to guard",
            "derivatives": [{"term": "TAQWA", "phonetic": "", "meaning_en": "piety"}],
        }),
    ]
    for aid, body in atoms:
        conn.execute(
            "INSERT INTO atoms (id, type, body, tradition) VALUES (?, 'etymology', ?, 'universal')",
            (aid, json.dumps(body, ensure_ascii=False)),
        )
    conn.commit()


class TestEtymologyWeaving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()) / "etym.db"
        _db._reset_connection()
        conn = _db.get_connection(db_path=cls.tmp)
        _db.run_migrations(db_path=cls.tmp)
        _seed_etymology(conn)

    @classmethod
    def tearDownClass(cls):
        _db._reset_connection()

    def test_matches_only_present_terms(self):
        text = "The discussion of iman and the nature of the insaan was central."
        got = {a["id"] for a in augmenter._fetch_matching_etymology(text)}
        self.assertIn("etymology:amn", got)   # 'iman' present
        self.assertIn("etymology:ans", got)   # 'insaan' present
        self.assertNotIn("etymology:ilm", got)  # 'alam'/'ilm' absent

    def test_skips_atoms_without_phonetic(self):
        text = "He spoke of taqwa at length."
        got = {a["id"] for a in augmenter._fetch_matching_etymology(text)}
        self.assertNotIn("etymology:nophon", got)

    def test_caps_at_three(self):
        text = "iman, insaan, alam, ilm — all of these terms appeared together."
        got = augmenter._fetch_matching_etymology(text, max_etymology=3)
        self.assertLessEqual(len(got), 3)

    def test_block_has_no_arabic_script(self):
        text = "The nature of iman and the insaan."
        atoms = augmenter._fetch_matching_etymology(text)
        block = augmenter._build_etymology_block(atoms)
        self.assertFalse(_ARABIC.search(block), "Arabic script leaked into etymology block")

    def test_block_uses_spoken_form_and_varies_phrasing_header(self):
        text = "The meaning of iman."
        atoms = augmenter._fetch_matching_etymology(text)
        block = augmenter._build_etymology_block(atoms)
        self.assertIn("ee-MAAN", block)          # derivative spoken form present
        self.assertIn("AH-man", block)           # root spoken form present
        self.assertIn("NEVER spell out Arabic", block)  # discipline instruction
        self.assertIn("VARY your phrasing", block)

    def test_empty_when_no_match(self):
        text = "A passage with no Arabic terms whatsoever."
        self.assertEqual(augmenter._fetch_matching_etymology(text), [])
        self.assertEqual(augmenter._build_etymology_block([]), "")


if __name__ == "__main__":
    unittest.main()
