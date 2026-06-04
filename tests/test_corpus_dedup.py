"""tests/test_corpus_dedup.py — WC1 tiered dedup engine (decision D7).

Covers the pure similarity helpers and an isolated, temp-DB integration test of
the tier routing (HIGH -> variant + auto-merge candidate; BORDERLINE -> review)
plus idempotency. No dependency on the live knowledge.db.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from intelligence import dedup_corpus as dc

_MINIMAL_SCHEMA = """
CREATE TABLE atoms (
    id TEXT PRIMARY KEY, type TEXT, body TEXT, tradition TEXT,
    first_seen_book TEXT, first_seen_chapter TEXT, confidence REAL
);
CREATE TABLE atom_topic_tags (atom_id TEXT, tag TEXT);
CREATE TABLE atoms_variants (
    atom_id TEXT NOT NULL, book_slug TEXT NOT NULL, text_en TEXT NOT NULL,
    translator TEXT, PRIMARY KEY (atom_id, book_slug)
);
CREATE TABLE manual_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT, book_slug TEXT NOT NULL,
    chapter_id TEXT, reason TEXT NOT NULL, payload TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    resolved_at TEXT, resolution TEXT
);
"""


class PureHelpers(unittest.TestCase):
    def test_jaccard_exact_and_disjoint(self):
        a = dc._tokens(dc._normalize("the soul ascends through knowledge"))
        self.assertEqual(dc._jaccard(a, a), 1.0)
        self.assertEqual(dc._jaccard(a, frozenset()), 0.0)
        b = dc._tokens(dc._normalize("ritual purity ablution water"))
        self.assertEqual(dc._jaccard(a, b), 0.0)

    def test_jaccard_partial(self):
        a = dc._tokens(dc._normalize("the soul ascends through knowledge and action"))
        b = dc._tokens(dc._normalize("the soul ascends via knowledge and through action and silence"))
        sim = dc._jaccard(a, b)
        self.assertGreater(sim, 0.65)
        self.assertLess(sim, 0.90)

    def test_normalize_strips_punctuation_and_case(self):
        self.assertEqual(dc._normalize("The  Soul, Ascends!"), "the soul ascends")

    def test_extract_text_from_json_and_plain(self):
        self.assertEqual(dc._extract_text(json.dumps({"text_en": "hello"})), "hello")
        self.assertEqual(dc._extract_text("plain string body"), "plain string body")

    def test_union_find_clusters(self):
        uf = dc._UF()
        uf.union("a", "b")
        uf.union("b", "c")
        self.assertEqual(uf.find("a"), uf.find("c"))
        self.assertNotEqual(uf.find("a"), uf.find("z"))


class DedupRouting(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        conn = sqlite3.connect(self.db_path)
        conn.executescript(_MINIMAL_SCHEMA)
        atoms = [
            ("a1", "the soul ascends through knowledge and action"),
            ("a2", "the soul ascends through knowledge and action"),          # exact dup -> HIGH
            ("a3", "the soul ascends via knowledge and through action and silence"),  # near -> BORDERLINE
            ("a4", "completely separate teaching on ritual purity and ablution"),     # distinct
        ]
        for aid, text in atoms:
            conn.execute(
                "INSERT INTO atoms (id, type, body, tradition) VALUES (?, 'doctrine', ?, 'fatimid-ismaili')",
                (aid, json.dumps({"text_en": text})),
            )
            conn.execute("INSERT INTO atom_topic_tags (atom_id, tag) VALUES (?, 'Eschatology')", (aid,))
        conn.commit()
        conn.close()
        # Route the engine at our temp DB.
        self._orig = dc.get_connection
        dc.get_connection = lambda **_: sqlite3.connect(self.db_path)

    def tearDown(self):
        dc.get_connection = self._orig
        Path(self.db_path).unlink(missing_ok=True)

    def _row_counts(self):
        conn = sqlite3.connect(self.db_path)
        v = conn.execute("SELECT COUNT(*) FROM atoms_variants").fetchone()[0]
        rq = conn.execute("SELECT COUNT(*) FROM manual_review_queue").fetchone()[0]
        conn.close()
        return v, rq

    def test_tier_routing(self):
        s = dc.dedup(types=("doctrine",), high=0.90, review=0.65)
        self.assertEqual(s.clusters, 1, "a1+a2 should form one HIGH cluster")
        self.assertEqual(s.variants_written, 1, "one duplicate recorded as a variant")
        self.assertEqual(s.review_high, 1, "one auto-merge candidate queued")
        self.assertEqual(s.review_borderline, 2, "a3 is borderline vs both a1 and a2")
        v, rq = self._row_counts()
        self.assertEqual(v, 1)
        self.assertEqual(rq, 3)  # 1 high + 2 borderline

    def test_idempotent(self):
        dc.dedup(types=("doctrine",))
        first = self._row_counts()
        dc.dedup(types=("doctrine",))
        second = self._row_counts()
        self.assertEqual(first, second, "re-run must not accumulate rows")

    def test_dry_run_writes_nothing(self):
        dc.dedup(types=("doctrine",), dry_run=True)
        self.assertEqual(self._row_counts(), (0, 0))


if __name__ == "__main__":
    unittest.main()
