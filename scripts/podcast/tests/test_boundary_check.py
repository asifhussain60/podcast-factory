#!/usr/bin/env python3
"""Tests for scripts/podcast/_boundary_check.py (P1.1 deliverable).

Verifies the AST scan correctly catches forbidden writes and honors the
single whitelisted exception path.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _boundary_check  # noqa: E402


class WhitelistTests(unittest.TestCase):
    def test_whitelisted_abjad_file_passes(self):
        self.assertTrue(
            _boundary_check._is_whitelisted("content/_shared/arabic/06-abjad-numerals.md")
        )

    def test_other_shared_paths_not_whitelisted(self):
        self.assertFalse(
            _boundary_check._is_whitelisted("content/_shared/arabic/01-other.md")
        )
        self.assertFalse(_boundary_check._is_whitelisted("content/_shared/foo.md"))


class ScanFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.scripts_dir = Path(self.tmp.name) / "scripts" / "podcast"
        self.scripts_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.scripts_dir / name
        p.write_text(content)
        return p

    def test_clean_file_zero_violations(self):
        f = self._write("clean.py", "x = 1\ny = open('/tmp/safe.txt', 'w')\nprint(x)\n")
        self.assertEqual(_boundary_check.scan_file(f), [])

    def test_open_w_to_babu_memoir_flagged(self):
        f = self._write(
            "violator.py",
            "f = open('content/babu-memoir/foo.md', 'w')\nf.write('x')\n",
        )
        v = _boundary_check.scan_file(f)
        self.assertEqual(len(v), 1)
        self.assertIn("content/babu-memoir/", v[0].target)

    def test_open_a_to_memoir_scripts_flagged(self):
        f = self._write(
            "writer.py",
            "open('scripts/memoir/util.py', 'a').close()\n",
        )
        v = _boundary_check.scan_file(f)
        self.assertEqual(len(v), 1)

    def test_open_r_only_is_safe(self):
        f = self._write("reader.py", "open('content/babu-memoir/foo.md', 'r').read()\n")
        self.assertEqual(_boundary_check.scan_file(f), [])

    def test_write_text_method_flagged(self):
        f = self._write(
            "wt.py",
            "from pathlib import Path\nPath('content/_shared/x.md').write_text('y')\n",
        )
        v = _boundary_check.scan_file(f)
        self.assertEqual(len(v), 1)
        self.assertIn(".write_text", v[0].reason)

    def test_write_text_to_whitelisted_abjad_is_safe(self):
        f = self._write(
            "abjad.py",
            "from pathlib import Path\n"
            "Path('content/_shared/arabic/06-abjad-numerals.md').write_text('table')\n",
        )
        self.assertEqual(_boundary_check.scan_file(f), [])

    def test_path_open_w_mode_flagged(self):
        f = self._write(
            "pop.py",
            "from pathlib import Path\nPath('scripts/site/foo.py').open('w').close()\n",
        )
        v = _boundary_check.scan_file(f)
        self.assertEqual(len(v), 1)

    def test_syntax_error_surfaces(self):
        f = self._write("broken.py", "def x(:\n  pass\n")
        v = _boundary_check.scan_file(f)
        self.assertEqual(len(v), 1)
        self.assertIn("SyntaxError", v[0].reason)


class ScanTreeTests(unittest.TestCase):
    def test_scan_tree_skips_pycache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "trash.py").write_text(
                "open('content/babu-memoir/x', 'w')\n"
            )
            (root / "real.py").write_text("x = 1\n")
            self.assertEqual(_boundary_check.scan_tree(root), [])

    def test_scan_tree_includes_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "subdir").mkdir()
            (root / "subdir" / "bad.py").write_text(
                "open('content/babu-memoir/x.md', 'w')\n"
            )
            v = _boundary_check.scan_tree(root)
            self.assertEqual(len(v), 1)


class CurrentTreeBaselineTest(unittest.TestCase):
    """The current scripts/podcast/ tree must scan clean — P1.1 acceptance."""

    def test_current_tree_zero_violations(self):
        violations = _boundary_check.scan_tree(_boundary_check.SCRIPTS_PODCAST)
        if violations:
            msg = "\n".join(v.fmt() for v in violations)
            self.fail(f"Current scripts/podcast/ tree has {len(violations)} boundary violations:\n{msg}")


class MainTests(unittest.TestCase):
    def test_main_exits_zero_on_clean(self):
        # main() scans the real tree; baseline is clean.
        self.assertEqual(_boundary_check.main(), 0)


if __name__ == "__main__":
    unittest.main()
