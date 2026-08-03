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
    substitutable_terms,
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
    # Classified `teach` deliberately: without it the entry is `legacy` and the
    # annotation-policy gate would reject it first, leaving the title guard
    # itself unexercised.
    entries = [
        {
            "phonetic": "Kitab ithbat al-imama",
            "arabic_script": "كتاب إثبات الإمامة",
            "annotation_class": "teach",
        }
    ]
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


# ─── The record must survive the four steps that run after this pass ────────
def test_a_later_apparatus_edit_does_not_destroy_the_english(tmp_path: Path) -> None:
    """THE IRREVERSIBLE CASE, and it was the normal path.

    `after_fingerprint` was stamped at 5a-substitute with four page-altering
    steps still to come — American spelling, the comprehension bridges, the
    honorific convention, the paragraph mirror. So the stored number described a
    chapter that never reached disk; the next compose read a mismatch, refused to
    restore, replaced nothing (the script was already there), and wrote the
    sidecar back without the key. `before_md` is the only copy of the English
    anywhere — substitution deletes the romanization `_normalize_annotations`
    would otherwise use to invert itself.
    """
    import yaml

    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here, with honour.\n", entries)
    apply_arabic_substitution(bd)
    book_md = bd / "book" / "book.md"

    # Stand in for 5a-spelling / bridges / honorifics / paragraph-mirror.
    book_md.write_text(book_md.read_text(encoding="utf-8").replace("honour", "honor"), encoding="utf-8")
    apply_arabic_substitution(bd)
    assert load_record(bd)["chapters"], "the pre-substitution English was discarded"

    # And a reclassification can still get the English back once the stamp is
    # brought up to date, which is what step 12 does at the end of the apparatus.
    from _book_substitution import restamp_from_final_book

    restamp_from_final_book(bd)
    entries[0]["annotation_class"] = "familiar"
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 2, "entries": entries}, allow_unicode=True), encoding="utf-8"
    )
    apply_arabic_substitution(bd)
    assert "*mawaddah*" in book_md.read_text(encoding="utf-8")


def test_the_restamp_matches_what_the_next_run_will_read(tmp_path: Path) -> None:
    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here, with honour.\n", entries)
    apply_arabic_substitution(bd)
    book_md = bd / "book" / "book.md"
    book_md.write_text(book_md.read_text(encoding="utf-8").replace("honour", "honor"), encoding="utf-8")

    from _book_edits import anchor_key, fingerprint
    from _book_substitution import _chapters, restamp_from_final_book

    assert restamp_from_final_book(bd) == 1
    bodies = {anchor_key(h): b for h, b in _chapters(book_md.read_text(encoding="utf-8"))}
    row = load_record(bd)["chapters"][0]
    assert row["after_fingerprint"] == fingerprint(bodies[row["chapter_key"]].strip())
    assert "*mawaddah*" in row["before_md"]


def test_the_restamp_is_idempotent_and_silent_on_an_unchanged_book(tmp_path: Path) -> None:
    from _book_substitution import record_path, restamp_from_final_book

    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    restamp_from_final_book(bd)
    before = record_path(bd).read_bytes()
    assert restamp_from_final_book(bd) == 0
    assert record_path(bd).read_bytes() == before


def test_the_restamp_leaves_an_orphaned_record_alone(tmp_path: Path) -> None:
    """A renamed chapter orphans its record. That is a fact to preserve, not a
    reason to guess — and never a reason to delete the English."""
    from _book_substitution import restamp_from_final_book

    entries = [{"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A Chapter\n\nThe *mawaddah* here.\n", entries)
    apply_arabic_substitution(bd)
    book_md = bd / "book" / "book.md"
    book_md.write_text(
        book_md.read_text(encoding="utf-8").replace("## 1. A Chapter", "## 1. Renamed"), encoding="utf-8"
    )
    assert restamp_from_final_book(bd) == 0
    assert load_record(bd)["chapters"][0]["chapter_key"] == "a chapter"


def test_the_apparatus_restamps_last(tmp_path: Path) -> None:
    """Step 12 must be the final thing that touches the sidecar, and no step may
    be added after it — anything that rewrites book.md stales the stamp again."""
    source = (Path(__file__).resolve().parents[1] / "_book_apparatus.py").read_text(encoding="utf-8")
    assert "restamp_from_final_book" in source
    assert source.index("restamp_from_final_book") > source.index("mirror_paragraphs")
    assert source.rstrip().endswith("return book_md")


# ─── A gate that gets stricter must take back what it already wrote ─────────
def test_a_reclassified_term_is_taken_back_even_without_a_wholesale_restore(tmp_path: Path) -> None:
    """The live case, on four editions at once.

    The wholesale restore needs the fingerprint to match, and it cannot once a
    later apparatus step has been through the page. So 74 substitutions written
    under the old gate were stranded in script — among them `adam` set as `آدَم`,
    *Adam the prophet*, in a passage that means `عَدَم`, non-existence.
    """
    import yaml

    entries = [
        {"phonetic": "adam", "arabic_script": "آدَم", "annotation_class": "teach"},
        {"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"},
    ]
    body = "## 1. A\n\nOut of an *adam*, a nothingness, and by the *mawaddah*, with honour.\n"
    bd = _book(tmp_path, body, entries)
    apply_arabic_substitution(bd)
    book_md = bd / "book" / "book.md"
    assert "آدَم" in book_md.read_text(encoding="utf-8")

    # A later apparatus step edits the page, so the fingerprint can no longer match.
    book_md.write_text(book_md.read_text(encoding="utf-8").replace("honour", "honor"), encoding="utf-8")
    # And a reviewer classifies `adam` out of scope.
    entries[0]["annotation_class"] = "familiar"
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 2, "entries": entries}, allow_unicode=True), encoding="utf-8"
    )

    apply_arabic_substitution(bd)
    out = book_md.read_text(encoding="utf-8")
    assert "*adam*" in out and "آدَم" not in out  # the English is back, italics intact
    assert "مَوَدَّة" in out  # the eligible term is untouched
    assert "honor" in out  # and so is the later step's own edit


