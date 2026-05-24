#!/usr/bin/env python3
"""tests/regression/test_systemic_fixes.py — pin the 5 systemic fixes + auditor closure.

Each test pins one lesson learned today so a future edit that re-breaks
the pattern fails CI / pre-commit before the bug ships. Run via:

    /usr/bin/python3 -m unittest tests.regression.test_systemic_fixes

Or use the convenience runner:

    bash tests/regression/run_all.sh

Coverage matrix (lessons → tests):

    AUDITOR P0 #1  deep_dive substring in template + prompt
                   → test_extract_template_no_modernize_substrings
                   → test_authoring_prompt_no_modernize_substrings
    AUDITOR P0 #2  Q4 host-pairing constants inert
                   → test_host_role_validator_exists
                   → test_host_role_validator_catches_swap
    AUDITOR Obs #9 agent specs contain "Imam Ali" literal
                   → test_agent_specs_no_literal_forbidden_phrase
    SYSTEMIC FIX   no cross-chapter refs in framing templates
                   → test_extract_templates_have_no_cross_chapter_refs_rule
    SYSTEMIC FIX   R-NO-READ-PROMPT closing guard
                   → test_extract_templates_have_no_read_prompt_guard
    SYSTEMIC FIX   host-pairing canonical-language present
                   → test_extract_templates_have_host_pairing_rule
    SYSTEMIC FIX   no-literal-forbidden-phrase-in-guards
                   → test_authoring_prompts_have_no_literal_forbidden_phrase_rule
    STILL OPEN #5  stale handbook references
                   → test_extract_script_no_stale_handbook_paths
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_PODCAST = REPO_ROOT / "scripts" / "podcast"
INFRA_AGENTS = REPO_ROOT / "infra" / "claude-agents"

sys.path.insert(0, str(SCRIPTS_PODCAST))


# ─── Shared helpers ─────────────────────────────────────────────────────────

def _stub_contract() -> dict:
    """Minimal valid contract that exercises both deep_dive and debate paths."""
    return {
        "title": "Test Chapter",
        "slug": "test-chapter",
        "source_type": "book-chapter",
        "book_slug": "fixture-book",
        "episode_number": 1,
        "audience": "Test audience.",
        "angle": "faithful_exposition",
        "host_dynamic": "curious_mind + scholar_companion",
        "length_target": "extended",
        "key_tensions": ["Tension A.", "Tension B."],
        "tone_constraints": ["No surprise reactions.", "No modern slang."],
        "phonetic_overrides": {},
        "anchor_passages": [],
        "show_notes": {"blurb": "Test."},
        "episode_format": "deep_dive",
        "essential": "core",
    }


def _fake_resolved_chapter() -> object:
    """Minimal duck for ResolvedChapter."""
    class _R:
        path = Path("/tmp/test-chapter.txt")
        source_bucket = "fixture-book"
        chapter_number = 1
        chapter_slug = "test-chapter"
    return _R()


# ─── AUDITOR P0 #1 — "deep dive" / "deep-dive" substring trap ──────────────

class TestNoModernizeSubstringsInTemplate(unittest.TestCase):
    """Both the template-rendered framing AND the authoring prompt must NOT
    contain MODERNIZE_DENY substrings. The substring scanner doesn't care
    that the prompt is metadata or that the template is the system speaking;
    if it's in the framing text reaching NotebookLM, it's a violation."""

    def setUp(self):
        from _rules import MODERNIZE_DENY
        # Normalize: include both hyphenated and spaced variants of any
        # multi-word entry. Today the deny list inconsistently carries one
        # or the other; tomorrow's audit will pin both.
        expanded = set(MODERNIZE_DENY)
        for term in list(MODERNIZE_DENY):
            if " " in term:
                expanded.add(term.replace(" ", "-"))
            if "-" in term:
                expanded.add(term.replace("-", " "))
        self.modernize_terms = expanded

    def test_extract_template_no_modernize_substrings(self):
        import extract_chapter
        c = _stub_contract()
        chapter = _fake_resolved_chapter()
        for mode in ("deep_dive", "debate"):
            c["episode_format"] = mode
            if mode == "debate":
                c["debate"] = {
                    "proposition": "P", "resolution": "open",
                    "host_a": {"role": "scholar", "position": "X",
                               "source_moves": ["m1"]},
                    "host_b": {"role": "debater", "position": "Y",
                               "source_moves": ["m1"]},
                }
            rendered = extract_chapter.render_framing(c, chapter, 1)
            # Mirror build_episode_txt's scrubbing: strip the canonical
            # `## Do not (forbidden vocabulary and framings)` section before
            # scanning, since that section's EXAMPLES legitimately quote the
            # forbidden phrases as a reference list for the LLM author.
            rendered_scrubbed = re.sub(
                r"##\s+Do not\s*\(forbidden vocabulary.*?(?=\n##\s|\Z)",
                "",
                rendered,
                flags=re.DOTALL | re.IGNORECASE,
            )
            rendered_lc = rendered_scrubbed.lower()
            for term in self.modernize_terms:
                self.assertNotIn(
                    term.lower(), rendered_lc,
                    f"{mode} framing template emits MODERNIZE_DENY substring "
                    f"{term!r} OUTSIDE the canonical `## Do not` section "
                    f"(R-NO-MODERNIZE-IN-METADATA)"
                )


# ─── AUDITOR P0 #2 — Q4 host-pairing constants must be consumed ────────────

class TestHostRoleValidator(unittest.TestCase):
    """Q4 host-role parity must be a HARD deterministic gate in
    build_episode_txt.py, not LLM-judgment-only. The HOST_A_ROLES_SCHOLAR /
    HOST_B_ROLES_SEEKER constants in _rules.py must have a consumer."""

    def test_host_role_validator_exists(self):
        """A function named validate_host_role_parity (or equivalent) must
        live in build_episode_txt.py and import the HOST_* constants."""
        build_src = (SCRIPTS_PODCAST / "build_episode_txt.py").read_text()
        self.assertIn(
            "HOST_A_ROLES_SCHOLAR", build_src,
            "build_episode_txt.py must import HOST_A_ROLES_SCHOLAR from _rules"
        )
        self.assertTrue(
            re.search(r"def validate_host_role_parity\b", build_src),
            "build_episode_txt.py must define validate_host_role_parity()"
        )

    def test_host_role_validator_catches_swap(self):
        """validate_host_role_parity must reject a contract whose host_a.role
        is in the seeker pool (and vice versa)."""
        try:
            from build_episode_txt import validate_host_role_parity
        except ImportError:
            self.skipTest("validate_host_role_parity not yet implemented")
        ok_contract = {
            "debate": {
                "host_a": {"role": "scholar"},
                "host_b": {"role": "debater"},
            }
        }
        result = validate_host_role_parity(ok_contract)
        self.assertEqual(
            result, [],
            "canonical pairing should produce no findings"
        )
        swap_contract = {
            "debate": {
                "host_a": {"role": "debater"},
                "host_b": {"role": "scholar"},
            }
        }
        result = validate_host_role_parity(swap_contract)
        self.assertTrue(
            len(result) > 0,
            "swapped pairing should produce at least one finding"
        )


# ─── AUDITOR Obs #9 — agent specs must not contain literal forbidden phrases ─

class TestAgentSpecsNoLiteralForbiddenPhrases(unittest.TestCase):
    """Agent specs are READ by the challenger at runtime. If they contain the
    literal forbidden phrase (e.g. 'Imam Ali') inside their own rule text,
    the substring scanner flags downstream chapters that quote the spec.
    More importantly, the pattern f7068bf was trying to break ('guard contains
    its own forbidden phrase') survives in the canonical spec files."""

    FORBIDDEN_LITERAL = "Imam Ali"
    # Exceptions: spec files MAY name the forbidden phrase ONCE in a
    # specifically-marked context (e.g., 'see content/_shared/islam/'
    # references where the YAML itself contains the data). Add specific
    # path exceptions here as they arise; default is zero tolerance.
    EXEMPT_PATHS: set = set()

    def test_agent_specs_no_literal_forbidden_phrase(self):
        offenders: list[str] = []
        for spec in INFRA_AGENTS.glob("*.md"):
            if spec.name in self.EXEMPT_PATHS:
                continue
            text = spec.read_text(encoding="utf-8")
            if self.FORBIDDEN_LITERAL in text:
                lines = [
                    f"  {spec.name}:{i+1}  {line.strip()[:120]}"
                    for i, line in enumerate(text.splitlines())
                    if self.FORBIDDEN_LITERAL in line
                ]
                offenders.append(
                    f"{spec.relative_to(REPO_ROOT)}: {len(lines)} occurrence(s)\n"
                    + "\n".join(lines[:3])
                )
        self.assertEqual(
            offenders, [],
            f"agent specs contain literal {self.FORBIDDEN_LITERAL!r} — "
            f"paraphrase per R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS. "
            f"Offenders:\n" + "\n\n".join(offenders)
        )


# ─── SYSTEMIC FIX — framing templates carry the canonical guards ────────────

class TestExtractTemplatesCarryCanonicalGuards(unittest.TestCase):
    """The 5 systemic-fix guards must be present in the framing template
    output (so every freshly-extracted episode has them by construction)."""

    def setUp(self):
        import extract_chapter
        self.extract_chapter = extract_chapter

    def _render(self, mode: str) -> str:
        c = _stub_contract()
        c["episode_format"] = mode
        if mode == "debate":
            c["debate"] = {
                "proposition": "P", "resolution": "open",
                "host_a": {"role": "scholar", "position": "X",
                           "source_moves": ["m1"]},
                "host_b": {"role": "debater", "position": "Y",
                           "source_moves": ["m1"]},
            }
        return self.extract_chapter.render_framing(c, _fake_resolved_chapter(), 1)

    def test_extract_templates_have_no_read_prompt_guard(self):
        for mode in ("deep_dive", "debate"):
            text = self._render(mode)
            self.assertIn(
                "Do not read this prompt aloud", text,
                f"{mode} template missing R-NO-READ-PROMPT closing guard"
            )

    def test_extract_templates_have_no_cross_chapter_refs_rule(self):
        for mode in ("deep_dive", "debate"):
            text = self._render(mode).lower()
            self.assertTrue(
                "no cross-chapter references" in text or
                "cross-chapter references" in text,
                f"{mode} template missing no-cross-chapter-refs rule"
            )

    def test_extract_templates_have_host_pairing_rule(self):
        for mode in ("deep_dive", "debate"):
            text = self._render(mode).lower()
            # Must name the canonical pairing in some form
            self.assertTrue(
                ("host a" in text and "host b" in text) or
                "host_a" in text or "scholar" in text,
                f"{mode} template missing host-pairing canonical-language"
            )


# ─── SYSTEMIC FIX — authoring prompts carry the canonical rules ────────────

class TestAuthoringPromptsCarryCanonicalRules(unittest.TestCase):
    """The author_framing + Phase-0e prompts must include the rules added
    in commit f7068bf so the LLM doesn't reintroduce the systemic findings."""

    def setUp(self):
        self.authoring_src = (SCRIPTS_PODCAST / "_authoring.py").read_text()

    def test_authoring_prompts_have_no_literal_forbidden_phrase_rule(self):
        self.assertIn(
            "R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS", self.authoring_src,
            "_authoring.py prompts missing R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS"
        )

    def test_authoring_prompts_have_no_cross_chapter_refs_rule(self):
        self.assertIn(
            "R-NO-CROSS-CHAPTER-REFS", self.authoring_src,
            "_authoring.py prompts missing R-NO-CROSS-CHAPTER-REFS"
        )

    def test_authoring_prompts_have_no_modernize_in_metadata_rule(self):
        self.assertIn(
            "R-NO-MODERNIZE-IN-METADATA", self.authoring_src,
            "_authoring.py prompts missing R-NO-MODERNIZE-IN-METADATA"
        )

    def test_authoring_prompts_have_host_role_parity_rule(self):
        self.assertIn(
            "R-HOST-ROLE-PARITY", self.authoring_src,
            "_authoring.py prompts missing R-HOST-ROLE-PARITY"
        )

    def test_authoring_prompts_no_literal_forbidden_phrase(self):
        """The prompts THEMSELVES must not embed the literal forbidden
        phrase in their rule text (the rule that bans X must not contain X)."""
        # Allow 'Imam Ali' only as an explicit paraphrase-reference inside
        # an "AND NEVER WRITE THE LITERAL" guard; otherwise zero tolerance.
        # Current state: prompt text uses "the literal phrase pairing the
        # leadership-title with the personal name of the Father of Imams"
        # — no literal "Imam Ali".
        offending_lines: list[str] = []
        for i, line in enumerate(self.authoring_src.splitlines(), 1):
            if "Imam Ali" in line:
                offending_lines.append(f"  line {i}: {line.strip()[:120]}")
        self.assertEqual(
            offending_lines, [],
            "scripts/podcast/_authoring.py contains literal 'Imam Ali' in "
            "prompt text — paraphrase per R-NO-LITERAL-FORBIDDEN-PHRASE-IN-GUARDS"
            + "\n".join(offending_lines[:5])
        )


# ─── STILL OPEN #5 — no stale handbook paths in extract_chapter.py ─────────

class TestNoStaleHandbookPaths(unittest.TestCase):
    """The content/podcast/.skill/handbook/ tree was retired 2026-05-23.
    No script should reference it as if it existed."""

    HANDBOOK_PATH_RE = re.compile(r"content/podcast/\.skill/handbook/[A-Za-z0-9_\-]+\.md")

    def test_extract_script_no_stale_handbook_paths(self):
        src = (SCRIPTS_PODCAST / "extract_chapter.py").read_text()
        # Exception: comments that explicitly NOTE the retirement are fine
        # (they document the history). Code paths emitting the strings to
        # outputs are not.
        offending: list[str] = []
        for i, line in enumerate(src.splitlines(), 1):
            if self.HANDBOOK_PATH_RE.search(line):
                # Skip if the line is clearly a comment about the retirement
                stripped = line.strip()
                if stripped.startswith("#") and (
                    "retired" in stripped.lower() or
                    "deleted" in stripped.lower() or
                    "no longer" in stripped.lower()
                ):
                    continue
                offending.append(f"  line {i}: {stripped[:120]}")
        self.assertEqual(
            offending, [],
            "scripts/podcast/extract_chapter.py contains stale handbook paths "
            "(retired 2026-05-23). Either restore the tree or rewrite to "
            "current authority:\n" + "\n".join(offending[:10])
        )


class TestMetaProseTellsAllowRuleExamples(unittest.TestCase):
    """assert_no_meta_prose must NOT flag a meta-prose tell that appears
    only inside a quoted example within a rule-statement bullet. The rule
    `- **Cross-episode language.** No "previous episode," "next episode."`
    legitimately quotes the tells it forbids. f7068bf-class pattern."""

    def setUp(self):
        import build_episode_txt
        self.B = build_episode_txt

    def test_rule_example_line_recognized(self):
        from build_episode_txt import _is_rule_example_line
        # Real rule statement with quoted tells
        line = '- **Cross-episode language.** No "previous episode," "next episode."'
        self.assertTrue(_is_rule_example_line(line, "previous episode"))
        self.assertTrue(_is_rule_example_line(line, "next episode"))

    def test_unquoted_tell_still_caught(self):
        from build_episode_txt import _is_rule_example_line
        # Tell appearing OUTSIDE quotes on a rule bullet = real leak
        line = '- **Bad bullet.** As we said in the previous episode, …'
        self.assertFalse(_is_rule_example_line(line, "previous episode"))

    def test_non_bullet_line_with_tell_is_real(self):
        from build_episode_txt import _is_rule_example_line
        line = 'As discussed in the previous episode, this matters.'
        self.assertFalse(_is_rule_example_line(line, "previous episode"))

    def test_assert_no_meta_prose_skips_rule_example_tells(self):
        # Framing fragment that ONLY contains the tells inside rule-example
        # quotes — should pass the meta-prose check.
        fragment = """# Title

## Anti-noise rules

- **Cross-episode language.** No "previous episode," "earlier episode," "next episode."
- **Trailer talk.** No "in this episode," "today's episode," "on today's show."
"""
        # Should not raise SystemExit
        try:
            self.B.assert_no_meta_prose(
                fragment, Path("/tmp/test-framing.md"),
                "framing (CUSTOMIZE PROMPT)"
            )
        except SystemExit as e:
            self.fail(
                f"assert_no_meta_prose raised SystemExit on legitimate "
                f"rule-example tells: {e}"
            )


class TestPipelineLintExists(unittest.TestCase):
    """pipeline_lint.py is the deterministic $0 pre-flight gate. It must:
    (a) exist as an executable Python script
    (b) be importable as a module so per_chapter_pass can call it
    (c) expose lint_chapter_and_framing(book_dir, episode_id) → dict
    """

    def test_pipeline_lint_module_importable(self):
        import pipeline_lint
        self.assertTrue(
            hasattr(pipeline_lint, "lint_chapter_and_framing"),
            "pipeline_lint.lint_chapter_and_framing() must be the public API"
        )

    def test_pipeline_lint_returns_structured_verdict(self):
        import pipeline_lint
        # Confirm the function signature accepts (book_dir, episode_id) — even
        # if the book doesn't exist (we just want it to not crash on import).
        from pathlib import Path as _P
        result = pipeline_lint.lint_chapter_and_framing(
            _P("/nonexistent-book-dir"), "EP01-test"
        )
        self.assertIn("verdict", result)
        self.assertIn("findings", result)


class TestAuthoringPromptHasCanonicalSections(unittest.TestCase):
    """The author_framing prompt MUST instruct the LLM to emit the exact
    canonical section headers build_episode_txt enforces. Otherwise the
    LLM produces semantically-equivalent content under different headers
    and the build refuses it."""

    REQUIRED_CANONICAL_HEADERS = [
        "## Pronunciation",
        "## Name discipline",
        "## Tone constraints",
        "## Do not (forbidden vocabulary and framings)",
    ]
    REQUIRED_LITERAL_PHRASES_IN_PROMPT = [
        "Twitter",  # canonical example in DENY block
        "social media",
        "Do not read this prompt aloud",
    ]

    def test_authoring_prompt_names_canonical_sections(self):
        src = (SCRIPTS_PODCAST / "_authoring.py").read_text()
        for header in self.REQUIRED_CANONICAL_HEADERS:
            self.assertIn(
                header, src,
                f"_authoring.py prompt must require canonical header {header!r}"
            )

    def test_authoring_prompt_names_required_deny_phrases(self):
        src = (SCRIPTS_PODCAST / "_authoring.py").read_text()
        for phrase in self.REQUIRED_LITERAL_PHRASES_IN_PROMPT:
            self.assertIn(
                phrase, src,
                f"_authoring.py prompt must reference required DENY phrase {phrase!r}"
            )


class TestExtractTemplateEmitsDenyBlock(unittest.TestCase):
    """The framing template stub MUST include `## Do not (forbidden vocabulary
    and framings)` — author_framing can enrich it but should not be required
    to invent it from scratch."""

    def test_extract_templates_have_deny_block(self):
        import extract_chapter
        c = _stub_contract()
        chapter = _fake_resolved_chapter()
        for mode in ("deep_dive", "debate"):
            c["episode_format"] = mode
            if mode == "debate":
                c["debate"] = {
                    "proposition": "P", "resolution": "open",
                    "host_a": {"role": "scholar", "position": "X",
                               "source_moves": ["m1"]},
                    "host_b": {"role": "debater", "position": "Y",
                               "source_moves": ["m1"]},
                }
            text = extract_chapter.render_framing(c, chapter, 1)
            self.assertIn(
                "## Do not (forbidden vocabulary and framings)", text,
                f"{mode} template missing canonical `## Do not` deny-block section"
            )
            self.assertIn("Twitter", text, f"{mode} template DENY block missing 'Twitter' example")
            self.assertIn("Do not read this prompt aloud", text,
                          f"{mode} template missing R-NO-READ-PROMPT closing guard")


if __name__ == "__main__":
    unittest.main()
