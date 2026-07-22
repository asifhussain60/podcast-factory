"""Tests for pronunciation_compiler.py (Step 4) + the _elevenlabs client's

dictionary upload path. All network mocked via the injectable transport."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import pronunciation_compiler as pc
from _dialogue_script import Turn

ENTRIES = [
    {
        "phonetic": "Sayyidina",
        "transliteration": "Sayyidina",
        "arabic_script": "سيدنا",
        "audio_phonetic": "sai-yi-DEE-nah",
    },
    {"phonetic": "batin", "transliteration": "batin", "arabic_script": "الباطن", "audio_phonetic": "BAA-tin"},
    # Trivial: alias == grapheme modulo case/punct — must be skipped.
    {"phonetic": "Umma", "audio_phonetic": "UM-MA"},
    # No audio_phonetic — skipped.
    {"phonetic": "minhaj", "arabic_script": "منهاج"},
    # XML-hostile characters must be escaped.
    {"phonetic": "Kun & <fa-yakun>", "audio_phonetic": "KOON & fa-ya-KOON"},
]


class TestCompile(unittest.TestCase):
    def test_deterministic_and_sorted(self):
        a = pc.compile_pls(ENTRIES)
        b = pc.compile_pls(list(reversed(ENTRIES)))
        self.assertEqual(a, b)  # input order does not matter
        self.assertEqual(pc.pls_sha256(a), pc.pls_sha256(b))

    def test_alias_rules_only_and_skips(self):
        pls = pc.compile_pls(ENTRIES)
        self.assertEqual(pls.count("<lexeme>"), 3)  # 2 skipped
        self.assertIn("<alias>sai-yi-DEE-nah</alias>", pls)
        self.assertNotIn("<phoneme", pls)  # phoneme rules are forbidden
        self.assertNotIn("Umma", pls)

    def test_xml_escaping(self):
        pls = pc.compile_pls(ENTRIES)
        self.assertIn("Kun &amp; &lt;fa-yakun&gt;", pls)
        self.assertIn("KOON &amp; fa-ya-KOON", pls)

    def test_empty_glossary_compiles_empty_lexicon(self):
        pls = pc.compile_pls([])
        self.assertEqual(pls.count("<lexeme>"), 0)
        self.assertIn("<lexicon", pls)


class _FakeClient:
    """Counts uploads; returns fresh ids per upload."""

    def __init__(self):
        self.uploads: list[tuple[str, str]] = []

    def create_pronunciation_dictionary(self, *, name, pls_text, description=""):
        self.uploads.append((name, pls_text))
        n = len(self.uploads)
        return f"dict-{n}", f"ver-{n}"


class TestEnsureDictionary(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "book"
        (self.book / "_system").mkdir(parents=True)
        self._write_glossary(ENTRIES)
        self.client = _FakeClient()

    def _write_glossary(self, entries):
        import yaml

        (self.book / "_system" / "glossary.yml").write_text(
            yaml.safe_dump({"schema_version": 1, "entries": entries}), encoding="utf-8"
        )

    def test_upload_once_then_pin(self):
        loc1 = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertEqual(loc1, {"pronunciation_dictionary_id": "dict-1", "version_id": "ver-1"})
        # Second call: glossary unchanged -> NO re-upload, same pin.
        loc2 = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertEqual(loc2, loc1)
        self.assertEqual(len(self.client.uploads), 1)

    def test_glossary_change_new_version_and_history(self):
        pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        changed = ENTRIES + [{"phonetic": "zahir", "audio_phonetic": "ZAA-hir"}]
        self._write_glossary(changed)
        loc = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertEqual(loc["pronunciation_dictionary_id"], "dict-2")
        self.assertEqual(len(self.client.uploads), 2)
        st = json.loads((self.book / "_system" / "pronunciation-dictionary.json").read_text(encoding="utf-8"))
        self.assertEqual(len(st["history"]), 1)  # old pin recorded in the ledger
        self.assertEqual(st["history"][0]["dictionary_id"], "dict-1")

    def test_no_usable_rules_returns_none(self):
        self._write_glossary([{"phonetic": "Umma", "audio_phonetic": "UMMA"}])
        loc = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertIsNone(loc)
        self.assertEqual(len(self.client.uploads), 0)

    def test_missing_glossary_returns_none(self):
        (self.book / "_system" / "glossary.yml").unlink()
        loc = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertIsNone(loc)


class TestArabicRecitationScaffold(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.book = Path(tmp) / "book"
        (self.book / "_system").mkdir(parents=True)
        import yaml

        (self.book / "_system" / "glossary.yml").write_text(yaml.safe_dump({"entries": ENTRIES}), encoding="utf-8")
        self.turns = [Turn("HOST_A", "The word Sayyidina opens the line."), Turn("HOST_B", "And batin stays hidden.")]

    def test_default_off_is_identity(self):
        self.assertFalse(pc.arabic_recitation_enabled(self.book))
        out = pc.compile_turns_for_render(self.book, self.turns)
        self.assertEqual(out, self.turns)

    def test_flag_on_substitutes_arabic_script(self):
        (self.book / "_system" / "series-config.yaml").write_text(
            "audio_engine: elevenlabs\nelevenlabs_arabic_recitation: true\n", encoding="utf-8"
        )
        self.assertTrue(pc.arabic_recitation_enabled(self.book))
        out = pc.compile_turns_for_render(self.book, self.turns)
        self.assertIn("سيدنا", out[0].text)
        self.assertIn("الباطن", out[1].text)
        # Source turns untouched (render-layer only).
        self.assertIn("Sayyidina", self.turns[0].text)


class TestGlossaryCuration(unittest.TestCase):
    """Schema-v2 human decisions (keep/fix_phonetic/correct_arabic/replace_english)."""

    def _book(self, entries):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        book = Path(tmp) / "book"
        (book / "_system").mkdir(parents=True)
        import yaml

        (book / "_system" / "glossary.yml").write_text(yaml.safe_dump({"entries": entries}), encoding="utf-8")
        (book / "_system" / "series-config.yaml").write_text(
            "audio_engine: elevenlabs\nelevenlabs_arabic_recitation: true\n", encoding="utf-8"
        )
        return book

    def test_keep_and_absent_are_unchanged(self):
        for entry in (
            {"phonetic": "batin", "arabic_script": "الباطن"},
            {"phonetic": "batin", "arabic_script": "الباطن", "decision": "keep"},
        ):
            book = self._book([entry])
            out = pc.compile_turns_for_render(book, [Turn("HOST_A", "the batin within")])
            self.assertIn("الباطن", out[0].text)

    def test_correct_arabic_uses_corrected_script(self):
        book = self._book(
            [
                {
                    "phonetic": "batin",
                    "arabic_script": "WRONG",
                    "decision": "correct_arabic",
                    "corrected_arabic": "الباطن",
                }
            ]
        )
        out = pc.compile_turns_for_render(book, [Turn("HOST_A", "the batin within")])
        self.assertIn("الباطن", out[0].text)
        self.assertNotIn("WRONG", out[0].text)

    def test_fix_phonetic_changes_match_key(self):
        # Script carries "ta'wil"; glossary phonetic was the Arabic form (no match).
        # Human fixes the phonetic so the substitution now fires.
        book = self._book(
            [
                {
                    "phonetic": "تأويل",
                    "arabic_script": "تأويل",
                    "decision": "fix_phonetic",
                    "corrected_phonetic": "ta'wil",
                }
            ]
        )
        out = pc.compile_turns_for_render(book, [Turn("HOST_A", "the ta'wil of the verse")])
        self.assertIn("تأويل", out[0].text)

    def test_replace_english_recites_nothing(self):
        book = self._book([{"phonetic": "batin", "arabic_script": "الباطن", "decision": "replace_english"}])
        out = pc.compile_turns_for_render(book, [Turn("HOST_A", "the batin within")])
        self.assertNotIn("الباطن", out[0].text)
        self.assertIn("batin", out[0].text)

    def test_fill_roundtrip_preserves_decision_fields(self):
        import fill_glossary_arabic as fg

        entries = [
            {
                "phonetic": "batin",
                "transliteration": "batin",
                "arabic_script": "الباطن",
                "audio_phonetic": "BAA-tin",
                "first_seen_snippet": "x",
                "decision": "correct_arabic",
                "corrected_arabic": "الباطنُ",
                "decided_by": "asif",
            }
        ]
        emitted = fg.emit_glossary_yml(entries, {"schema_version": 2})
        self.assertIn('decision: "correct_arabic"', emitted)
        self.assertIn('corrected_arabic: "الباطنُ"', emitted)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = Path(tmp) / "glossary.yml"
        p.write_text(emitted, encoding="utf-8")
        parsed, _top = fg.parse_glossary_yml(p)
        self.assertEqual(parsed[0]["decision"], "correct_arabic")
        self.assertEqual(parsed[0]["corrected_arabic"], "الباطنُ")
        self.assertEqual(parsed[0]["decided_by"], "asif")


class TestClientDictionaryUpload(unittest.TestCase):
    def test_multipart_upload_parses_ids(self):
        from _elevenlabs import ElevenLabsClient

        captured = {}

        def transport(method, url, headers, body, timeout):
            captured.update(method=method, url=url, headers=headers, body=body)
            return 200, json.dumps({"id": "d1", "version_id": "v1"}).encode()

        c = ElevenLabsClient(api_key="k", transport=transport)
        did, vid = c.create_pronunciation_dictionary(name="book-glossary", pls_text="<lexicon/>")
        self.assertEqual((did, vid), ("d1", "v1"))
        self.assertIn("/v1/pronunciation-dictionaries/add-from-file", captured["url"])
        self.assertIn(b"<lexicon/>", captured["body"])
        self.assertIn(b'name="file"', captured["body"])
        # ElevenLabs rejects application/xml on the file part (live 2026-06-12).
        self.assertIn(b"Content-Type: text/plain", captured["body"])
        self.assertNotIn(b"application/xml", captured["body"])

    def test_locator_cap_three(self):
        from _elevenlabs import ElevenLabsClient

        c = ElevenLabsClient(api_key="k", transport=lambda *a: (200, b"{}"))
        with self.assertRaises(ValueError):
            c.text_to_dialogue(
                [{"text": "x", "voice_id": "v"}], model_id="eleven_v3", pronunciation_dictionary_locators=[{}] * 4
            )

    def test_loanword_skip_list(self):
        # Common English loanwords never get alias rules ("Imam" -> "e-Maam"
        # mangled live audio, 2026-06-12); multi-word names keep theirs.
        import pronunciation_compiler as pc

        entries = [
            {"phonetic": "Imam", "audio_phonetic": "e-Maam"},
            {"phonetic": "Sunnah", "audio_phonetic": "SOON-nah"},
            {"phonetic": "Allah", "audio_phonetic": "ahl-LAH"},
            {"phonetic": "Abd Allah", "audio_phonetic": "ab-dul-LAH"},
            {"phonetic": "Sinai", "audio_phonetic": "SEE-nigh"},
        ]
        rules = dict(pc._usable_rules(entries))
        self.assertNotIn("Imam", rules)
        self.assertNotIn("Sunnah", rules)
        self.assertNotIn("Allah", rules)
        self.assertIn("Abd Allah", rules)  # name, not a loanword
        self.assertIn("Sinai", rules)


if __name__ == "__main__":
    unittest.main()
