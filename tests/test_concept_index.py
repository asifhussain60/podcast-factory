"""tests/test_concept_index.py — WC2 concept-derivation engine (decision D19).

Synthetic atoms (never the live DB) → assert: terms+etymology sharing a root merge
into one root-concept, hadith themes form theme-concepts, Quran/doctrine count as
unmapped, and the build is deterministic.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from intelligence import concept_index as ci

_SCHEMA = "CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, body TEXT, tradition TEXT);"


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_SCHEMA)
    rows = [
        ("term:kqur:alim", "term", {"term": "ALIM", "arabic": "عالم", "root": "ilm", "definition": "One having knowledge, scholar"}),
        ("term:kqur:aleem", "term", {"term": "ALEEM", "arabic": "عليم", "root": "ilm", "definition": "All-Knowing"}),
        ("etymology:ilm", "etymology", {"text_en": "root ilm — to know"}),       # merges into root:ilm
        ("term:kqur:rahman", "term", {"term": "RAHMAN", "arabic": "رحمٰن", "root": "rhm", "definition": "Universally Merciful"}),
        ("hadith:kashkole:14", "hadith", {"collection": "soul", "english": "knows himself"}),
        ("hadith:kashkole:20", "hadith", {"collection": "soul", "english": "the soul ascends"}),
        ("hadith:kashkole:30", "hadith", {"collection": "tawheed", "english": "God is one"}),
        ("quran:1:1", "quran", {"surah": 1, "ayat": 1, "arabic": "بسم"}),         # unmapped
        ("doctrine:wisdom:1:1:0", "doctrine", {"text_en": "teaching"}),           # unmapped
    ]
    for aid, t, body in rows:
        c.execute("INSERT INTO atoms VALUES (?,?,?,?)", (aid, t, json.dumps(body), "universal"))
    c.commit()
    return c


class ConceptIndex(unittest.TestCase):
    def setUp(self):
        self.idx = ci.build_concepts(_conn())
        self.by_id = {c["id"]: c for c in self.idx["concepts"]}

    def test_terms_and_etymology_merge_by_root(self):
        ilm = self.by_id["root:ilm"]
        self.assertEqual(ilm["atom_count"], 3, "2 terms + 1 etymology share root ilm")
        self.assertEqual(ilm["by_type"], {"term": 2, "etymology": 1})
        self.assertIn("ALIM", ilm["synonyms"])
        self.assertEqual(ilm["arabic"], "عالم")

    def test_hadith_themes_group(self):
        soul = self.by_id["theme:soul"]
        self.assertEqual(soul["atom_count"], 2)
        self.assertEqual(soul["kind"], "theme")
        self.assertIn("theme:tawheed", self.by_id)

    def test_quran_and_doctrine_unmapped(self):
        cov = self.idx["coverage"]
        self.assertEqual(cov["unmapped_by_type"].get("quran"), 1)
        self.assertEqual(cov["unmapped_by_type"].get("doctrine"), 1)
        self.assertEqual(cov["concept_mapped"], 7)  # 3 ilm + 1 rhm + 3 hadith

    def test_deterministic(self):
        a = ci.build_concepts(_conn())
        b = ci.build_concepts(_conn())
        self.assertEqual(json.dumps(a, ensure_ascii=False, sort_keys=True),
                         json.dumps(b, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
