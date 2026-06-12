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

import pronunciation_compiler as pc  # noqa: E402
from _dialogue_script import Turn  # noqa: E402

ENTRIES = [
    {"phonetic": "Sayyidina", "transliteration": "Sayyidina",
     "arabic_script": "سيدنا",
     "audio_phonetic": "sai-yi-DEE-nah"},
    {"phonetic": "batin", "transliteration": "batin",
     "arabic_script": "الباطن",
     "audio_phonetic": "BAA-tin"},
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
            yaml.safe_dump({"schema_version": 1, "entries": entries}),
            encoding="utf-8")

    def test_upload_once_then_pin(self):
        loc1 = pc.ensure_dictionary(self.book, self.client, log=lambda *a: None)
        self.assertEqual(loc1, {"pronunciation_dictionary_id": "dict-1",
                                "version_id": "ver-1"})
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
        st = json.loads((self.book / "_system" / "pronunciation-dictionary.json")
                        .read_text(encoding="utf-8"))
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
        (self.book / "_system" / "glossary.yml").write_text(
            yaml.safe_dump({"entries": ENTRIES}), encoding="utf-8")
        self.turns = [Turn("HOST_A", "The word Sayyidina opens the line."),
                      Turn("HOST_B", "And batin stays hidden.")]

    def test_default_off_is_identity(self):
        self.assertFalse(pc.arabic_recitation_enabled(self.book))
        out = pc.compile_turns_for_render(self.book, self.turns)
        self.assertEqual(out, self.turns)

    def test_flag_on_substitutes_arabic_script(self):
        (self.book / "_system" / "series-config.yaml").write_text(
            "elevenlabs_arabic_recitation: true\n", encoding="utf-8")
        self.assertTrue(pc.arabic_recitation_enabled(self.book))
        out = pc.compile_turns_for_render(self.book, self.turns)
        self.assertIn("سيدنا", out[0].text)
        self.assertIn("الباطن", out[1].text)
        # Source turns untouched (render-layer only).
        self.assertIn("Sayyidina", self.turns[0].text)


class TestClientDictionaryUpload(unittest.TestCase):
    def test_multipart_upload_parses_ids(self):
        from _elevenlabs import ElevenLabsClient
        captured = {}

        def transport(method, url, headers, body, timeout):
            captured.update(method=method, url=url, headers=headers, body=body)
            return 200, json.dumps({"id": "d1", "version_id": "v1"}).encode()

        c = ElevenLabsClient(api_key="k", transport=transport)
        did, vid = c.create_pronunciation_dictionary(
            name="book-glossary", pls_text="<lexicon/>")
        self.assertEqual((did, vid), ("d1", "v1"))
        self.assertIn("/v1/pronunciation-dictionaries/add-from-file", captured["url"])
        self.assertIn(b"<lexicon/>", captured["body"])
        self.assertIn(b'name="file"', captured["body"])

    def test_locator_cap_three(self):
        from _elevenlabs import ElevenLabsClient
        c = ElevenLabsClient(api_key="k", transport=lambda *a: (200, b"{}"))
        with self.assertRaises(ValueError):
            c.text_to_dialogue(
                [{"text": "x", "voice_id": "v"}], model_id="eleven_v3",
                pronunciation_dictionary_locators=[{}] * 4)


if __name__ == "__main__":
    unittest.main()
