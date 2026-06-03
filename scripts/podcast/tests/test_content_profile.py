"""
Tests for _content_profile.py (Wave CP).

Validates that resolve_content_profile() returns the correct profile for
various series-config.yaml states, and that the allowed profile set matches
CONTENT_PROFILES in _rules.py.
"""

import sys
import unittest
from pathlib import Path
import tempfile
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from _content_profile import resolve_content_profile, is_islamic_scholarly
from _rules import CONTENT_PROFILES, ISLAMIC_SCHOLARLY_PROFILE


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

    def test_content_profiles_constant_has_three_entries(self):
        self.assertEqual(len(CONTENT_PROFILES), 3)
        self.assertIn("islamic_scholarly", CONTENT_PROFILES)
        self.assertIn("consumer_explainer", CONTENT_PROFILES)
        self.assertIn("general_nonfiction", CONTENT_PROFILES)

    def test_islamic_scholarly_profile_constant(self):
        self.assertEqual(ISLAMIC_SCHOLARLY_PROFILE, "islamic_scholarly")


if __name__ == "__main__":
    unittest.main()
