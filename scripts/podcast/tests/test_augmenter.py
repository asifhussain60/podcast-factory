#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.podcast.knowledge import augmenter


class AugmenterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "quran.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "id": "quran:2:255",
                            "type": "quran",
                            "body": {"text_en": "Allah! There is no deity except Him."},
                            "first_seen": {"book": "kitab-a", "chapter": "ch01"},
                            "sources": [{"book": "kitab-a", "chapter": "ch01"}],
                        }
                    ),
                    json.dumps(
                        {
                            "id": "quran:112:1",
                            "type": "quran",
                            "body": {"text_en": "Say: He is Allah, One."},
                            "first_seen": {"book": "kitab-b", "chapter": "ch03"},
                            "sources": [{"book": "kitab-b", "chapter": "ch03"}],
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        (self.root / "hadith.jsonl").write_text(
            json.dumps(
                {
                    "id": "hadith:bukhari:1",
                    "type": "hadith",
                    "body": {"text_en": "Actions are judged by intentions."},
                    "first_seen": {"book": "kitab-c", "chapter": "ch09"},
                    "sources": [{"book": "kitab-c", "chapter": "ch09"}],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_lookup_atom_finds_existing(self):
        atom = augmenter.lookup_atom("quran:2:255", self.root)
        self.assertIsNotNone(atom)
        self.assertEqual(atom["id"], "quran:2:255")

    def test_lookup_atom_returns_none_missing(self):
        self.assertIsNone(augmenter.lookup_atom("quran:9:9", self.root))

    def test_augment_for_chapter_returns_empty_without_matches(self):
        with mock.patch.object(augmenter, "KNOWLEDGE_ROOT", self.root):
            out = augmenter.augment_for_chapter(
                "kitab-z", "ch01", "No citations in this chapter."
            )
        self.assertEqual(out, "")

    def test_augment_for_chapter_includes_matched_atoms(self):
        chapter_text = "Quran 2:255 and Bukhari 1 are discussed."
        with mock.patch.object(augmenter, "KNOWLEDGE_ROOT", self.root):
            out = augmenter.augment_for_chapter("kitab-z", "ch01", chapter_text, max_atoms=5)
        self.assertIn("[PRIOR TREATMENT CONTEXT]", out)
        self.assertIn("quran:2:255", out)
        self.assertIn("hadith:bukhari:1", out)

    def test_augment_for_chapter_respects_max_atoms(self):
        chapter_text = "Quran 2:255, Quran 112:1, Bukhari 1"
        with mock.patch.object(augmenter, "KNOWLEDGE_ROOT", self.root):
            out = augmenter.augment_for_chapter("kitab-z", "ch01", chapter_text, max_atoms=1)
        # Header + one atom line only
        self.assertEqual(len(out.splitlines()), 2)

    def test_augment_for_chapter_excludes_self_only_sources(self):
        chapter_text = "Quran 2:255"
        with mock.patch.object(augmenter, "KNOWLEDGE_ROOT", self.root):
            out = augmenter.augment_for_chapter("kitab-a", "ch01", chapter_text)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
