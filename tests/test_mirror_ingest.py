"""tests/test_mirror_ingest.py — WC1 mirror-primary importers (ingest_kqur/kashkole/ksessions).

Builds a synthetic mirror.db + a temp knowledge.db (never the live DB) and asserts:
  * every atom is tradition-stamped (D5 — acceptance gate),
  * Quran -> universal; terms -> their source tradition; hadith -> universal,
  * KASHKOLE Urdu topics mint ZERO atoms (D8 no-retranslate),
  * a hadith id already authored upstream is preserved (INSERT OR IGNORE, non-destructive),
  * sessions register as corpus_chapters with no atoms,
  * re-running is idempotent (no new rows).
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from intelligence import ingest_kashkole, ingest_kqur, ingest_ksessions_dump

# Minimal target schema (the columns the importers touch).
_KNOWLEDGE_SCHEMA = """
CREATE TABLE atoms (
    id TEXT PRIMARY KEY, type TEXT NOT NULL, body TEXT NOT NULL,
    tradition TEXT NOT NULL DEFAULT 'universal',
    first_seen_book TEXT, first_seen_chapter TEXT, confidence REAL NOT NULL DEFAULT 1.0
);
CREATE TABLE atom_topic_tags (atom_id TEXT, tag TEXT, PRIMARY KEY (atom_id, tag));
CREATE TABLE external_corpora (
    id TEXT PRIMARY KEY, display_name TEXT NOT NULL, corpus_type TEXT NOT NULL,
    atom_count INTEGER NOT NULL DEFAULT 0, last_synced TEXT
);
CREATE TABLE corpus_chapters (
    id TEXT PRIMARY KEY, corpus_id TEXT NOT NULL, number INTEGER,
    title_en TEXT, title_ar TEXT, verse_count INTEGER,
    ingestion_status TEXT DEFAULT 'pending', last_ingested_at TEXT
);
"""

_MIRROR_SCHEMA = """
CREATE TABLE fts_quran (surah, ayat, arabic, pickthall, asad, urdu, phonetic);
CREATE TABLE term_index (
    term TEXT, arabic TEXT, root TEXT, grammar_tag TEXT, definition TEXT,
    etymology TEXT, tradition TEXT, source TEXT, related TEXT
);
CREATE TABLE fts_hadith (hadith_id, collection, hadith_num, arabic, english);
CREATE TABLE fts_sessions (session_id, session_name, group_id, content);
CREATE TABLE fts_topics (topic_id, topic_type_id, name, name_en, description);
"""


class MirrorIngest(unittest.TestCase):
    def setUp(self):
        self._kt = tempfile.NamedTemporaryFile(suffix="-k.db", delete=False); self._kt.close()
        self._mt = tempfile.NamedTemporaryFile(suffix="-m.db", delete=False); self._mt.close()
        self.k_path, self.m_path = self._kt.name, self._mt.name

        k = sqlite3.connect(self.k_path)
        k.executescript(_KNOWLEDGE_SCHEMA)
        # Pre-existing hadith atom authored "upstream" — must be preserved (ismaili, not universal).
        k.execute(
            "INSERT INTO atoms (id, type, body, tradition, first_seen_book)"
            " VALUES ('hadith:kashkole:9', 'hadith', '{\"english\":\"upstream original\"}', 'ismaili', 'wisdom')"
        )
        k.commit(); k.close()

        m = sqlite3.connect(self.m_path)
        m.executescript(_MIRROR_SCHEMA)
        m.executemany(
            "INSERT INTO fts_quran VALUES (?,?,?,?,?,?,?)",
            [(1, 1, "ar1", "pick1", "asad1", "ur1", "ph1"),
             (1, 2, "ar2", "pick2", "asad2", "ur2", "ph2"),
             (2, 1, "ar3", "pick3", "asad3", "ur3", "ph3")],
        )
        m.executemany(
            "INSERT INTO term_index VALUES (?,?,?,?,?,?,?,?,?)",
            [("ALIM", "عالم", "ilm", "noun", "scholar", "", "ismaili", "KQUR", ""),
             ("WUDU", "وضو", "wdu", "noun", "ablution", "", "ismaili", "KASHKOLE", "")],
        )
        m.executemany(
            "INSERT INTO fts_hadith VALUES (?,?,?,?,?)",
            [(9, "tawheed", "9", "har", "existing-id"),     # collides w/ upstream -> ignored
             (500, "soul", "500", "har2", "brand new")],     # new -> inserted
        )
        m.executemany(
            "INSERT INTO fts_sessions VALUES (?,?,?,?)",
            [(1, "Intro", 1, "english content"), (2, "Part Two", 1, "more english")],
        )
        m.executemany(
            "INSERT INTO fts_topics VALUES (?,?,?,?,?)",
            [(3, 15, "اردو عنوان", "", "اردو متن"), (4, 16, "دوسرا", "", "متن دو")],
        )
        m.commit(); m.close()

        # Route both connections at the temp DBs for all three importers.
        self._patches = []
        target = self  # noqa
        ro = lambda: sqlite3.connect(f"file:{self.m_path}?mode=ro", uri=True)
        for mod in (ingest_kqur, ingest_kashkole, ingest_ksessions_dump):
            for name, fn in (("get_connection", self._open_k), ("open_mirror_ro", self._open_m)):
                if hasattr(mod, name):
                    self._patches.append((mod, name, getattr(mod, name)))
                    setattr(mod, name, fn)

    def _open_k(self, **_):
        c = sqlite3.connect(self.k_path); c.row_factory = sqlite3.Row; return c

    def _open_m(self):
        c = sqlite3.connect(f"file:{self.m_path}?mode=ro", uri=True); c.row_factory = sqlite3.Row; return c

    def tearDown(self):
        for mod, name, orig in self._patches:
            setattr(mod, name, orig)
        Path(self.k_path).unlink(missing_ok=True)
        Path(self.m_path).unlink(missing_ok=True)

    def _q(self, sql, *args):
        c = sqlite3.connect(self.k_path)
        out = c.execute(sql, args).fetchone()[0]
        c.close()
        return out

    def test_every_atom_is_tradition_stamped(self):
        ingest_kqur.ingest_all()
        ingest_kashkole.ingest_all()
        blank = self._q("SELECT COUNT(*) FROM atoms WHERE tradition IS NULL OR tradition = ''")
        self.assertEqual(blank, 0, "D5: every atom must carry a tradition")

    def test_quran_universal_and_chapters(self):
        ingest_kqur.ingest_all()
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms WHERE type='quran'"), 3)
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms WHERE type='quran' AND tradition='universal'"), 3)
        # one corpus_chapters row per surah (2 surahs)
        self.assertEqual(self._q("SELECT COUNT(*) FROM corpus_chapters WHERE corpus_id='quran'"), 2)
        self.assertEqual(self._q("SELECT verse_count FROM corpus_chapters WHERE id='quran:1'"), 2)

    def test_terms_carry_source_tradition(self):
        ingest_kqur.ingest_all()
        ingest_kashkole.ingest_all()
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms WHERE type='term'"), 2)
        self.assertEqual(self._q("SELECT tradition FROM atoms WHERE id='term:kqur:alim'"), "ismaili")

    def test_hadith_additive_preserves_upstream(self):
        ingest_kashkole.ingest_all()
        # upstream hadith:kashkole:9 untouched (still ismaili + original body); 500 added as universal
        self.assertEqual(self._q("SELECT tradition FROM atoms WHERE id='hadith:kashkole:9'"), "ismaili")
        self.assertIn("upstream original", self._q("SELECT body FROM atoms WHERE id='hadith:kashkole:9'"))
        self.assertEqual(self._q("SELECT tradition FROM atoms WHERE id='hadith:kashkole:500'"), "universal")
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms WHERE type='hadith'"), 2)

    def test_topics_mint_no_atoms(self):
        ingest_kashkole.ingest_all()
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms WHERE type='doctrine'"), 0,
                         "D8: Urdu topics must NOT become atoms")

    def test_sessions_chapters_no_atoms(self):
        before = self._q("SELECT COUNT(*) FROM atoms")
        ingest_ksessions_dump.ingest_all()
        self.assertEqual(self._q("SELECT COUNT(*) FROM corpus_chapters WHERE corpus_id='ksessions'"), 2)
        self.assertEqual(self._q("SELECT COUNT(*) FROM atoms"), before, "sessions add no atoms in WC1")

    def test_idempotent(self):
        for _ in range(2):
            ingest_kqur.ingest_all()
            ingest_kashkole.ingest_all()
            ingest_ksessions_dump.ingest_all()
        counts = (
            self._q("SELECT COUNT(*) FROM atoms"),
            self._q("SELECT COUNT(*) FROM corpus_chapters"),
            self._q("SELECT COUNT(*) FROM external_corpora"),
        )
        # 1 upstream + 3 quran + 2 terms + 1 new hadith = 7 atoms; 2 quran + 2 session chapters = 4
        self.assertEqual(counts, (7, 4, 3))


if __name__ == "__main__":
    unittest.main()
