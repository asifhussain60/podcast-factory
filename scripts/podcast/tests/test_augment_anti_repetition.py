#!/usr/bin/env python3
"""Tests for Wave L-5 — cross-chapter anti-repetition.

Verifies the per-episode augmentation ledger excludes atoms already injected
into OTHER episodes of the same book, while keeping single-episode re-runs
idempotent. Uses a throwaway DB + temp book dir — no Gemini, no canonical-DB writes.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "intelligence"))

import _db
import augmenter


class TestLedgerHelpers(unittest.TestCase):
    def _book(self) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / "_system").mkdir(parents=True)
        return d

    def test_excludes_other_episodes_keeps_self(self):
        ledger = {
            "episodes": {
                "ch01": {"atoms_injected": ["doctrine:a", "term:x"]},
                "ch02": {"atoms_injected": ["doctrine:b"]},
            }
        }
        # From ch02's perspective: ch01's atoms are excluded; ch02's own are not.
        used = augmenter._atoms_used_in_other_episodes(ledger, "ch02")
        self.assertEqual(used, {"doctrine:a", "term:x"})
        self.assertNotIn("doctrine:b", used)

    def test_record_and_reload_roundtrip(self):
        book = self._book()
        augmenter._record_episode_atoms(book, "ch01", ["doctrine:a", "doctrine:a", "term:x"])
        ledger = augmenter._load_episode_ledger(book)
        self.assertEqual(ledger["episodes"]["ch01"]["atoms_injected"], ["doctrine:a", "term:x"])
        # Re-record overwrites that episode's entry, not others.
        augmenter._record_episode_atoms(book, "ch02", ["doctrine:b"])
        ledger = augmenter._load_episode_ledger(book)
        self.assertEqual(set(ledger["episodes"].keys()), {"ch01", "ch02"})

    def test_record_keeps_usage_metadata(self):
        book = self._book()
        augmenter._record_episode_atoms(
            book,
            "ch01",
            ["doctrine:quranic-studies:a"],
            atom_usage=[
                {
                    "atom_id": "doctrine:quranic-studies:a",
                    "type": "doctrine",
                    "reason": "doctrine_topic_match",
                    "topic_tags": ["hamd"],
                    "quran_refs": ["1:2"],
                    "source_kind": "quranic_studies",
                }
            ],
        )
        ledger = augmenter._load_episode_ledger(book)
        usage = ledger["episodes"]["ch01"]["atom_usage"]
        self.assertEqual(usage[0]["topic_tags"], ["hamd"])
        self.assertEqual(usage[0]["quran_refs"], ["1:2"])
        self.assertEqual(usage[0]["source_kind"], "quranic_studies")

    def test_missing_ledger_is_empty(self):
        book = self._book()
        self.assertEqual(augmenter._load_episode_ledger(book), {"episodes": {}})


class TestDoctrineExclusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()) / "rep.db"
        _db._reset_connection()
        conn = _db.get_connection(db_path=cls.tmp)
        _db.run_migrations(db_path=cls.tmp)
        for i in range(5):
            conn.execute(
                "INSERT INTO atoms (id, type, body, tradition, content_level) "
                "VALUES (?, 'doctrine', ?, 'universal', 'taveel')",
                (f"doctrine:d{i}", json.dumps({"text_en": f"teaching {i}"})),
            )
            conn.execute("INSERT INTO atom_topic_tags (atom_id, tag) VALUES (?, 'wisdom')", (f"doctrine:d{i}",))
        conn.commit()

    @classmethod
    def tearDownClass(cls):
        _db._reset_connection()

    def test_excluded_ids_never_returned(self):
        exclude = {"doctrine:d0", "doctrine:d1", "doctrine:d2"}
        got = {
            a["id"]
            for a in augmenter._fetch_doctrine_atoms(
                ["wisdom"], max_atoms=50, tradition="universal", content_level="esoteric", exclude_atom_ids=exclude
            )
        }
        self.assertFalse(got & exclude, "excluded atom leaked through")
        self.assertEqual(got, {"doctrine:d3", "doctrine:d4"})

    def test_no_exclusion_returns_all(self):
        got = {
            a["id"]
            for a in augmenter._fetch_doctrine_atoms(
                ["wisdom"], max_atoms=50, tradition="universal", content_level="esoteric"
            )
        }
        self.assertEqual(len(got), 5)

    def test_end_to_end_ch02_excludes_ch01(self):
        """Full augment_episode_text flow: ch02 must not reuse ch01's doctrine atoms."""
        book = Path(tempfile.mkdtemp())
        (book / "_system").mkdir(parents=True)
        (book / "meta.yml").write_text(
            "series:\n  enable_knowledge_augmenter: true\n"
            "tradition_affinity: universal\n"
            "content_level: esoteric\n"
            "knowledge_tags:\n  - wisdom\n",
            encoding="utf-8",
        )
        text = "A chapter discussing wisdom and teaching."
        augmenter.augment_episode_text(text, book, max_atoms=2, episode_slug="ch01")
        led = augmenter._load_episode_ledger(book)
        ch01_atoms = set(led["episodes"]["ch01"]["atoms_injected"])
        self.assertTrue(ch01_atoms, "ch01 should have injected at least one atom")

        augmenter.augment_episode_text(text, book, max_atoms=2, episode_slug="ch02")
        led = augmenter._load_episode_ledger(book)
        ch02_atoms = set(led["episodes"]["ch02"]["atoms_injected"])
        self.assertFalse(ch01_atoms & ch02_atoms, f"atom repeated across chapters: {ch01_atoms & ch02_atoms}")


if __name__ == "__main__":
    unittest.main()
