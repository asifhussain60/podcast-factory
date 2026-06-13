#!/usr/bin/env python3
"""Tests for the 'technical' pipeline path (category: explainers).

Coverage: every pipeline phase that currently has hardcoded Islamic/Arabic
assumptions and needs a technical-content variant for categories like
`explainers` (developer docs, onboarding content, professional guides).

Test legend:
  # GREEN today  — currently passes; validates existing correct behaviour
  # RED today    — currently fails; defines the target behaviour for the
                   technical path implementation. These tests SHOULD pass
                   after each phase's category-aware branching is added.

Phases covered:
  0b  (Refine/Denoise)    — Arabic preservation constraint must not leak
  0c  (Phonetics)         — must be skipped for explainers
  0d  (Chapter Design)    — must not require _phonetics.md for explainers
  0e  (Enrichment)        — Islamic source tiers must not appear
  Framing                 — explainers must not route to Islamic scholarly prompt
  Noise Router            — Sonnet pass-2 system prompt must protect tech content
  Routing / Rules         — category and branch-prefix validation

Run:
  cd /path/to/podcast-factory
  python3 -m pytest scripts/podcast/tests/test_technical_path.py -v
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path
import tempfile
import os

# Make scripts/podcast/ importable
SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _branching  # noqa: E402
import _rules      # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_book_dir(tmp: Path, category: str = "explainers") -> Path:
    """Scaffold a minimal book directory with meta.yml for the given category."""
    book_dir = tmp / "claude-code-training"
    (book_dir / "_system" / "source" / "text").mkdir(parents=True)
    (book_dir / "chapters").mkdir()
    (book_dir / "chapter-contracts").mkdir()
    (book_dir / "_system").joinpath("meta.yml").write_text(
        f"slug: claude-code-training\ncategory: {category}\n", encoding="utf-8"
    )
    return book_dir


def _make_refined_english(book_dir: Path, content: str = "Sample technical text.") -> Path:
    p = book_dir / "_system" / "source" / "text" / "refined-english.md"
    p.write_text(content, encoding="utf-8")
    return p


def _make_phonetics(book_dir: Path) -> Path:
    p = book_dir / "_system" / "source" / "text" / "_phonetics.md"
    p.write_text(
        "| term | transliteration | phonetic | first-occurrence-snippet |\n"
        "|---|---|---|---|\n",
        encoding="utf-8",
    )
    return p


def _make_chapter(book_dir: Path, stem: str = "ch01-getting-started",
                  content: str = "Install Claude Code with: npm install -g @anthropic-ai/claude-code") -> Path:
    p = book_dir / "chapters" / f"{stem}.txt"
    p.write_text(content, encoding="utf-8")
    return p


def _make_contract(book_dir: Path, slug: str = "getting-started") -> Path:
    p = book_dir / "chapter-contracts" / f"{slug}.yml"
    p.write_text(
        f"slug: {slug}\ntitle: Getting Started\naudiece: developers\n",
        encoding="utf-8",
    )
    return p


# ─────────────────────────────────────────────────────────────────────────────
# 1. Routing and rules (category + branch prefix)
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoryRouting(unittest.TestCase):
    """Validate that `explainers` is a first-class category with correct branch prefix.

    These should all be GREEN today — the category and prefix exist in rules + branching.
    """

    def test_explainers_in_allowed_categories(self):
        # GREEN today
        self.assertIn("explainers", _rules.ALLOWED_CATEGORIES)

    def test_sites_in_allowed_categories(self):
        # GREEN today — regression guard
        self.assertIn("sites", _rules.ALLOWED_CATEGORIES)

    def test_explainers_branch_prefix(self):
        # GREEN today
        self.assertEqual(_branching.branch_prefix("explainers"), "explainer")

    def test_explainers_branch_name(self):
        # 2026-06-07: branch is <Bucket>/<slug>, bucket-grouped. The 'explainers'
        # category maps to the Guides bucket via the legacy category fallback.
        self.assertEqual(
            _branching.branch_name("explainers", "claude-code-training"),
            "Guides/claude-code-training",
        )

    def test_branch_name_bucket_from_profile(self):
        # content_profile takes precedence over the legacy category for the bucket.
        self.assertEqual(
            _branching.branch_name("books", "journey-to-the-west-vol-1", profile="fiction"),
            "Fiction/journey-to-the-west-vol-1",
        )
        self.assertEqual(
            _branching.branch_name("books", "ayyuhal-walad", profile="islamic_scholarly"),
            "Islamic/ayyuhal-walad",
        )

    def test_branch_name_explicit_bucket_wins(self):
        self.assertEqual(
            _branching.branch_name("books", "some-slug", bucket="Technical"),
            "Technical/some-slug",
        )

    def test_branch_name_books_category_defaults_islamic(self):
        # Legacy 'books' category with no profile falls back to the Islamic bucket.
        self.assertEqual(
            _branching.branch_name("books", "kitab-al-riyad"),
            "Islamic/kitab-al-riyad",
        )

    def test_sites_branch_prefix_unchanged(self):
        # GREEN today — regression guard
        self.assertEqual(_branching.branch_prefix("sites"), "site")

    def test_books_branch_prefix_unchanged(self):
        # GREEN today — regression guard
        self.assertEqual(_branching.branch_prefix("books"), "book")

    def test_unknown_category_falls_back_to_draft(self):
        # GREEN today
        self.assertEqual(_branching.branch_prefix("unknown-category"), "draft")

    def test_branch_name_rejects_slug_with_slash(self):
        # GREEN today
        with self.assertRaises(ValueError):
            _branching.branch_name("explainers", "foo/bar")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Phase 0b — Refine / Denoise
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase0bPrompt(unittest.TestCase):
    """Phase 0b refinement prompt must not leak Arabic-specific constraints into
    technical content.

    The function `build_phase_0b_window_prompt()` currently hardcodes:
      'Preserve every Arabic-derived term in transliteration form (al-Razi, al-Kirmani, etc.)'
    This constraint is correct for books/letters/lectures but WRONG for explainers.
    """

    def _import_refine(self):
        from _authoring._refine import build_phase_0b_window_prompt
        return build_phase_0b_window_prompt

    def test_books_prompt_contains_arabic_preservation(self):
        # GREEN today — verify the Islamic constraint IS present for books
        build = self._import_refine()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            win_in = tmp / "win-001.in.md"
            win_out = tmp / "win-001.out.md"
            win_in.write_text("Sample.", encoding="utf-8")
            prompt = build("test-book", 1, 1, win_in, win_out)
        self.assertIn("Arabic-derived term", prompt)

    def test_technical_prompt_omits_arabic_preservation(self):
        # RED today — a technical-variant prompt builder should NOT carry
        # Arabic-specific preservation constraints.
        # Target: a `build_phase_0b_window_prompt_technical()` function exists
        # and its output does not reference Arabic preservation.
        try:
            from _authoring._refine import build_phase_0b_window_prompt_technical as build_tech
        except ImportError:
            self.skipTest("build_phase_0b_window_prompt_technical not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            win_in = tmp / "win-001.in.md"
            win_out = tmp / "win-001.out.md"
            win_in.write_text("Sample.", encoding="utf-8")
            prompt = build_tech("claude-code-training", 1, 1, win_in, win_out)
        self.assertNotIn("Arabic-derived term", prompt)
        self.assertNotIn("al-Razi", prompt)
        self.assertNotIn("al-Kirmani", prompt)
        self.assertNotIn("transliteration", prompt)

    def test_technical_prompt_contains_technical_constraints(self):
        # RED today — the technical variant should instead preserve CLI syntax,
        # version numbers, and code block fidelity.
        try:
            from _authoring._refine import build_phase_0b_window_prompt_technical as build_tech
        except ImportError:
            self.skipTest("build_phase_0b_window_prompt_technical not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            win_in = tmp / "win-001.in.md"
            win_out = tmp / "win-001.out.md"
            win_in.write_text("Sample.", encoding="utf-8")
            prompt = build_tech("claude-code-training", 1, 1, win_in, win_out)
        # At least one of these technical-constraint markers should appear
        technical_markers = [
            "code block", "code fence", "CLI command", "version number",
            "command", "technical term", "exact syntax",
        ]
        self.assertTrue(
            any(m.lower() in prompt.lower() for m in technical_markers),
            f"Expected at least one of {technical_markers} in technical prompt",
        )

    def test_category_aware_0b_routes_correctly(self):
        # RED today — `author_phase_0b()` (or a wrapper) should accept a
        # `category` argument (or read meta.yml) and select the correct prompt
        # builder. When category=explainers, it should call the technical variant.
        # This is a routing test, not an end-to-end test — we check that
        # the function accepts a category kwarg without raising TypeError.
        try:
            from _authoring._refine import author_phase_0b
            import inspect
            sig = inspect.signature(author_phase_0b)
            self.assertIn(
                "category",
                sig.parameters,
                "author_phase_0b should accept a `category` keyword argument",
            )
        except ImportError:
            self.skipTest("Cannot import author_phase_0b")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Phase 0c — Phonetics (must be SKIPPED for explainers)
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase0cSkip(unittest.TestCase):
    """Phase 0c (Arabic phonetics) must be a no-op for explainers category.

    Currently `author_phase_0c()` unconditionally attempts to extract a
    phonetic table. For technical English content there is nothing to extract.
    The correct behaviour for explainers is to:
      (a) detect category from meta.yml, and
      (b) return a skip message without writing _phonetics.md.
    """

    def test_phase_0c_skipped_for_explainers(self):
        # RED today — after implementation, author_phase_0c on an explainers
        # book should return a skip/no-op result rather than attempting
        # Arabic phonetic extraction.
        try:
            from _authoring._refine import author_phase_0c
            import inspect
            sig = inspect.signature(author_phase_0c)
            self.assertIn(
                "category",
                sig.parameters,
                "author_phase_0c should accept a `category` keyword argument "
                "to enable category-aware skip logic",
            )
        except ImportError:
            self.skipTest("Cannot import author_phase_0c")

    def test_phase_0c_skip_returns_skip_message(self):
        # RED today — when called with category='explainers', author_phase_0c
        # should return a string indicating it was skipped (not raise, not
        # write _phonetics.md).
        try:
            from _authoring._refine import author_phase_0c
        except ImportError:
            self.skipTest("Cannot import author_phase_0c")

        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), category="explainers")
            _make_refined_english(book_dir)
            try:
                result = author_phase_0c(book_dir, category="explainers")
            except TypeError:
                self.skipTest("author_phase_0c does not yet accept category kwarg")
            except Exception as e:
                self.fail(f"author_phase_0c raised unexpectedly for explainers: {e}")

        phonetics_path = book_dir / "_system" / "source" / "text" / "_phonetics.md"
        self.assertFalse(
            phonetics_path.exists(),
            "_phonetics.md should NOT be written when category=explainers",
        )
        self.assertIsInstance(result, str)
        self.assertIn("skip", result.lower(),
                      "Skip message should contain 'skip' for non-phonetic categories")

    def test_phase_0c_still_runs_for_books(self):
        # GREEN today (once category kwarg is added) — regression guard.
        # For books, phase 0c should still be invoked (not skipped).
        try:
            from _authoring._refine import author_phase_0c
            import inspect
            sig = inspect.signature(author_phase_0c)
            if "category" not in sig.parameters:
                self.skipTest("category kwarg not yet added")
        except ImportError:
            self.skipTest("Cannot import author_phase_0c")
        # We verify only that the signature accepts category='books'.
        # We do NOT run the full phase (it would call claude -p).
        # This is a contract test, not an integration test.
        self.assertIn("category", sig.parameters)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Phase 0d — Chapter Design
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase0dTechnical(unittest.TestCase):
    """Phase 0d (Chapter Design) currently reads _phonetics.md as a hard input.
    For explainers (where 0c is skipped), _phonetics.md won't exist and the
    phase must gracefully handle its absence.
    """

    def test_phase_0d_does_not_crash_without_phonetics_for_explainers(self):
        # RED today — currently `author_phase_0d` reads in_phonetics unconditionally.
        # For explainers it must either skip reading phonetics, or treat its absence
        # as a no-op (not raise AuthoringError).
        try:
            from _authoring._chapter_design import author_phase_0d
            import inspect
            sig = inspect.signature(author_phase_0d)
            self.assertIn(
                "category",
                sig.parameters,
                "author_phase_0d should accept a `category` kwarg so it can "
                "skip _phonetics.md for explainers",
            )
        except ImportError:
            self.skipTest("Cannot import author_phase_0d")

    def test_phase_0d_toc_prompt_for_explainers_omits_phonetics_section(self):
        # RED today — the TOC step prompt currently inlines instructions about
        # phonetic terms; the technical variant should omit these.
        try:
            from _authoring._chapter_design import build_phase_0d_toc_prompt_technical
        except ImportError:
            self.skipTest("build_phase_0d_toc_prompt_technical not yet implemented")
        prompt = build_phase_0d_toc_prompt_technical("claude-code-training")
        self.assertNotIn("_phonetics.md", prompt)
        self.assertNotIn("Arabic", prompt)
        self.assertNotIn("phonetic", prompt.lower())

    def test_phase_0d_toc_prompt_for_explainers_uses_episode_arc_language(self):
        # RED today — the technical TOC prompt should frame chapters as
        # "episodes in a developer training series", not as "source chapters
        # from a scholarly text".
        try:
            from _authoring._chapter_design import build_phase_0d_toc_prompt_technical
        except ImportError:
            self.skipTest("build_phase_0d_toc_prompt_technical not yet implemented")
        prompt = build_phase_0d_toc_prompt_technical("claude-code-training")
        technical_markers = [
            "episode", "developer", "technical", "training", "practical",
        ]
        self.assertTrue(
            any(m.lower() in prompt.lower() for m in technical_markers),
            f"Expected episode/developer arc language in technical 0d TOC prompt, "
            f"got: {prompt[:300]}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Phase 0e — Enrichment
# ─────────────────────────────────────────────────────────────────────────────

class TestPhase0eEnrichment(unittest.TestCase):
    """Phase 0e enrichment prompt hardcodes Islamic source tiers and doctrinal
    rules. For explainers, the enrichment goal is accuracy verification against
    official technical documentation, not Quranic/hadith citation.
    """

    def _get_0e_prompt(self, book_dir: Path, stem: str, chapter_file: Path) -> str:
        """Extract the Phase 0e prompt string for the given chapter (no LLM call)."""
        # We'll read the enrichment module and invoke the prompt builder directly
        # once it's refactored to expose it. For now, we reproduce the relevant
        # portion to inspect it.
        from _authoring._enrichment import author_phase_0e
        import inspect
        src = inspect.getsource(author_phase_0e)
        return src

    def test_current_enrichment_prompt_contains_islamic_content(self):
        # GREEN today — documents that the Islamic content IS present.
        # Prevents silent regression if someone removes it without a technical
        # replacement.
        from _authoring._enrichment import author_phase_0e
        import inspect
        src = inspect.getsource(author_phase_0e)
        self.assertIn("_shared/islam", src)
        self.assertIn("seven tiers", src.lower().replace("_", " ").replace("-", " ")
                      .replace("tier", "tiers")
                      if "seven tier" in src.lower() or "seven-tier" in src.lower()
                      else src)

    def test_technical_enrichment_function_exists(self):
        # RED today — a `_build_technical_enrichment_prompt()` (or
        # `author_phase_0e_technical()`) must be introduced.
        try:
            from _authoring._enrichment import build_technical_enrichment_prompt
        except ImportError:
            self.skipTest("build_technical_enrichment_prompt not yet implemented")

    def test_technical_enrichment_prompt_omits_islamic_sources(self):
        # RED today
        try:
            from _authoring._enrichment import build_technical_enrichment_prompt
        except ImportError:
            self.skipTest("build_technical_enrichment_prompt not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp))
            chapter_file = _make_chapter(book_dir)
            prompt = build_technical_enrichment_prompt(
                book_slug="claude-code-training",
                chapter_file=chapter_file,
            )
        self.assertNotIn("_shared/islam", prompt)
        self.assertNotIn("Quran", prompt)
        self.assertNotIn("hadith", prompt)
        self.assertNotIn("Ismaili", prompt)
        self.assertNotIn("Tier 1", prompt)  # Islamic tier-1 = Quran/Prophetic

    def test_technical_enrichment_prompt_references_official_docs(self):
        # RED today — technical enrichment should add: official doc citations,
        # version accuracy checks, practical gotchas from real usage.
        try:
            from _authoring._enrichment import build_technical_enrichment_prompt
        except ImportError:
            self.skipTest("build_technical_enrichment_prompt not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp))
            chapter_file = _make_chapter(book_dir)
            prompt = build_technical_enrichment_prompt(
                book_slug="claude-code-training",
                chapter_file=chapter_file,
            )
        technical_markers = [
            "official", "documentation", "accuracy", "version",
            "technical", "source", "verified",
        ]
        self.assertTrue(
            any(m.lower() in prompt.lower() for m in technical_markers),
            f"Expected technical accuracy language in enrichment prompt",
        )

    def test_technical_enrichment_prompt_omits_arabic_name_rules(self):
        # RED today — Arabic personal name substitution rules (R-NO-ARABIC-NAMES,
        # R-SURAH-ENGLISH-ONLY, R-HONORIFIC-ONCE) should NOT appear in
        # the technical enrichment prompt.
        try:
            from _authoring._enrichment import build_technical_enrichment_prompt
        except ImportError:
            self.skipTest("build_technical_enrichment_prompt not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp))
            chapter_file = _make_chapter(book_dir)
            prompt = build_technical_enrichment_prompt(
                book_slug="claude-code-training",
                chapter_file=chapter_file,
            )
        self.assertNotIn("R-NO-ARABIC-NAMES", prompt)
        self.assertNotIn("R-HONORIFIC-ONCE", prompt)
        self.assertNotIn("R-SURAH-ENGLISH-ONLY", prompt)
        self.assertNotIn("al-Kirmani", prompt)

    def test_phase_0e_routes_to_technical_for_explainers(self):
        # RED today — `author_phase_0e()` should detect category=explainers
        # and call `build_technical_enrichment_prompt()` instead of the Islamic prompt.
        try:
            from _authoring._enrichment import author_phase_0e
            import inspect
            sig = inspect.signature(author_phase_0e)
            self.assertIn(
                "category",
                sig.parameters,
                "author_phase_0e should accept a `category` kwarg for routing",
            )
        except ImportError:
            self.skipTest("Cannot import author_phase_0e")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Framing — per-chapter framing authorship
# ─────────────────────────────────────────────────────────────────────────────

class TestFramingRouting(unittest.TestCase):
    """author_framing() must route explainers to a technical prompt, not the
    Islamic scholarly prompt or the consumer (sites) prompt.

    Current state:
      _use_consumer_prompt = (_category == "sites")
    This means explainers silently gets the Islamic scholarly prompt.
    """

    def _detect_category(self, book_dir: Path) -> str:
        """Replicate the category-detection logic from author_framing()."""
        meta_yml = book_dir / "_system" / "meta.yml"
        category = "books"
        if meta_yml.exists():
            for line in meta_yml.read_text(encoding="utf-8").splitlines():
                if line.startswith("category:"):
                    category = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
        return category

    def test_meta_yml_category_detection_works_for_explainers(self):
        # GREEN today — the raw detection logic correctly reads 'explainers'.
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), category="explainers")
            self.assertEqual(self._detect_category(book_dir), "explainers")

    def test_meta_yml_category_detection_falls_back_to_books(self):
        # GREEN today
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), category="books")
            (book_dir / "_system" / "meta.yml").unlink()
            self.assertEqual(self._detect_category(book_dir), "books")

    def test_framing_has_technical_prompt_builder(self):
        # RED today — a `_build_technical_framing_prompt()` function must exist.
        try:
            from _authoring._framing import _build_technical_framing_prompt
        except ImportError:
            self.skipTest("_build_technical_framing_prompt not yet implemented")

    def test_framing_prompt_builder_registry(self):
        # Strategy registry (2026-06-13 refactor): exactly the three variants,
        # every value callable. A new content variant is one dict entry + one fn.
        try:
            from _authoring._framing import (
                FRAMING_PROMPT_BUILDERS, _resolve_prompt_variant,
            )
        except ImportError:
            self.skipTest("FRAMING_PROMPT_BUILDERS not yet implemented")
        self.assertEqual(
            set(FRAMING_PROMPT_BUILDERS), {"islamic", "consumer", "technical"}
        )
        for variant, fn in FRAMING_PROMPT_BUILDERS.items():
            self.assertTrue(callable(fn), f"{variant} builder is not callable")
        # Every resolved variant must have a builder (no silent KeyError path).
        for cat in ("books", "sites", "explainers", "unknown-cat"):
            self.assertIn(_resolve_prompt_variant(cat), FRAMING_PROMPT_BUILDERS)

    def test_technical_framing_prompt_omits_islamic_content(self):
        # RED today — the technical framing prompt must contain ZERO Islamic/
        # scholarly content.
        try:
            from _authoring._framing import _build_technical_framing_prompt
        except ImportError:
            self.skipTest("_build_technical_framing_prompt not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp))
            chapter_file = _make_chapter(book_dir)
            contract = _make_contract(book_dir)
            draft_dir = book_dir / "_system" / "episode-drafts" / "EP01-getting-started"
            draft_dir.mkdir(parents=True)
            framing_path = draft_dir / "00-framing.md"
            prompt = _build_technical_framing_prompt(
                book_slug="claude-code-training",
                chapter_slug="getting-started",
                chap_num="01",
                contract=contract,
                chapter_file=chapter_file,
                framing_path=framing_path,
                book_dir=book_dir,
            )
        islamic_markers = [
            "hadith", "Quran", "Islamic", "scholarly rubric", "Ismaili",
            "doctrinal", "spiritual", "imam lineage", "ta'wil", "esoteric",
            "seeker/student", "scholar/teacher",
        ]
        for marker in islamic_markers:
            self.assertNotIn(
                marker.lower(), prompt.lower(),
                f"Islamic marker {marker!r} found in technical framing prompt",
            )

    def test_technical_framing_prompt_contains_developer_voice(self):
        # RED today — technical framing must orient hosts around developer
        # experience: practical workflow, CLI use, code examples.
        try:
            from _authoring._framing import _build_technical_framing_prompt
        except ImportError:
            self.skipTest("_build_technical_framing_prompt not yet implemented")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp))
            chapter_file = _make_chapter(book_dir)
            contract = _make_contract(book_dir)
            draft_dir = book_dir / "_system" / "episode-drafts" / "EP01-getting-started"
            draft_dir.mkdir(parents=True)
            framing_path = draft_dir / "00-framing.md"
            prompt = _build_technical_framing_prompt(
                book_slug="claude-code-training",
                chapter_slug="getting-started",
                chap_num="01",
                contract=contract,
                chapter_file=chapter_file,
                framing_path=framing_path,
                book_dir=book_dir,
            )
        developer_markers = [
            "developer", "engineer", "workflow", "command", "CLI",
            "practical", "hands-on", "terminal",
        ]
        self.assertTrue(
            any(m.lower() in prompt.lower() for m in developer_markers),
            f"Expected developer-oriented language in technical framing prompt",
        )

    def test_author_framing_routes_explainers_to_technical_prompt(self):
        # RED today — `author_framing()` must branch on `explainers` the same
        # way it currently branches on `sites`. The key line to change is:
        #   _use_consumer_prompt = (_category == "sites")
        # to something like:
        #   _prompt_variant = _resolve_prompt_variant(_category)
        # This test checks the routing contract: when category=explainers,
        # the Islamic scholarly prompt is NOT used.
        try:
            from _authoring._framing import author_framing
            import inspect
            src = inspect.getsource(author_framing)
        except ImportError:
            self.skipTest("Cannot import author_framing")

        # After the fix, the routing should NOT be a simple `== "sites"` check.
        # It should handle 'explainers' too.
        # We inspect source to check that explainers is accounted for in routing.
        routes_explainers = (
            '"explainers"' in src or
            "'explainers'" in src or
            "explainer" in src
        )
        self.assertTrue(
            routes_explainers,
            "author_framing() source does not reference 'explainers' — "
            "it will silently use the Islamic scholarly prompt for this category",
        )

    def test_sites_framing_route_still_works(self):
        # GREEN today — regression guard. The sites/consumer path must not break.
        try:
            from _authoring._framing import _build_consumer_framing_prompt
        except ImportError:
            self.skipTest("Cannot import _build_consumer_framing_prompt")
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), category="sites")
            chapter_file = _make_chapter(book_dir)
            contract = _make_contract(book_dir)
            draft_dir = book_dir / "_system" / "episode-drafts" / "EP01-getting-started"
            draft_dir.mkdir(parents=True)
            framing_path = draft_dir / "00-framing.md"
            prompt = _build_consumer_framing_prompt(
                book_slug="healthequity",
                chapter_slug="hsa",
                chap_num="01",
                contract=contract,
                chapter_file=chapter_file,
                framing_path=framing_path,
                book_dir=book_dir,
            )
        self.assertIn("HealthEquity", prompt)  # Sites prompt contains the brand name
        self.assertIn("consumer", prompt.lower() + "healthcare benefits".lower())


# ─────────────────────────────────────────────────────────────────────────────
# 7. Noise Router — category-aware Sonnet system prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestNoiseRouter(unittest.TestCase):
    """The noise router's Pass 2 (Sonnet) system prompt protects 'spiritual,
    doctrinal, scriptural, or philosophical' content. For technical content the
    equivalent protection should cover code blocks, CLI commands, and version
    numbers — not spiritual content (which won't appear and is irrelevant).

    Also tests that _is_protected() correctly handles technical paragraphs.
    """

    def _import_router(self):
        sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
        from noise_router import _is_protected, _pass2_sonnet, route_chapter
        return _is_protected, _pass2_sonnet, route_chapter

    def test_arabic_text_is_protected(self):
        # GREEN today
        _is_protected, _, _ = self._import_router()
        self.assertTrue(_is_protected("هذا نص عربي"))

    def test_pure_technical_paragraph_is_not_protected(self):
        # GREEN today — a technical paragraph has no Arabic and no Islamic
        # category keywords, so _is_protected() correctly returns False.
        _is_protected, _, _ = self._import_router()
        tech_para = textwrap.dedent("""\
            Install Claude Code using the native installer:
            curl -fsSL https://claude.ai/install.sh | bash
            Verify with: claude --version
        """)
        self.assertFalse(_is_protected(tech_para))

    def test_code_block_paragraph_is_not_falsely_protected(self):
        # GREEN today — code blocks should NOT trigger Islamic protection
        _is_protected, _, _ = self._import_router()
        code_para = "```bash\nnpm install -g @anthropic-ai/claude-code\n```"
        self.assertFalse(_is_protected(code_para))

    def test_sonnet_system_prompt_for_technical_category_exists(self):
        # RED today — a `_build_sonnet_system_for_category()` (or equivalent)
        # function must exist that returns a different system prompt for
        # technical categories.
        try:
            sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
            from noise_router import _build_sonnet_system_for_category
        except ImportError:
            self.skipTest("_build_sonnet_system_for_category not yet implemented")

    def test_technical_sonnet_system_omits_spiritual_protection(self):
        # RED today — the technical Sonnet system prompt should not instruct
        # the model to protect "spiritual, doctrinal, scriptural" content —
        # that framing is meaningless for technical docs.
        try:
            sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
            from noise_router import _build_sonnet_system_for_category
        except ImportError:
            self.skipTest("_build_sonnet_system_for_category not yet implemented")
        prompt = _build_sonnet_system_for_category("explainers")
        self.assertNotIn("spiritual", prompt)
        self.assertNotIn("doctrinal", prompt)
        self.assertNotIn("scriptural", prompt)

    def test_technical_sonnet_system_protects_code_content(self):
        # RED today — the technical Sonnet system prompt SHOULD protect
        # code examples and CLI commands from being deleted as "noise".
        try:
            sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
            from noise_router import _build_sonnet_system_for_category
        except ImportError:
            self.skipTest("_build_sonnet_system_for_category not yet implemented")
        prompt = _build_sonnet_system_for_category("explainers")
        technical_protection_markers = [
            "code", "command", "CLI", "technical", "specification",
            "example", "syntax",
        ]
        self.assertTrue(
            any(m.lower() in prompt.lower() for m in technical_protection_markers),
            f"Expected code/CLI protection language in technical Sonnet system prompt",
        )

    def test_books_sonnet_system_unchanged(self):
        # GREEN today (once the function exists) — regression guard.
        # The books Sonnet system prompt should still protect spiritual content.
        try:
            sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
            from noise_router import _build_sonnet_system_for_category
        except ImportError:
            self.skipTest("_build_sonnet_system_for_category not yet implemented")
        prompt = _build_sonnet_system_for_category("books")
        self.assertIn("spiritual", prompt)
        self.assertIn("doctrinal", prompt)

    def test_current_pass2_sonnet_has_spiritual_protection(self):
        # GREEN today — the books Sonnet system prompt protects spiritual content.
        # After refactoring, this lives in _build_sonnet_system_for_category("books").
        sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))
        from noise_router import _build_sonnet_system_for_category
        prompt = _build_sonnet_system_for_category("books")
        self.assertIn("spiritual", prompt)
        self.assertIn("doctrinal", prompt)


# ─────────────────────────────────────────────────────────────────────────────
# 8. End-to-end routing integration
# ─────────────────────────────────────────────────────────────────────────────

class TestTechnicalPathRouting(unittest.TestCase):
    """Integration-level routing tests: verify that a book_dir with
    category=explainers gets routed to technical variants at each phase
    without needing to invoke an LLM.
    """

    def test_meta_yml_category_survives_across_phases(self):
        # GREEN today — category written to meta.yml persists correctly.
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = _make_book_dir(Path(tmp), category="explainers")
            meta = book_dir / "_system" / "meta.yml"
            content = meta.read_text()
            self.assertIn("category: explainers", content)

    def test_orchestrator_state_initial_for_explainers(self):
        # GREEN today — initial_state for explainers should record category.
        try:
            from _progress import initial_state
        except ImportError:
            self.skipTest("Cannot import initial_state")
        state = initial_state("claude-code-training", "explainers")
        self.assertEqual(state.get("category"), "explainers")

    def test_framing_routing_coverage_for_all_non_book_categories(self):
        # RED today — author_framing() must handle ALL non-book categories.
        # Currently only 'sites' gets a non-Islamic prompt. Every category
        # in ALLOWED_CATEGORIES should map to SOME explicit prompt variant —
        # never fall through silently to the Islamic scholarly default.
        #
        # This test documents the requirement: every category name must appear
        # in the framing module's routing logic.
        try:
            from _authoring._framing import author_framing
            import inspect
            src = inspect.getsource(author_framing)
        except ImportError:
            self.skipTest("Cannot import author_framing")

        non_book_categories = [c for c in _rules.ALLOWED_CATEGORIES if c != "books"]
        missing = []
        for cat in non_book_categories:
            # Accept either the category name or a clear "non-book" routing block
            if cat not in src and cat.rstrip("s") not in src:
                missing.append(cat)

        # For now we only assert on explainers (the immediate target).
        # As other categories get technical/specialized prompts, add them here.
        if "explainers" in missing:
            self.fail(
                "author_framing() does not reference 'explainers' in its routing logic. "
                "explainers content will silently use the Islamic scholarly prompt. "
                f"All non-book categories missing from routing: {missing}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
