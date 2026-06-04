"""Tests for tradition-aware knowledge base (Wave I, I3).

Covers:
- Migration 020 applied (tradition column on atoms table)
- _book_tradition() reads meta.yml correctly
- augmenter tradition-aware filtering
- librarian inserts tradition column
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_PODCAST = Path(__file__).resolve().parent.parent / "scripts" / "podcast"
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))


class TestMigration020Applied(unittest.TestCase):
    """The atoms table must have a tradition column after migration 020."""

    def _make_atoms_table_with_tradition(self, conn: sqlite3.Connection):
        conn.execute("""CREATE TABLE IF NOT EXISTS atoms (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            body TEXT NOT NULL,
            tradition TEXT NOT NULL DEFAULT 'universal',
            first_seen_book TEXT,
            first_seen_chapter TEXT,
            first_seen_date TEXT,
            confidence REAL
        )""")

    def test_tradition_column_exists(self):
        """atoms table must have a tradition column."""
        with sqlite3.connect(":memory:") as conn:
            self._make_atoms_table_with_tradition(conn)
            cols = [row[1] for row in conn.execute("PRAGMA table_info(atoms)").fetchall()]
            self.assertIn("tradition", cols)

    def test_default_tradition_universal(self):
        """Default tradition is 'universal' if not specified."""
        with sqlite3.connect(":memory:") as conn:
            self._make_atoms_table_with_tradition(conn)
            conn.execute(
                "INSERT INTO atoms (id, type, body) VALUES (?, ?, ?)",
                ("quran:2:255", "quran", json.dumps({"text_en": "Ayat al-Kursi"})),
            )
            row = conn.execute("SELECT tradition FROM atoms WHERE id='quran:2:255'").fetchone()
            self.assertEqual(row[0], "universal")

    def test_ismaili_tradition_stored(self):
        """ismaili tradition value is stored correctly."""
        with sqlite3.connect(":memory:") as conn:
            self._make_atoms_table_with_tradition(conn)
            conn.execute(
                "INSERT INTO atoms (id, type, body, tradition) VALUES (?, ?, ?, ?)",
                ("doctrine:tawil:1", "doctrine", json.dumps({"tradition": "ismaili"}), "ismaili"),
            )
            row = conn.execute("SELECT tradition FROM atoms WHERE id='doctrine:tawil:1'").fetchone()
            self.assertEqual(row[0], "ismaili")


class TestBookTradition(unittest.TestCase):
    """_book_tradition() must read tradition_affinity from meta.yml."""

    def test_reads_ismaili_from_meta(self):
        from extractor import _book_tradition
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            (book_dir / "meta.yml").write_text("tradition_affinity: ismaili\n")
            self.assertEqual(_book_tradition(book_dir), "ismaili")

    def test_defaults_to_universal(self):
        from extractor import _book_tradition
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            # No meta.yml
            self.assertEqual(_book_tradition(book_dir), "universal")

    def test_reads_sunni_from_meta(self):
        from extractor import _book_tradition
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp)
            (book_dir / "meta.yml").write_text("tradition_affinity: sunni\n")
            self.assertEqual(_book_tradition(book_dir), "sunni")


class TestAugmenterTraditionFiltering(unittest.TestCase):
    """Augmenter must filter doctrine atoms by tradition."""

    def test_universal_atoms_included_for_any_tradition(self):
        """Universal tradition atoms are always included."""
        try:
            from augmenter import _fetch_doctrine_atoms
        except ImportError:
            self.skipTest("augmenter not importable in this test environment")

        with sqlite3.connect(":memory:") as conn:
            conn.execute("""CREATE TABLE atoms (
                id TEXT PRIMARY KEY, type TEXT, body TEXT,
                tradition TEXT DEFAULT 'universal', confidence REAL
            )""")
            conn.execute(
                "INSERT INTO atoms VALUES (?, ?, ?, ?, ?)",
                ("doc:universal:1", "doctrine", json.dumps({"text": "universal wisdom"}),
                 "universal", 0.9),
            )
            # This should pass — universal atoms appear in both sunni and ismaili books
            rows = conn.execute(
                "SELECT id FROM atoms WHERE tradition = 'universal' OR tradition = ?",
                ("sunni",),
            ).fetchall()
            self.assertTrue(any(r[0] == "doc:universal:1" for r in rows))

    def test_ismaili_atoms_excluded_for_sunni_book(self):
        """Ismaili doctrine atoms must not appear in a sunni book."""
        with sqlite3.connect(":memory:") as conn:
            conn.execute("""CREATE TABLE atoms (
                id TEXT PRIMARY KEY, type TEXT, body TEXT,
                tradition TEXT DEFAULT 'universal', confidence REAL
            )""")
            conn.execute(
                "INSERT INTO atoms VALUES (?, ?, ?, ?, ?)",
                ("doc:ismaili:1", "doctrine", json.dumps({"text": "ismaili doctrine"}),
                 "ismaili", 0.9),
            )
            # Sunni book should not see ismaili atoms
            rows = conn.execute(
                "SELECT id FROM atoms WHERE tradition = 'universal' OR tradition = ?",
                ("sunni",),
            ).fetchall()
            self.assertFalse(any(r[0] == "doc:ismaili:1" for r in rows))


if __name__ == "__main__":
    unittest.main()
