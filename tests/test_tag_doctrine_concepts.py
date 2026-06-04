"""tests/test_tag_doctrine_concepts.py — WC2 doctrine concept-tagger (D19).

Uses a MOCK llm_caller (no Gemini, no network, no cost) over a temp DB. Asserts:
tags are written to atom_topic_tags, the pass is idempotent (already-tagged atoms
skipped), --dry-run writes nothing, and the cost cap halts the run.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from intelligence import tag_doctrine_concepts as td

_SCHEMA = (
    "CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, body TEXT, tradition TEXT);"
    "CREATE TABLE atom_topic_tags (atom_id TEXT, tag TEXT, PRIMARY KEY (atom_id, tag));"
)


def _mock_caller(prompt: str):
    """Return deterministic tags for every passage index found in the prompt."""
    import re
    idxs = [int(n) for n in re.findall(r"\[(\d+)\]", prompt)]
    results = [{"i": i, "tags": ["mercy", "soul"]} for i in idxs]
    return 0, json.dumps({"results": results}), "0.0001"


class DoctrineTagger(unittest.TestCase):
    def setUp(self):
        self._tmp = __import__("tempfile").NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.path = self._tmp.name
        c = sqlite3.connect(self.path)
        c.executescript(_SCHEMA)
        for i in range(3):
            c.execute("INSERT INTO atoms VALUES (?, 'doctrine', ?, 'fatimid-ismaili')",
                      (f"doctrine:wisdom:1:{i}:0", json.dumps({"text_en": f"teaching about the soul {i}"})))
        # one non-doctrine + one already-tagged doctrine (should be skipped)
        c.execute("INSERT INTO atoms VALUES ('quran:1:1','quran','{}','universal')")
        c.execute("INSERT INTO atoms VALUES ('doctrine:wisdom:9:9:0','doctrine','{\"text_en\":\"x\"}','fatimid-ismaili')")
        c.execute("INSERT INTO atom_topic_tags VALUES ('doctrine:wisdom:9:9:0','preexisting')")
        c.commit(); c.close()
        self._orig = td.get_connection
        td.get_connection = lambda **_: self._open()

    def _open(self):
        c = sqlite3.connect(self.path); c.row_factory = sqlite3.Row; return c

    def tearDown(self):
        td.get_connection = self._orig
        Path(self.path).unlink(missing_ok=True)

    def _count(self, sql, *a):
        c = sqlite3.connect(self.path); n = c.execute(sql, a).fetchone()[0]; c.close(); return n

    def test_dry_run_writes_nothing(self):
        s = td.tag_all(dry_run=True, llm_caller=_mock_caller)
        self.assertEqual(s.candidates, 3, "3 untagged doctrine atoms (the 4th is already tagged)")
        self.assertEqual(self._count("SELECT COUNT(*) FROM atom_topic_tags"), 1)  # only preexisting

    def test_tags_written_and_skip_existing(self):
        s = td.tag_all(llm_caller=_mock_caller)
        self.assertEqual(s.tagged, 3)
        # 3 atoms x 2 tags = 6 new + 1 preexisting = 7
        self.assertEqual(self._count("SELECT COUNT(*) FROM atom_topic_tags"), 7)
        # the already-tagged atom keeps only its original tag (was skipped)
        self.assertEqual(self._count("SELECT COUNT(*) FROM atom_topic_tags WHERE atom_id='doctrine:wisdom:9:9:0'"), 1)

    def test_idempotent(self):
        td.tag_all(llm_caller=_mock_caller)
        first = self._count("SELECT COUNT(*) FROM atom_topic_tags")
        s2 = td.tag_all(llm_caller=_mock_caller)
        self.assertEqual(s2.candidates, 0, "all doctrine atoms now tagged")
        self.assertEqual(self._count("SELECT COUNT(*) FROM atom_topic_tags"), first)

    def test_cost_cap_halts(self):
        # need >1 batch (BATCH_SIZE=8) for the pre-batch cap to trigger
        c = sqlite3.connect(self.path)
        for i in range(10):
            c.execute("INSERT INTO atoms VALUES (?, 'doctrine', ?, 'fatimid-ismaili')",
                      (f"doctrine:wisdom:5:{i}:0", json.dumps({"text_en": f"more teaching {i}"})))
        c.commit(); c.close()

        def pricey(prompt):
            return 0, json.dumps({"results": [{"i": 0, "tags": ["mercy"]}]}), "99.0"
        s = td.tag_all(llm_caller=pricey, cost_cap=1.0)
        self.assertTrue(any("cost cap" in e for e in s.errors))
        self.assertEqual(s.batches, 1, "halted before the second batch")


if __name__ == "__main__":
    unittest.main()
