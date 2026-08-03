"""Romanization out, Arabic script in — the third inline-Arabic operation.

Asif, 2026-08-02: "there should be zero English transliteration of Arabic terms
… in book.md." The overlay CONVERTED a bracket the author wrote and ANNOTATED a
term he did not; neither reached a term the prose simply uses (`the *mawaddah*`),
which is what he read on the page on 2026-08-03.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_substitution import (  # noqa: E402
    apply_arabic_substitution,
    load_record,
    substitute_body,
)

TERMS = [
    {"phonetic": "nafi al-jins", "script": "نَفْي الجِنْس", "style": "teach"},
    {"phonetic": "mawaddah", "script": "مَوَدَّة", "style": "teach"},
    {"phonetic": "amal", "script": "عَمَل", "style": "teach"},
    {"phonetic": "kun", "script": "كُنْ", "style": "teach"},
    {"phonetic": "Qutb", "script": "قُطْب", "style": "teach"},
]


def _book(tmp_path: Path, body: str, entries: list[dict]) -> Path:
    bd = tmp_path / "book_dir"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    import yaml

    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 2, "entries": entries}, allow_unicode=True), encoding="utf-8"
    )
    return bd


# ─── The substitution itself ────────────────────────────────────────────────
def test_a_bare_romanization_becomes_script() -> None:
    out, n = substitute_body("the noble affections — the *mawaddah* — carry the soul.", TERMS)
    assert "مَوَدَّة" in out and "mawaddah" not in out and n == 1


def test_a_multi_word_term_is_matched_whole() -> None:
    out, _ = substitute_body("what the grammarians call *nafi al-jins*, the negation.", TERMS)
    assert "نَفْي الجِنْس" in out and "nafi" not in out


def test_the_appended_shape_collapses_to_script_alone() -> None:
    """`amal (عَمَل)` -> `عَمَل`. Asif's example, verbatim."""
    out, n = substitute_body("The *amal* (عَمَل) is the deed.", TERMS)
    assert out == "The عَمَل is the deed."
    assert n == 1


def test_letters_as_letters_keeps_both_forms() -> None:
    """BK-N4 REQUIRES `كُنْ (kun)` where a passage discusses Arabic as letters."""
    line = "The words كُنْ (kun) are read as two letters."
    out, n = substitute_body(line, TERMS)
    assert out == line and n == 0


def test_a_reversed_gloss_keeps_its_english_translation() -> None:
    """`*Qutb* (pole)` -> `قُطْب (pole)`: the translation stays, the romanization goes."""
    out, _ = substitute_body("And *Qutb* (pole) opens the matter.", TERMS)
    assert out == "And قُطْب (pole) opens the matter."


def test_quotations_headings_and_fences_are_untouched() -> None:
    body = "> a quoted *amal* stays\n\n## A heading with amal\n\n| a table | *amal* |\n"
    out, n = substitute_body(body, TERMS)
    assert out == body and n == 0


def test_line_structure_is_never_disturbed() -> None:
    """`"\\n".join(splitlines())` ate nine blank lines out of a live book."""
    body = "First.\n\nThe *amal* here.\n\n\nLast.\n"
    out, _ = substitute_body(body, TERMS)
    assert out.splitlines() == ["First.", "", "The عَمَل here.", "", "", "Last."]
    assert out.endswith("\n")


def test_a_term_inside_a_longer_word_is_not_matched() -> None:
    out, n = substitute_body("The amalgam and the amals are not the term.", TERMS)
    assert n == 0 and out.count("عَمَل") == 0


# ─── Policy exclusions, inherited from the overlay ──────────────────────────
def test_familiar_silent_and_name_terms_are_never_substituted(tmp_path: Path) -> None:
    entries = [
        {"phonetic": "Quran", "arabic_script": "قُرْآن", "annotation_class": "familiar"},
        {"phonetic": "hawiya", "arabic_script": "هَاوِيَة", "annotation_class": "silent"},
        {"phonetic": "Ghazali", "arabic_script": "غَزَالِي", "annotation_class": "name"},
        {"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"},
    ]
    bd = _book(tmp_path, "## 1. A\n\nThe *Quran*, the *hawiya*, *Ghazali*, and the *mawaddah*.\n", entries)
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "Quran" in out and "hawiya" in out and "Ghazali" in out
    assert "مَوَدَّة" in out and "mawaddah" not in out


# ─── Reversibility — the property that makes it safe to run automatically ───
def test_running_twice_changes_nothing_the_second_time(tmp_path: Path) -> None:
    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    once = (bd / "book" / "book.md").read_text(encoding="utf-8")
    apply_arabic_substitution(bd)
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == once


def test_reclassifying_a_term_gives_its_english_back(tmp_path: Path) -> None:
    """The whole reason for the sidecar.

    `_normalize_annotations` inverts an annotation by reading the romanization
    still on the page. Substitution deletes that anchor, so without a record the
    pass could only ever ADD — and a term later classified `familiar` would stay
    fossilised in script forever.
    """
    import yaml

    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    assert "مَوَدَّة" in (bd / "book" / "book.md").read_text(encoding="utf-8")

    entries[0]["annotation_class"] = "familiar"
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 2, "entries": entries}, allow_unicode=True), encoding="utf-8"
    )
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "*mawaddah*" in out and "مَوَدَّة" not in out


