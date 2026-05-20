#!/usr/bin/env python3
"""Tests for the Phase 0b refinement prompt's page-marker preservation guarantee.

Acceptance row: P22.markers.fixture (acceptance-criteria.md §P22.markers).

Background — asaas-al-taveel Phase 0b post-mortem 2026-05-20:
    Of 49 chunked refinement windows, 7 (003, 007, 016, 019, 029, 038, 039)
    emitted 0 page markers from inputs containing 7-10 each. Net: 58/416 page
    anchors missing from refined-english.md. Plus 1 hallucinated marker in
    win-010, 1 lost marker each in win-046 and win-049.

    Body text was preserved across all 416 pages (verified by sampling each
    gap region — John 15:26-27 quote at L7135, al-Nu'man's preamble at L213,
    Dawud/Sulayman judgment quote at L5316). The defect is metadata loss,
    not content loss. Root cause: Phase 0b refinement prompt template did
    not enforce verbatim preservation of `<!-- page N -->` HTML comments;
    LLM "tidied" them out during heavy prose passages.

This test pins the prompt's page-marker invariant. It is intentionally
ASSERTION-HEAVY (tests for the exact instruction text, not just generic
"page" mentions) so a future prompt refactor cannot accidentally re-introduce
the bug — the test would fail loudly if the preservation language is
deleted, weakened, or moved into a sub-clause where the LLM might overlook it.

Runs in <5s with zero `claude -p` invocations (pure prompt-string assertion).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _authoring  # noqa: E402


class Phase0bPromptPageMarkerTests(unittest.TestCase):
    """The Phase 0b window-refinement prompt must instruct the LLM to
    preserve every ``<!-- page N -->`` HTML comment verbatim."""

    def setUp(self) -> None:
        self.prompt = _authoring.build_phase_0b_window_prompt(
            book_slug="test-book",
            idx=1,
            total=5,
            win_in=Path("/tmp/win-001.in.md"),
            win_out=Path("/tmp/win-001.out.md"),
        )

    def test_prompt_mentions_page_marker_syntax(self) -> None:
        """The literal token ``<!-- page N -->`` must appear in the prompt
        (so the LLM knows the exact pattern it is being asked to preserve)."""
        self.assertIn(
            "<!-- page",
            self.prompt,
            msg=(
                "Phase 0b prompt does not reference the `<!-- page N -->` "
                "syntax — LLM has no signal that page markers exist as a "
                "distinct artifact class to preserve. Add an explicit "
                "preservation constraint to build_phase_0b_window_prompt()."
            ),
        )

    def test_prompt_uses_preservation_verb(self) -> None:
        """A strong preservation verb (preserve / keep / retain / verbatim /
        do NOT remove / do NOT omit / do NOT collapse) must appear within
        the same paragraph block as the page-marker mention.

        The verb co-located with the marker syntax is what tells the LLM the
        instruction is binding. Without it, the marker reference reads as
        descriptive ("the input has these comments") rather than prescriptive
        ("you must keep them"). Using a paragraph-scope window rather than a
        single-sentence window because a binding instruction is often
        structured as "Concept introduction. Binding rule." across two
        sentences.
        """
        # Find every paragraph (double-newline block) that mentions page markers.
        paragraphs = self.prompt.split("\n\n")
        page_paragraphs = [p for p in paragraphs if "<!-- page" in p]
        self.assertGreater(
            len(page_paragraphs),
            0,
            msg="No paragraph references `<!-- page` syntax in the prompt.",
        )

        preservation_verbs = ("preserve", "keep", "retain", "do not remove",
                              "do not omit", "do not collapse", "verbatim")
        # At least one of the page-mentioning paragraphs must use a strong verb.
        verb_present = any(
            any(verb in p.lower() for verb in preservation_verbs)
            for p in page_paragraphs
        )
        self.assertTrue(
            verb_present,
            msg=(
                f"No paragraph mentioning page markers contains a strong "
                f"preservation verb {preservation_verbs}. Paragraphs were: "
                f"{page_paragraphs!r}"
            ),
        )

    def test_prompt_forbids_collapse_renumber_invent(self) -> None:
        """The instruction must explicitly forbid the three failure modes
        observed in the asaas post-mortem: collapsing adjacent markers,
        renumbering them, or inventing new ones.

        Hallucinated markers (one observed in asaas win-010) cause downstream
        Loop N citation drift; collapsed markers (the 7 zero-marker windows)
        cause anchoring loss. Both need explicit prohibition.
        """
        lower = self.prompt.lower()
        forbidden_actions = ["collapse", "renumber", "invent", "omit"]
        missing = [verb for verb in forbidden_actions if verb not in lower]
        self.assertEqual(
            missing,
            [],
            msg=(
                f"Phase 0b prompt does not forbid the failure modes "
                f"{missing!r} that the asaas post-mortem identified as "
                f"recurring. Add explicit DO-NOT clauses to "
                f"build_phase_0b_window_prompt()."
            ),
        )

    def test_prompt_specifies_position_preservation(self) -> None:
        """The instruction must also require the markers stay in their
        original relative positions in the refined output, not just be
        emitted somewhere. Without this, the LLM might preserve marker
        counts but cluster them at the start/end, breaking citation
        anchoring for body text.
        """
        lower = self.prompt.lower()
        position_signals = ("same position", "same relative position",
                            "at the same", "where they appear",
                            "where it appears", "in place", "in-place",
                            "in their original position",
                            "at the same relative position")
        self.assertTrue(
            any(signal in lower for signal in position_signals),
            msg=(
                "Phase 0b prompt does not require page markers stay at "
                "their original relative position. Without this, the LLM "
                "may preserve marker counts but cluster them at the start/"
                "end, breaking anchoring for body text. Add a position "
                "preservation clause."
            ),
        )


class Phase0bPromptStructureTests(unittest.TestCase):
    """Sanity checks on the prompt's existing contract — these should pass
    against both pre-fix and post-fix templates. They guard against
    accidental regression in unrelated parts of the prompt during the
    P22.markers fix."""

    def setUp(self) -> None:
        self.prompt = _authoring.build_phase_0b_window_prompt(
            book_slug="test-book",
            idx=3,
            total=10,
            win_in=Path("/tmp/in.md"),
            win_out=Path("/tmp/out.md"),
        )

    def test_includes_window_position(self) -> None:
        self.assertIn("window 3 of 10", self.prompt)

    def test_includes_book_slug(self) -> None:
        self.assertIn("test-book", self.prompt)

    def test_input_output_paths_resolve(self) -> None:
        self.assertIn("/tmp/in.md", self.prompt)
        self.assertIn("/tmp/out.md", self.prompt)

    def test_forbids_invention(self) -> None:
        self.assertIn("Do NOT invent content", self.prompt)


if __name__ == "__main__":
    unittest.main()
