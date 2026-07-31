"""The reading edition is a text deliverable; figures come from a human.

Two things are tested: the knob that stops the pipeline generating visuals, and
the scan that proves the composed edition really carries none.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_visual_policy import (  # noqa: E402
    check_text_only,
    layout_placements,
    scan_markdown,
)
from _pipeline_flags import (  # noqa: E402
    BOOK_VISUALS_MANUAL_ONLY,
    BOOK_VISUALS_PIPELINE,
    book_visuals,
)


def book(tmp_path: Path, md: str, config: str = "") -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(md, encoding="utf-8")
    (bd / "_system" / "series-config.yaml").write_text(config or "slug: slug\n", encoding="utf-8")
    return bd


# ─── the knob ────────────────────────────────────────────────────────────────
def test_companion_edition_defaults_to_human_curated_visuals(tmp_path: Path) -> None:
    bd = book(tmp_path, "# B\n", "book_augmentation: source_only\n")
    assert book_visuals(bd) == BOOK_VISUALS_MANUAL_ONLY


def test_a_translation_edition_is_ALSO_human_curated_now(tmp_path: Path) -> None:
    """The default is manual_only for EVERY book (2026-07-31, Asif).

    A translation edition used to fall through to `pipeline`, which auto-injected
    generated diagrams and imported NotebookLM decks into the reading edition and
    halted the book lane until those decks were dropped. The rule is that no image
    reaches the PDF except by hand in the Book Composer, and that rule does not
    have an exception for translation editions.
    """
    bd = book(tmp_path, "# B\n", "deliverable_mode: translation_edition\n")
    assert book_visuals(bd) == BOOK_VISUALS_MANUAL_ONLY


def test_a_book_with_no_config_at_all_is_human_curated(tmp_path: Path) -> None:
    # The state every book is in before 0f writes series-config.yaml.
    bd = book(tmp_path, "# B\n", "")
    assert book_visuals(bd) == BOOK_VISUALS_MANUAL_ONLY


def test_an_explicit_key_wins_over_the_default(tmp_path: Path) -> None:
    bd = book(tmp_path, "# B\n", "book_augmentation: source_only\nbook_visuals: pipeline\n")
    assert book_visuals(bd) == BOOK_VISUALS_PIPELINE


def test_an_unrecognised_value_is_refused_not_defaulted(tmp_path: Path) -> None:
    """Strict, like its two sibling knobs (2026-07-21).

    This value decides whether the illustrate and slide-import phases run at all,
    so a typo silently produces candidate assets behind the curator's back — or
    silently stops producing them. `book_driver` catches the error and fails the
    book lane visibly; the podcast is unaffected.
    """
    bd = book(tmp_path, "# B\n", "book_augmentation: source_only\nbook_visuals: whatever\n")
    with pytest.raises(ValueError, match="book_visuals"):
        book_visuals(bd)


def test_an_absent_value_still_follows_the_augmentation_knob(tmp_path: Path) -> None:
    bd = book(tmp_path, "# B\n", "book_augmentation: source_only\n")
    assert book_visuals(bd) == BOOK_VISUALS_MANUAL_ONLY


# ─── the scan ────────────────────────────────────────────────────────────────
def test_plain_prose_and_quotations_are_not_visuals() -> None:
    md = '## One\n\nProse here.\n\n> شُكْرُ الْعَالِمِ طَاعَتُهُ\n>\n> "The translation."\n\nMore prose.\n'
    assert scan_markdown(md) == []


def test_every_route_to_a_picture_is_caught() -> None:
    md = (
        "## One\n\n"
        "![a diagram](visuals/one.svg)\n"
        '<img src="visuals/two.png">\n'
        '<svg viewBox="0 0 10 10"></svg>\n'
        '<figure class="book-diagram">x</figure>\n'
        "```mermaid\ngraph TD;\n```\n"
    )
    kinds = {f["kind"] for f in scan_markdown(md)}
    assert kinds == {"markdown-image", "html-img", "inline-svg", "figure-block", "mermaid-fence"}


def test_a_finding_names_the_chapter_it_landed_in() -> None:
    md = "## One\n\nprose\n\n## Two\n\n![x](y.svg)\n"
    findings = scan_markdown(md)
    assert len(findings) == 1
    assert findings[0]["chapter"] == "Two"


def test_curated_placements_are_counted_not_flagged(tmp_path: Path) -> None:
    bd = book(tmp_path, "## One\n\nprose only\n", "book_augmentation: source_only\n")
    (bd / "book" / "visual-layout.json").write_text(
        json.dumps({"placements": [{"asset": "a.svg"}, {"asset": "b.svg"}]}), encoding="utf-8"
    )

    report = check_text_only(bd, log=lambda *a: None)

    assert report["curated_placements"] == 2
    assert report["text_only"], "a figure the human placed is the point of the policy"


def test_missing_or_unreadable_layout_counts_as_no_figures(tmp_path: Path) -> None:
    bd = book(tmp_path, "## One\n\nprose\n")
    assert layout_placements(bd) == 0
    (bd / "book" / "visual-layout.json").write_text("{not json", encoding="utf-8")
    assert layout_placements(bd) == 0


# ─── the report ──────────────────────────────────────────────────────────────
def test_text_only_edition_is_confirmed_and_recorded(tmp_path: Path) -> None:
    bd = book(tmp_path, "## One\n\njust prose\n", "book_augmentation: source_only\n")

    report = check_text_only(bd, log=lambda *a: None)

    assert report["text_only"]
    assert report["policy"] == BOOK_VISUALS_MANUAL_ONLY
    written = json.loads((bd / "_system" / "book-visual-policy.json").read_text(encoding="utf-8"))
    assert written == report


def test_an_image_that_slipped_into_the_prose_is_a_violation(tmp_path: Path) -> None:
    bd = book(tmp_path, "## One\n\n![snuck in](x.svg)\n", "book_augmentation: source_only\n")

    report = check_text_only(bd, log=lambda *a: None)

    assert not report["text_only"]
    assert report["pipeline_inserted"][0]["kind"] == "markdown-image"


def test_a_book_that_allows_pipeline_visuals_is_reported_not_failed(tmp_path: Path) -> None:
    bd = book(tmp_path, "## One\n\n![fine here](x.svg)\n", "book_visuals: pipeline\n")

    report = check_text_only(bd, log=lambda *a: None)

    assert report["text_only"], "the scan only judges books that promised to be text-only"
    assert report["pipeline_inserted"], "but what it found is still recorded"