def test_a_hand_edit_after_substitution_is_never_overwritten(tmp_path: Path) -> None:
    """The stored body is trusted only while the text is still this pass's output."""
    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    book_md = bd / "book" / "book.md"
    book_md.write_text("## 1. A\n\nThe مَوَدَّة here, and a sentence a human added.\n", encoding="utf-8")
    apply_arabic_substitution(bd)
    assert "a sentence a human added" in book_md.read_text(encoding="utf-8")


def test_the_record_is_written_and_readable(tmp_path: Path) -> None:
    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A Chapter\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    rec = load_record(bd)
    assert rec["schema"] == "book.substitutions/v1"
    assert len(rec["chapters"]) == 1
    row = rec["chapters"][0]
    assert row["chapter_key"] == "a chapter"
    assert "*mawaddah*" in row["before_md"] and row["replacements"] == 1
    assert json.loads((bd / "_system" / "book-substitutions.json").read_text(encoding="utf-8"))


def test_one_chapter_can_be_targeted(tmp_path: Path) -> None:
    """What the Composer button does — the rest of the book must not move."""
    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. First\n\nThe *mawaddah*.\n\n## 2. Second\n\nThe *mawaddah* too.\n", entries)
    apply_arabic_substitution(bd, chapter_key="second")
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "## 1. First\n\nThe *mawaddah*." in out
    assert "مَوَدَّة too" in out


def test_a_book_with_no_scripted_terms_is_a_no_op(tmp_path: Path) -> None:
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here.\n", [{"phonetic": "mawaddah", "arabic_script": ""}])
    body = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert apply_arabic_substitution(bd) == 0
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == body


# ─── The live corpus ────────────────────────────────────────────────────────
def test_the_compose_step_is_classified_as_page_altering() -> None:
    """An unclassified skip would let a book ship romanized and still pass B8."""
    from _compose_skips import PAGE_ALTERING_STEPS

    assert "arabic-substitution" in PAGE_ALTERING_STEPS


# ─── The shredding guard ────────────────────────────────────────────────────
SHAHADA_TERMS = [
    {"phonetic": "La ilaha", "script": "لَا إِلَهَ", "style": "teach"},
    {"phonetic": "illa", "script": "إِلَّا", "style": "teach"},
]


def test_a_term_inside_a_longer_emphasised_phrase_is_left_whole() -> None:
    """The live defect: `*La ilaha illa Allah*` -> `لَا إِلَهَ إِلَّا Allah*`.

    Two glossary terms matched inside one formula and produced half script, half
    romanization, with the closing emphasis marker orphaned. A partly-converted
    shahada is worse than an unconverted one.
    """
    for line in (
        "the formula *La ilaha illa Allah* contains seven strokes.",
        "twelve letters form *la ilaha illa Allah* — and those twelve",
    ):
        out, n = substitute_body(line, SHAHADA_TERMS)
        assert (out, n) == (line, 0), out


def test_a_term_that_is_the_whole_emphasis_run_still_converts() -> None:
    out, n = substitute_body('*La ilaha* — "there is no god" — is the negation.', SHAHADA_TERMS)
    assert out.startswith("لَا إِلَهَ —") and n == 1


def test_a_bare_term_outside_emphasis_still_converts() -> None:
    """Adjacency proves nothing outside a run — English surrounds every term."""
    out, n = substitute_body("the mawaddah carries the soul.", TERMS)
    assert "مَوَدَّة" in out and n == 1


def test_absorbed_english_is_never_substituted(tmp_path: Path) -> None:
    """REQ-BA-070 follows LAL 6.2.10 rule 15: use the Merriam-Webster English
    form where one exists. Without this, `*Shaykh*` became شَيْخ."""
    entries = [
        {"phonetic": "Shaykh", "arabic_script": "شَيْخ", "annotation_class": "teach"},
        {"phonetic": "Allah", "arabic_script": "اللَّه", "annotation_class": "teach"},
        {"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"},
    ]
    bd = _book(tmp_path, "## 1. A\n\nThe *Shaykh*, *Allah*, and the *mawaddah*.\n", entries)
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "Shaykh" in out and "Allah" in out and "مَوَدَّة" in out


def test_a_work_title_is_never_substituted(tmp_path: Path) -> None:
    """`*Kitab ithbat al-imama*` became unvowelled Arabic mid-sentence."""
    entries = [{"phonetic": "Kitab ithbat al-imama", "arabic_script": "كتاب إثبات الإمامة"}]
    bd = _book(tmp_path, "## 1. A\n\nIts title *Kitab ithbat al-imama* names the task.\n", entries)
    apply_arabic_substitution(bd)
    assert "*Kitab ithbat al-imama*" in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_english_in_the_glossary_is_never_substituted(tmp_path: Path) -> None:
    """21 English words reached three glossaries before the harvester guarded it;
    this pass turned `*blind*` and `*Path*` into Arabic on the page."""
    entries = [
        {"phonetic": "blind", "arabic_script": "أَعْمَى", "annotation_class": "teach"},
        {"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"},
    ]
    bd = _book(tmp_path, "## 1. A\n\nThe *blind* man and the *mawaddah*.\n", entries)
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "*blind*" in out and "مَوَدَّة" in out
