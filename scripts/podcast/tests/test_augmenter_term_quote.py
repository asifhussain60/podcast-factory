"""Tests for the term and quote keyword-lookup paths in augment_episode_text (Wave K).

Verifies:
- Term atoms whose name appears in the episode text are injected in a TERM GLOSSARY block.
- Quote atoms whose speaker appears in the episode text are injected in an ATTRIBUTED SAYINGS block.
- Short terms (< _MIN_TERM_MATCH_LEN chars) are not matched.
- Disabled gate (enable_knowledge_augmenter=False) skips all three lookups.
- Empty lookups produce no block; only non-empty blocks appear in the output.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "podcast"))


class TermQuoteLookupTests(unittest.TestCase):
    """Unit tests for _fetch_matching_terms, _fetch_matching_quotes, and their callers."""

    def _fake_book_dir(self, tmp: Path, enabled: bool = True,
                       tradition: str = "fatimid-ismaili",
                       tags: list[str] | None = None) -> Path:
        book_dir = tmp / "books" / "test-book"
        book_dir.mkdir(parents=True)
        meta = {
            "series": {"enable_knowledge_augmenter": enabled},
            "tradition_affinity": tradition,
            "knowledge_tags": tags or [],
        }
        import yaml  # type: ignore[import]
        (book_dir / "meta.yml").write_text(yaml.dump(meta), encoding="utf-8")
        return book_dir

    def _fake_db(self, atoms: list[dict]) -> sqlite3.Connection:
        """Build an in-memory DB with atom rows matching the production schema."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE atoms (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                body TEXT NOT NULL,
                tradition TEXT NOT NULL DEFAULT 'universal',
                confidence REAL NOT NULL DEFAULT 1.0
            )
        """)
        conn.execute("""
            CREATE TABLE atom_topic_tags (
                atom_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (atom_id, tag)
            )
        """)
        for a in atoms:
            conn.execute(
                "INSERT INTO atoms (id, type, body, tradition) VALUES (?,?,?,?)",
                (a["id"], a["type"], json.dumps(a["body"], ensure_ascii=False), a.get("tradition", "universal")),
            )
        conn.commit()
        return conn

    def _run_augment(self, episode_text: str, book_dir: Path,
                     term_atoms: list[dict], quote_atoms: list[dict]) -> str:
        import intelligence.augmenter as aug_mod
        fake_conn = self._fake_db(term_atoms + quote_atoms)

        def fake_get_connection():
            return fake_conn

        with mock.patch.object(aug_mod._db, "get_connection", side_effect=fake_get_connection):
            return aug_mod.augment_episode_text(episode_text, book_dir)

    # ── term lookup ────────────────────────────────────────────────────────────

    def test_term_match_injects_glossary_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), tradition="universal")
            term = {"id": "term:doctrine:tawakkul", "type": "term",
                    "body": {"term": "tawakkul", "text_en": "Complete trust in Allah"}, "tradition": "universal"}
            episode = "The chapter discusses tawakkul and its spiritual dimensions."
            result = self._run_augment(episode, book_dir, [term], [])
            self.assertIn("[TERM GLOSSARY", result)
            self.assertIn("*tawakkul*", result)
            self.assertIn("Complete trust in Allah", result)
            self.assertIn(episode, result)

    def test_term_not_in_text_produces_no_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), tradition="universal")
            term = {"id": "term:doctrine:zuhd", "type": "term",
                    "body": {"term": "zuhd", "text_en": "Asceticism"}, "tradition": "universal"}
            episode = "This episode covers patience and sincerity only."
            result = self._run_augment(episode, book_dir, [term], [])
            self.assertNotIn("[TERM GLOSSARY", result)
            self.assertEqual(result, episode)

    def test_short_term_below_min_length_not_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), tradition="universal")
            short_term = {"id": "term:doctrine:al", "type": "term",
                          "body": {"term": "al", "text_en": "Definite article"}, "tradition": "universal"}
            episode = "The al-prefix carries deep meaning in Arabic grammar."
            result = self._run_augment(episode, book_dir, [short_term], [])
            self.assertNotIn("[TERM GLOSSARY", result)

    # ── quote lookup ───────────────────────────────────────────────────────────

    def test_quote_match_injects_sayings_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), tradition="universal")
            quote = {"id": "quote:imam-ali:abc1234567", "type": "quote",
                     "body": {"speaker": "Imam Ali", "text_en": "Knowledge is the greatest gift."},
                     "tradition": "universal"}
            episode = "Imam Ali is frequently cited by scholars of this tradition."
            result = self._run_augment(episode, book_dir, [], [quote])
            self.assertIn("[ATTRIBUTED SAYINGS", result)
            self.assertIn("Imam Ali:", result)
            self.assertIn("Knowledge is the greatest gift.", result)

    def test_quote_speaker_absent_produces_no_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), tradition="universal")
            quote = {"id": "quote:imam-hussain:xyz9999", "type": "quote",
                     "body": {"speaker": "Imam Hussain", "text_en": "Patience is honour."},
                     "tradition": "universal"}
            episode = "This episode discusses only Ghazali's letter to his student."
            result = self._run_augment(episode, book_dir, [], [quote])
            self.assertNotIn("[ATTRIBUTED SAYINGS", result)

    # ── gate check ─────────────────────────────────────────────────────────────

    def test_disabled_gate_skips_all_lookups(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._fake_book_dir(Path(tmp), enabled=False)
            term = {"id": "term:doctrine:nafs", "type": "term",
                    "body": {"term": "nafs", "text_en": "The soul or self"}, "tradition": "universal"}
            episode = "This chapter is about nafs and its purification."
            result = self._run_augment(episode, book_dir, [term], [])
            self.assertEqual(result, episode)


if __name__ == "__main__":
    unittest.main()