def test_the_take_back_leaves_an_annotation_bracket_alone(tmp_path: Path) -> None:
    """`*marifah* (مَعْرِفَة)` is the ANNOTATION overlay's apparatus, not this
    pass's output, and undoing it here would delete another step's work."""
    from _book_substitution import revert_ineligible

    body = "The *marifah* (مَعْرِفَة) is one thing, and the مَعْرِفَة alone is another.\n"
    out, n = revert_ineligible(
        body, "The *marifah* here and *marifah* there.", [], [{"phonetic": "marifah", "script": "مَعْرِفَة"}]
    )
    assert n == 1
    assert "(مَعْرِفَة)" in out and "the *marifah* alone" in out


def test_the_take_back_refuses_when_the_page_holds_more_script_than_the_text_held() -> None:
    """A surplus came from somewhere else — a quotation, the source's own Arabic.
    Guessing at it would corrupt prose in order to tidy it."""
    from _book_substitution import revert_ineligible

    body = "One حَدّ here, another حَدّ there, a third حَدّ.\n"
    out, n = revert_ineligible(body, "Only one *hadd* in the original.", [], [{"phonetic": "hadd", "script": "حَدّ"}])
    assert n == 0 and out == body


def test_the_take_back_never_touches_a_still_eligible_term() -> None:
    from _book_substitution import revert_ineligible

    allowed = [{"phonetic": "mawaddah", "script": "مَوَدَّة"}]
    body = "The مَوَدَّة stands.\n"
    out, n = revert_ineligible(body, "The *mawaddah* stands.", allowed, allowed)
    assert n == 0 and out == body


def test_the_take_back_skips_quotations_and_headings() -> None:
    from _book_substitution import revert_ineligible

    body = "> a quoted حَدّ stays\n\n## A heading with حَدّ\n"
    out, n = revert_ineligible(body, "*hadd* *hadd*", [], [{"phonetic": "hadd", "script": "حَدّ"}])
    assert n == 0 and out == body


# ─── The two gates that replaced the denylist (post-merge sweep, 2026-08-03) ─
def test_a_glossary_english_word_no_denylist_names_is_still_refused(tmp_path: Path) -> None:
    """THE P0. `mukhtasar-ul-asar-1` holds an entry whose phonetic is the English
    word `approach`, and every denylist here passed it: not in the ninety-word
    seed, not a loanword, not a title, not a person. The page was one compose
    away from "and do not الْمُبَاشَرَة them during that time".

    Nothing was added to a list to fix this. The skeleton of `approach` cannot
    fit `المباشرة` — or any Arabic word, since Arabic has no `p` and no `ch`.
    """
    entries = [
        {"phonetic": "approach", "arabic_script": "الْمُبَاشَرَة", "annotation_class": "teach"},
        {"phonetic": "mahram", "arabic_script": "مَحْرَم", "annotation_class": "teach"},
    ]
    bd = _book(tmp_path, "## 1. A\n\nDo not *approach* them, nor a *mahram*.\n", entries)
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "*approach*" in out
    assert "مَحْرَم" in out  # and the real term beside it still converts


def test_an_unclassified_term_is_never_substituted(tmp_path: Path) -> None:
    """`legacy` means the glossary was harvested and nobody has reviewed it.

    Full-book destructive replacement is not a thing to do on an unreviewed
    list: `kunooz-al-hikmah` carries 266 such entries, among them `surah` paired
    with `صُورَة` — which is *picture*; the chapter of the Quran is `سورة`. The
    skeleton fits perfectly, so only a reviewer can catch it.
    """
    entries = [
        {"phonetic": "surah", "arabic_script": "صُورَة"},  # no annotation_class
        {"phonetic": "mawaddah", "arabic_script": "مَوَدَّة", "annotation_class": "teach"},
    ]
    bd = _book(tmp_path, "## 1. A\n\nThe *surah* opens, and the *mawaddah* holds.\n", entries)
    apply_arabic_substitution(bd)
    out = (bd / "book" / "book.md").read_text(encoding="utf-8")
    assert "*surah*" in out and "مَوَدَّة" in out


