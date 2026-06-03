#!/usr/bin/env python3
"""Tests for Wave L-6 — Category W (augmentation quality) challenger checks.

Covers _augmentation.py: W3 (etymology cap / spoken-form / no-Arabic), W4 (content
-level leak), W5 (fabricated atom), W6 (cross-chapter repeat), and the revert_block
auto-revert helper. Throwaway DB + temp book dir; no Gemini, no canonical-DB writes.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _db  # noqa: E402
import _augmentation as aug  # noqa: E402

_ETYM_HEADER = "[ETYMOLOGY — OPTIONAL ROOT-INSIGHTS — weave AT MOST 3]"


def _etym_block(n: int, *, arabic: bool = False, spoken: bool = True) -> str:
    lines = [_ETYM_HEADER, ""]
    for i in range(n):
        sp = ' (spoken "ee-MAAN")' if spoken else ""
        ar = " إيمان" if arabic else ""
        lines.append(f'- When the word "faith"{sp} arises, its root is AMN{ar}, meaning "peace".')
    return "\n".join(lines)


class TestW3Etymology(unittest.TestCase):
    def test_within_cap_clean(self):
        self.assertEqual(aug.check_w3_etymology(_etym_block(3)), [])

    def test_over_cap_flags(self):
        ids = [f.signature for f in aug.check_w3_etymology(_etym_block(4))]
        self.assertIn("etymology-over-cap", ids)

    def test_arabic_script_flags(self):
        ids = [f.signature for f in aug.check_w3_etymology(_etym_block(1, arabic=True))]
        self.assertIn("etymology-arabic-script", ids)

    def test_missing_spoken_form_flags(self):
        ids = [f.signature for f in aug.check_w3_etymology(_etym_block(1, spoken=False))]
        self.assertIn("etymology-no-spoken-form", ids)

    def test_no_block_no_findings(self):
        self.assertEqual(aug.check_w3_etymology("Just plain episode text."), [])


class TestW4W5W6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()) / "w.db"
        _db._reset_connection()
        conn = _db.get_connection(db_path=cls.tmp)
        _db.run_migrations(db_path=cls.tmp)
        conn.execute("INSERT INTO atoms (id,type,body,tradition,content_level) "
                     "VALUES ('doctrine:eso','doctrine','{}','universal','taveel')")
        conn.execute("INSERT INTO atoms (id,type,body,tradition,content_level) "
                     "VALUES ('doctrine:real','doctrine','{}','universal','haqaiq')")
        conn.execute("INSERT INTO atoms (id,type,body,tradition,content_level) "
                     "VALUES ('term:x','term','{}','universal',NULL)")
        conn.commit()

    @classmethod
    def tearDownClass(cls):
        _db._reset_connection()

    def _book(self, *, level: str, episodes: dict) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / "_system").mkdir(parents=True)
        (d / "meta.yml").write_text(f"content_level: {level}\n", encoding="utf-8")
        (d / "_system" / "episode-augment-ledger.json").write_text(
            json.dumps({"episodes": episodes}), encoding="utf-8")
        return d

    def test_w4_content_level_leak(self):
        book = self._book(level="taveel",
                          episodes={"ch01": {"atoms_injected": ["doctrine:real"]}})
        f = aug.check_w4_w5_content_and_existence(book, "ch01")
        self.assertTrue(any(x.check_id == "W4" and x.severity == "P0" for x in f))

    def test_w4_within_level_clean(self):
        book = self._book(level="taveel",
                          episodes={"ch01": {"atoms_injected": ["doctrine:eso", "term:x"]}})
        f = aug.check_w4_w5_content_and_existence(book, "ch01")
        self.assertFalse(any(x.check_id == "W4" for x in f))

    def test_w5_fabricated_atom(self):
        book = self._book(level="taveel",
                          episodes={"ch01": {"atoms_injected": ["doctrine:ghost"]}})
        f = aug.check_w4_w5_content_and_existence(book, "ch01")
        self.assertTrue(any(x.check_id == "W5" and x.severity == "P0" for x in f))

    def test_w6_cross_chapter_repeat(self):
        book = self._book(level="taveel", episodes={
            "ch01": {"atoms_injected": ["doctrine:eso"]},
            "ch02": {"atoms_injected": ["doctrine:eso"]},
        })
        f = aug.check_w6_no_cross_chapter_repeat(book)
        self.assertTrue(any(x.check_id == "W6" for x in f))

    def test_w6_no_repeat_clean(self):
        book = self._book(level="taveel", episodes={
            "ch01": {"atoms_injected": ["doctrine:eso"]},
            "ch02": {"atoms_injected": ["doctrine:real"]},
        })
        self.assertEqual(aug.check_w6_no_cross_chapter_repeat(book), [])


class TestRevert(unittest.TestCase):
    def test_revert_strips_block(self):
        text = _etym_block(2) + "\n\nThe real episode body begins here."
        out = aug.revert_block(text, "etymology")
        self.assertNotIn("ETYMOLOGY", out)
        self.assertIn("real episode body", out)

    def test_revert_absent_block_noop(self):
        text = "Plain body, no augmentation."
        self.assertIn("Plain body", aug.revert_block(text, "etymology"))


if __name__ == "__main__":
    unittest.main()
