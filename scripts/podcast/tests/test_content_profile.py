"""
Tests for _content_profile.py (Wave CP).

Validates that resolve_content_profile() returns the correct profile for
various series-config.yaml states, and that the allowed profile set matches
CONTENT_PROFILES in _rules.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from _content_profile import is_islamic_scholarly, resolve_content_profile
from _rules import (
    BUCKETS,
    CONTENT_PROFILES,
    CONTENT_TYPE_REGISTRY,
    ISLAMIC_SCHOLARLY_PROFILE,
    bucket_for_profile,
    literary_voice_for_profile,
)


class TestResolveContentProfile(unittest.TestCase):
    def _make_book(self, tmp: Path, content_profile=None) -> Path:  # type: ignore[assignment]
        """Create a minimal book_dir with _system/series-config.yaml."""
        book = tmp / "book"
        sys_dir = book / "_system"
        sys_dir.mkdir(parents=True)
        cfg: dict = {}
        if content_profile is not None:
            cfg["content_profile"] = content_profile
        (sys_dir / "series-config.yaml").write_text(yaml.dump(cfg))
        return book

    def test_defaults_to_islamic_scholarly_when_no_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "book"
            book.mkdir()
            (book / "_system").mkdir()
            self.assertEqual(resolve_content_profile(book), "islamic_scholarly")

    def test_defaults_to_islamic_scholarly_when_field_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp))  # no content_profile field
            self.assertEqual(resolve_content_profile(book), "islamic_scholarly")

    def test_reads_consumer_explainer(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="consumer_explainer")
            self.assertEqual(resolve_content_profile(book), "consumer_explainer")

    def test_reads_general_nonfiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="general_nonfiction")
            self.assertEqual(resolve_content_profile(book), "general_nonfiction")

    def test_invalid_profile_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="unknown_profile")
            self.assertEqual(resolve_content_profile(book), "islamic_scholarly")

    def test_is_islamic_scholarly_true_for_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "book"
            book.mkdir()
            (book / "_system").mkdir()
            self.assertTrue(is_islamic_scholarly(book))

    def test_is_islamic_scholarly_false_for_consumer(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="consumer_explainer")
            self.assertFalse(is_islamic_scholarly(book))

    def test_content_profiles_derived_from_registry(self):
        # CONTENT_PROFILES is now derived from CONTENT_TYPE_REGISTRY; technical +
        # fiction are first-class (was a hand-maintained 3-tuple before 2026-06-04).
        self.assertEqual(tuple(CONTENT_TYPE_REGISTRY), CONTENT_PROFILES)
        for expected in (
            "islamic_scholarly",
            "technical",
            "fiction",
            "consumer_explainer",
            "general_nonfiction",
            "islamic_supplication",
        ):
            self.assertIn(expected, CONTENT_PROFILES)

    def test_reads_technical_profile(self):
        # Previously fell back to islamic_scholarly (not in the 3-tuple); now valid.
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="technical")
            self.assertEqual(resolve_content_profile(book), "technical")

    def test_reads_fiction_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._make_book(Path(tmp), content_profile="fiction")
            self.assertEqual(resolve_content_profile(book), "fiction")

    def test_islamic_scholarly_profile_constant(self):
        self.assertEqual(ISLAMIC_SCHOLARLY_PROFILE, "islamic_scholarly")


class TestContentTypeRegistry(unittest.TestCase):
    """The single content-type registry: profile→bucket, voice, parity."""

    def test_profile_to_bucket_mapping(self):
        self.assertEqual(bucket_for_profile("islamic_scholarly"), "Islamic")
        self.assertEqual(bucket_for_profile("technical"), "Technical")
        self.assertEqual(bucket_for_profile("fiction"), "Fiction")
        self.assertEqual(bucket_for_profile("consumer_explainer"), "Guides")
        self.assertEqual(bucket_for_profile("general_nonfiction"), "Guides")
        self.assertEqual(bucket_for_profile("islamic_supplication"), "Supplications")

    def test_unknown_or_none_profile_defaults_to_islamic_bucket(self):
        self.assertEqual(bucket_for_profile(None), "Islamic")
        self.assertEqual(bucket_for_profile("nonsense"), "Islamic")

    def test_every_registry_bucket_is_a_known_bucket(self):
        for ct in CONTENT_TYPE_REGISTRY.values():
            self.assertIn(ct.bucket, BUCKETS)

    def test_literary_voice_resolves_per_profile(self):
        self.assertEqual(literary_voice_for_profile("fiction")["narrator_voice"], "narrative_voice")
        self.assertEqual(literary_voice_for_profile("technical")["narrator_voice"], "peer_expert")
        # Unknown profile falls back to the islamic_scholarly voice.
        self.assertEqual(literary_voice_for_profile("nonsense")["narrator_voice"], "author_first_person")

    def test_registry_keys_match_profile_field(self):
        for key, ct in CONTENT_TYPE_REGISTRY.items():
            self.assertEqual(key, ct.profile)


if __name__ == "__main__":
    unittest.main()