def test_the_live_glossaries_carry_nothing_english_into_substitution() -> None:
    """A corpus ratchet over every book in the checkout.

    The three books the sweep reproduced — `mukhtasar-ul-asar-1`,
    `kunooz-al-hikmah`, `kitab-al-riyad` — had 5, 266 and 110 substitutable
    terms, and the sample sentences came back as `الْمُبَاشَرَة`, `The Prophet
    مُحَمَّد … the صُورَة`, and `from العراق to أصفهان`. Every term that survives
    both gates must be a possible romanization of its own script.
    """
    from _translit_skeleton import romanizes

    repo = Path(__file__).resolve().parents[3]
    globs = list(repo.glob("content/*/*/_system/glossary.yml")) + list(repo.glob("content/*/*/*/_system/glossary.yml"))
    checked = 0
    for glossary in globs:
        book_dir = glossary.parent.parent
        if book_dir.name == "knowledge-base":
            continue
        for term in substitutable_terms(book_dir):
            checked += 1
            assert romanizes(term["phonetic"], term["script"]), (
                f"{book_dir.name}: {term['phonetic']!r} would be printed as "
                f"{term['script']!r}, which it does not romanize"
            )
            assert term["style"] == "teach", f"{book_dir.name}: unreviewed term {term['phonetic']!r}"
    if globs:
        assert checked > 0


def test_the_three_sentences_the_sweep_reproduced() -> None:
    """Verbatim from the post-merge sweep, run against the live glossaries."""
    repo = Path(__file__).resolve().parents[3]
    cases = [
        ("mukhtasar-ul-asar-1", "and do not approach them during that time"),
        ("kunooz-al-hikmah", "The Prophet Muhammad taught it, and the surah opens with Bismillah."),
        ("kitab-al-riyad", "He travelled from Iraq to Isfahan, and the Sharia binds him."),
    ]
    for slug, line in cases:
        book_dir = repo / "content" / "Islamic" / slug
        if not (book_dir / "_system" / "glossary.yml").exists():
            continue
        out, replaced = substitute_body(line + "\n", substitutable_terms(book_dir))
        assert replaced == 0, f"{slug}: {out.strip()!r}"


# ─── The Composer button's path: a pure transform ───────────────────────────
def test_substitute_text_writes_nothing_and_reports_what_it_cannot_do(tmp_path: Path) -> None:
    """Why the button looked broken.

    It wrote book.md server-side and reloaded the page. On a book whose glossary
    cannot reach the words on screen, the page bounced and nothing changed, with
    nothing to say why. `unavailable` is the answer — and the transform touches
    no file, so the Composer can apply it to the live editor instead.
    """
    from _book_substitution import substitute_text

    entries = [{"phonetic": "hudud", "arabic_script": "حُدُود", "annotation_class": "teach"}]
    bd = _book(tmp_path, "## 1. A\n\nunchanged on disk\n", entries)
    before = (bd / "book" / "book.md").read_text(encoding="utf-8")

    out = substitute_text(bd, "the *hudud* and the *mawaddah* together.")
    assert out["replaced"] == 1
    assert "حُدُود" in out["text"] and "*mawaddah*" in out["text"]
    assert out["unavailable"] == ["mawaddah"]
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == before
    assert not (bd / "_system" / "book-substitutions.json").exists()


def test_substitute_text_on_a_passage_with_nothing_to_do(tmp_path: Path) -> None:
    from _book_substitution import substitute_text

    bd = _book(tmp_path, "## 1. A\n\nbody\n", [{"phonetic": "hudud", "arabic_script": "حُدُود"}])
    out = substitute_text(bd, "An ordinary English sentence.")
    assert out["replaced"] == 0 and out["unavailable"] == []


def test_a_possessive_keeps_its_emphasis_markers_balanced() -> None:
    """`*Natiq*'s age` became `اَلنَّاطِق*'s age` — the apostrophe blocked the
    closing marker, the engine backtracked to consume none, and the opening `*`
    was stranded. The markers must balance or the term is left alone."""
    natiq = [{"phonetic": "natiq", "script": "اَلنَّاطِق", "style": "teach"}]
    line = "until that *Natiq*'s age is finished"
    assert substitute_body(line, natiq) == (line, 0)


def test_matching_is_case_blind_because_script_has_no_case() -> None:
    """`simplify_transliteration` lowercases the glossary's phonetic, so sixteen
    asaas terms carried script and still printed romanized as `*Natiq*`."""
    natiq = [{"phonetic": "natiq", "script": "اَلنَّاطِق", "style": "teach"}]
    out, n = substitute_body("these are the *Natiq*, the Speaker", natiq)
    assert out == "these are the اَلنَّاطِق, the Speaker" and n == 1
