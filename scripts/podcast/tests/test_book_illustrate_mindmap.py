#!/usr/bin/env python3
"""Tests for the Mermaid-mindmap single-root guard in _book_illustrate.

Regression: the classifier prompt used to instruct the LLM that mindmap branches
were "indented 2 spaces" — the SAME indent as the root — which Mermaid parses as
multiple roots and rejects ("multiple roots" render failure). On
al-anwaar-al-lateefah vol-01, 4 generated mindmaps failed to render until their
children were re-indented from 2 to 4 spaces (root at 2, children at 4).

The prompt now teaches deeper nesting, and _normalize_mindmap_dsl is a belt-and-
suspenders guard: whatever the LLM emits, every branch is re-nested under the
root so a stray top-level line can't break the render. These tests pin that
guard and, when a Mermaid renderer is available, assert a real single-root SVG.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _book_illustrate import _normalize_mindmap_dsl, _RENDER_SCRIPT, _DASHBOARD  # noqa: E402


def _root_count(dsl: str) -> int:
    """Count top-level roots in a mindmap DSL the way Mermaid does.

    The first node after the `mindmap` declaration is the root; any later
    non-blank line at the same-or-shallower indent is parsed as ANOTHER root.
    A well-formed mindmap therefore has exactly one such top-level line.
    """
    lines = dsl.splitlines()
    decl = next((i for i, ln in enumerate(lines)
                 if ln.strip().lower() == "mindmap"), None)
    assert decl is not None, "not a mindmap DSL"

    def indent_of(ln: str) -> int:
        return len(ln) - len(ln.lstrip(" "))

    content = [i for i in range(decl + 1, len(lines)) if lines[i].strip()]
    if not content:
        return 0
    root_indent = indent_of(lines[content[0]])
    return sum(1 for i in content if indent_of(lines[i]) <= root_indent)


class NormalizeMindmapTests(unittest.TestCase):
    def test_flat_branches_get_nested_under_root(self) -> None:
        # The exact bug shape: root and branches all at 2-space indent.
        bad = 'mindmap\n  root(("Topic"))\n  Branch1\n  Branch2\n  Branch3'
        self.assertEqual(_root_count(bad), 4, "fixture should reproduce multi-root")
        fixed = _normalize_mindmap_dsl(bad)
        self.assertEqual(_root_count(fixed), 1, f"still multi-root:\n{fixed}")

    def test_already_nested_is_unchanged(self) -> None:
        good = 'mindmap\n  root(("Topic"))\n    Branch1\n    Branch2'
        self.assertEqual(_normalize_mindmap_dsl(good), good)
        self.assertEqual(_root_count(good), 1)

    def test_relative_nesting_among_branches_preserved(self) -> None:
        # Branch2 is a child of Branch1 (deeper). After the shift the parent/child
        # relationship must survive, just nested one level under the root.
        bad = 'mindmap\n  root(("R"))\n  Branch1\n    Branch1a\n  Branch2'
        fixed = _normalize_mindmap_dsl(bad)
        self.assertEqual(_root_count(fixed), 1, fixed)

        def indent_of(ln: str) -> int:
            return len(ln) - len(ln.lstrip(" "))

        lines = fixed.splitlines()
        b1 = next(ln for ln in lines if ln.strip() == "Branch1")
        b1a = next(ln for ln in lines if ln.strip() == "Branch1a")
        self.assertGreater(indent_of(b1a), indent_of(b1),
                           "child must stay deeper than its parent")

    def test_shallower_than_root_still_nested(self) -> None:
        bad = 'mindmap\n    root(("R"))\n  Branch1\n  Branch2'
        fixed = _normalize_mindmap_dsl(bad)
        self.assertEqual(_root_count(fixed), 1, fixed)

    def test_non_mindmap_dsl_untouched(self) -> None:
        flow = 'flowchart TD\nA["Start"] --> B["End"]'
        self.assertEqual(_normalize_mindmap_dsl(flow), flow)

    def test_root_only_untouched(self) -> None:
        only = 'mindmap\n  root(("R"))'
        self.assertEqual(_normalize_mindmap_dsl(only), only)


@unittest.skipUnless(
    _RENDER_SCRIPT.exists() and shutil.which("node"),
    "render-mermaid.mjs / node unavailable — skipping live render assertion",
)
class MindmapRenderTests(unittest.TestCase):
    def test_normalized_mindmap_renders_single_root(self) -> None:
        bad = 'mindmap\n  root(("Topic"))\n  Branch1\n  Branch2\n  Branch3'
        dsl = _normalize_mindmap_dsl(bad)

        book = Path(tempfile.mkdtemp()) / "book"
        diagrams = book / "book" / "_diagrams"
        diagrams.mkdir(parents=True)
        (diagrams / "mm-1.mmd").write_text(dsl, encoding="utf-8")

        proc = subprocess.run(
            ["node", str(_RENDER_SCRIPT), f"--book-dir={book}"],
            cwd=str(_DASHBOARD), capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 3:
            self.skipTest("chromium unavailable for live render")
        self.assertEqual(proc.returncode, 0,
                         f"render failed (multi-root regression?):\n{proc.stderr[:400]}")
        svg = diagrams / "mm-1.svg"
        self.assertTrue(svg.exists(), "renderer produced no SVG")
        # A multi-root failure never reaches a clean SVG; a successful single-root
        # mindmap does. Guard against an empty/garbage file too.
        self.assertIn("<svg", svg.read_text(encoding="utf-8")[:2000])


if __name__ == "__main__":
    unittest.main()
