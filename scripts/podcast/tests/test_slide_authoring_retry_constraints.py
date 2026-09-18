#!/usr/bin/env python3
"""_slide_authoring.py's retry constraint merging.

isaf-al-talib's per-chapter-slides phase stalled twice in a row on the same
content-quality findings (SL-P1 restatement, SL-P4 diagram-type discipline),
each time after genuinely using 2 of its 5 outer-loop iterations. Tracing it
down: `author_deck_pair` DOES seed `extra_constraints` from the outer Slide
Deck Challenger's `prior_findings` on the first inner attempt — but almost
every first attempt fails the deterministic build validator (a missing H2
section, an unattributed quote), and both retry sites replaced
`extra_constraints` wholesale with just that attempt's validator findings,
discarding the challenger's content-quality guidance. The deck that finally
passed the mechanical validator had never actually been asked to fix the
thing the outer loop was iterating to fix, so the same finding came back
unchanged next iteration and the loop's 2-consecutive-identical-verdicts
break fired. These tests pin `_merge_constraints` (the fix: union, not
replace) and that both retry call sites in `author_deck_pair` use it.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _slide_authoring as sa  # noqa: E402


def test_merge_keeps_both_when_both_present() -> None:
    merged = sa._merge_constraints("- [SL-P1] restatement (slides: M3, M4)", ["missing H2 section"])
    assert "SL-P1" in merged
    assert "missing H2 section" in merged


def test_merge_returns_prior_when_new_is_empty() -> None:
    assert sa._merge_constraints("- [SL-P1] restatement", []) == "- [SL-P1] restatement"


def test_merge_returns_new_when_prior_is_empty() -> None:
    merged = sa._merge_constraints("", ["missing H2 section"])
    assert merged == "- missing H2 section"


def test_merge_empty_when_both_empty() -> None:
    assert sa._merge_constraints("", []) == ""


def test_author_deck_pair_keeps_outer_findings_across_inner_retry(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: attempt 1 fails the mechanical validator, attempt 2 passes —
    the prompt for attempt 2 must still carry the outer challenger's finding,
    not just the mechanical one from attempt 1's failure."""
    book_dir = tmp_path
    (book_dir / "chapters").mkdir()
    chapter_file = book_dir / "chapters" / "ch01-test-topic.txt"
    chapter_file.write_text("word " * 3000, encoding="utf-8")

    deck_path = book_dir / "slide-decks" / "ch01-deck-test-topic.txt"
    framing_path = book_dir / "slide-decks" / "ch01-framing-test-topic.md"

    captured_prompts: list[str] = []
    call_count = {"n": 0}

    def fake_build_pair_prompt(*, extra_constraints: str = "", **_kwargs) -> str:
        captured_prompts.append(extra_constraints)
        return "PROMPT"

    def fake_run_claude_p(prompt, **_kwargs):
        call_count["n"] += 1
        book_dir.joinpath("slide-decks").mkdir(exist_ok=True)
        deck_path.write_text("deck content", encoding="utf-8")
        framing_path.write_text("framing content", encoding="utf-8")
        return 0, "", ""

    def fake_run_validator(_book_dir, _slug):
        if call_count["n"] == 1:
            return False, ["BUILD-SLIDE FAIL: has 5 H2 section(s); required minimum 6."]
        return True, []

    monkeypatch.setattr(sa, "_build_pair_prompt", fake_build_pair_prompt)
    monkeypatch.setattr(sa, "_run_claude_p", fake_run_claude_p)
    monkeypatch.setattr(sa, "_run_validator", fake_run_validator)
    import _authoring._core as _core

    monkeypatch.setattr(_core, "_read_category", lambda _bd: "islamic_scholarly")

    prior_findings = [{"id": "SL-P1", "notes": "restatement in 10 moments", "slides": "M3, M4, M5"}]

    result = sa.author_deck_pair(book_dir, "test-topic", prior_findings=prior_findings)

    assert result.success is True
    assert call_count["n"] == 2
    assert len(captured_prompts) == 2
    # Attempt 1 carries the outer finding.
    assert "SL-P1" in captured_prompts[0]
    # Attempt 2 (the retry after the mechanical validator failure) must STILL
    # carry it, merged with the mechanical finding — this is the fix.
    assert "SL-P1" in captured_prompts[1]
    assert "H2 section" in captured_prompts[1]
