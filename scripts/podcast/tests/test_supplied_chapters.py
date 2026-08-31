"""Phase 0d honours a supplied chapter list, and is held to it.

The failure this pins: `purification-of-the-heart` is a series teaching through
Hamza Yusuf's *Purification of the Heart* chapter by chapter, and phase 0d cut
its two recordings into seventeen chapters of its own naming — "The World and
the Envious Heart" being two of the book's chapters merged into one. Step 1's
prompt says so in as many words ("the source's own chapter breaks are ADVISORY,
not authoritative"), which is right for a book being reconfigured into a podcast
and exactly wrong here.

Two halves, and both are needed: the prompt must ASK for the supplied set, and
the plan must be CHECKED against it. A prompt alone is a request.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _pipeline_flags as flags  # noqa: E402
from _authoring._supplied_chapters import (  # noqa: E402
    _supplied_chapter_violations,
    _supplied_chapters_block,
)
from _authoring._toc_prompt import _build_phase_0d_toc_prompt  # noqa: E402

TITLES = ["Love of the World", "Envy", "Boasting & Arrogance"]


def _book(tmp_path: Path, **cfg) -> Path:
    d = tmp_path / "a-book"
    (d / "_system").mkdir(parents=True)
    (d / "_system" / "series-config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return d


# ── the flags ────────────────────────────────────────────────────────────────
def test_segmentation_defaults_to_what_0d_has_always_done(tmp_path):
    """A book that never answered the question must be unaffected."""
    assert flags.chapter_segmentation(_book(tmp_path)) == flags.SEGMENTATION_FROM_TRANSCRIPT


def test_a_list_is_authoritative_only_under_from_source_toc(tmp_path):
    """A leftover list under a different answer must not take over the plan."""
    d = _book(tmp_path, chapter_segmentation="one_per_recording", chapter_list=TITLES)
    assert flags.chapter_list(d) == TITLES  # still readable
    assert flags.supplied_chapter_titles(d) == []  # but not authoritative


def test_the_list_is_used_when_the_answer_says_to_follow_it(tmp_path):
    d = _book(tmp_path, chapter_segmentation="from_source_toc", chapter_list=TITLES)
    assert flags.supplied_chapter_titles(d) == TITLES


def test_a_typoed_list_reads_as_absent_rather_than_one_chapter(tmp_path):
    """series-config.yaml is hand-edited; a string where a list belongs must not
    become a one-chapter book."""
    d = _book(tmp_path, chapter_segmentation="from_source_toc", chapter_list="Envy")
    assert flags.supplied_chapter_titles(d) == []


def test_an_unknown_segmentation_answer_is_refused(tmp_path):
    d = _book(tmp_path, chapter_segmentation="whatever-i-typed")
    with pytest.raises(Exception):
        flags.chapter_segmentation(d)


# ── the prompt ───────────────────────────────────────────────────────────────
def test_no_supplied_list_leaves_the_prompt_exactly_as_it_was(tmp_path):
    assert _supplied_chapters_block([]) == ""
    assert _supplied_chapters_block(None) == ""


def test_the_block_names_every_chapter_in_order():
    block = _supplied_chapters_block(TITLES)
    assert "all 3 of them" in block
    for i, t in enumerate(TITLES, start=1):
        assert f"{i}. {t}" in block
    # Order, not merely presence.
    assert block.index("Love of the World") < block.index("Envy") < block.index("Boasting")


def test_the_block_forbids_the_four_verbs_that_caused_the_failure():
    block = _supplied_chapters_block(TITLES)
    for phrase in ("Do NOT merge", "do NOT split", "do NOT add", "character for character"):
        assert phrase in block, phrase
    assert "A recording is NOT one chapter" in block


def test_a_chapter_the_source_never_reaches_is_reported_not_dropped():
    """Silence would look like the chapter having been covered."""
    block = _supplied_chapters_block(TITLES)
    assert "Never silently drop it" in block
    assert "null" in block


def _prompt(supplied):
    return _build_phase_0d_toc_prompt(
        book_slug="a-book",
        in_content=Path("/tmp/in.md"),
        toc_path=Path("/tmp/toc.json"),
        _gap_context_block="",
        consolidation_directive="",
        tier_band="x",
        unit_directive="y",
        inventory_block="",
        density_advisory_block="",
        density_ceiling_hint=2500,
        length_tier="extended",
        unit_mode="auto",
        supplied_chapters=supplied,
        episode_max_concepts=3,
    )


def test_the_supplied_set_is_stated_before_the_advisory_instruction():
    """The prompt still carries "the source's own chapter breaks are ADVISORY" —
    it is the right instruction for every other book. What matters is that the
    suspension is read FIRST, so the model meets the override before the rule."""
    p = _prompt(TITLES)
    assert "THE CHAPTER SET IS GIVEN" in p
    assert p.index("THE CHAPTER SET IS GIVEN") < p.index("ADVISORY, not authoritative")
    assert "is SUSPENDED" in p


def test_the_prompt_is_byte_identical_without_a_supplied_list():
    assert _prompt(None) == _prompt([])
    assert "THE CHAPTER SET IS GIVEN" not in _prompt(None)


# ── the gate ─────────────────────────────────────────────────────────────────
def _plan(*titles):
    return [{"source_title": t} for t in titles]


def test_a_matching_plan_passes():
    assert _supplied_chapter_violations(_plan(*TITLES), TITLES) == []


def test_no_supplied_list_means_nothing_to_check():
    assert _supplied_chapter_violations(_plan("Anything At All"), []) == []


def test_a_merged_chapter_is_caught():
    out = _supplied_chapter_violations(_plan("Love of the World and Envy", "Boasting & Arrogance"), TITLES)
    assert any("2 chapters" in m and "3" in m for m in out)
    assert any("missing" in m for m in out)


def test_a_renamed_chapter_is_caught_even_when_the_count_is_right():
    """ "Boasting and Arrogance" is a different name from "Boasting & Arrogance",
    and renaming a chapter of somebody's book is not the pipeline's to do."""
    out = _supplied_chapter_violations(_plan("Love of the World", "Envy", "Boasting and Arrogance"), TITLES)
    assert len(out) == 1
    assert "chapter 3" in out[0]


def test_a_reordered_plan_is_caught():
    out = _supplied_chapter_violations(_plan("Envy", "Love of the World", "Boasting & Arrogance"), TITLES)
    assert len(out) == 2


def test_an_extra_chapter_is_named():
    out = _supplied_chapter_violations(_plan(*TITLES, "One I Invented"), TITLES)
    assert any("One I Invented" in m for m in out)


def test_whitespace_around_a_title_is_not_a_violation():
    """The plan is JSON a model wrote; a stray space is not a renamed chapter."""
    assert _supplied_chapter_violations(_plan(*[f"  {t} " for t in TITLES]), TITLES) == []
