"""Putting the Arabic script back beside an inline term, without damaging it.

Every case here is a defect the book-challenger found in a real edition on
2026-07-21. The pass writes into finished prose, so its failure mode is not an
exception — it is a book that looks fine and says something wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_inline_arabic import apply_inline_arabic  # noqa: E402


def book(tmp_path: Path, body: str, entries: list[dict]) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(body, encoding="utf-8")
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 1, "entries": entries}, allow_unicode=True),
        encoding="utf-8",
    )
    return bd


def read(bd: Path) -> str:
    return (bd / "book" / "book.md").read_text(encoding="utf-8")


def write_glossary(bd: Path, entries: list[dict]) -> None:
    """Replace the glossary of an existing book — for the re-vowelling case."""
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 1, "entries": entries}, allow_unicode=True),
        encoding="utf-8",
    )


ALLAH = {"phonetic": "Allah", "arabic_script": "الله"}
ABD_ALLAH = {"phonetic": "Abd Allah", "arabic_script": "عبد الله"}


def test_the_script_lands_beside_the_first_mention(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nHe called upon Allah in the morning.\n", [ALLAH])
    assert apply_inline_arabic(bd) == 1
    assert "Allah (الله)" in read(bd)


def test_only_the_first_mention_per_chapter_is_annotated(tmp_path: Path) -> None:
    """Repeating the script at every mention turns prose into a glossary."""
    bd = book(tmp_path, "## 1. A\n\nAllah, and again Allah, and Allah.\n", [ALLAH])
    assert apply_inline_arabic(bd) == 1
    assert read(bd).count("الله") == 1


def test_a_short_term_never_fires_inside_a_longer_name(tmp_path: Path) -> None:
    """The live defect: once "Abd Allah" had been annotated in an earlier line it
    left the pending set, so on a later line the standalone "Allah" entry matched
    the Allah INSIDE "son of Abd Allah" — printing "Abd Allah (الله)" and leaving
    one name carrying two different scripts in the same chapter."""
    body = "## 1. A\n\nHe met Abd Allah at the gate.\n\nI am free, son of Abd Allah.\n"
    bd = book(tmp_path, body, [ALLAH, ABD_ALLAH])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "Abd Allah (عبد الله)" in out
    assert "Abd Allah (الله)" not in out, "the short entry fired inside the name"


def test_a_mention_that_already_carries_its_script_is_left_alone(tmp_path: Path) -> None:
    # The pass re-DERIVES annotations each run, so the count it returns is the
    # standing total (1 mention carries script), not a delta. The invariant is
    # that the text does not change and the script is not doubled.
    body = "## 1. A\n\nHe called upon Allah (الله) once.\n"
    bd = book(tmp_path, body, [ALLAH])
    apply_inline_arabic(bd)
    assert read(bd) == body
    assert read(bd).count("الله") == 1


def test_an_intervening_quote_does_not_hide_an_existing_annotation(tmp_path: Path) -> None:
    """The live defect: the approved base wrote `"Kab al-Ahbar (كعب الأحبار)"`
    with the closing quote BETWEEN term and parenthetical. A strict `\\s*\\(`
    check walked straight past it and added the script a second time, eight
    characters away."""
    kab = {"phonetic": "Kab al-Ahbar", "arabic_script": "كعب الأحبار"}
    body = '## 1. A\n\nHe said "Kab al-Ahbar (كعب الأحبار)" plainly.\n'
    bd = book(tmp_path, body, [kab])
    apply_inline_arabic(bd)
    assert read(bd) == body
    assert read(bd).count("كعب الأحبار") == 1


def test_the_pass_is_idempotent(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nAllah and Abd Allah both appear.\n", [ALLAH, ABD_ALLAH])
    first = apply_inline_arabic(bd)
    assert first > 0
    once = read(bd)
    apply_inline_arabic(bd)
    assert read(bd) == once  # re-derivation is byte-stable


def test_blockquotes_and_headings_are_never_annotated(tmp_path: Path) -> None:
    """Quoted Arabic already carries its own script; a heading is not prose."""
    body = "## Allah in the chapter title\n\n> Allah is named in this quote.\n"
    bd = book(tmp_path, body, [ALLAH])
    assert apply_inline_arabic(bd) == 0
    assert "الله" not in read(bd)


def test_honorific_formulas_and_name_particles_are_not_terms(tmp_path: Path) -> None:
    """A formula attached to a name is not a rendering OF the name, and "ibn" is
    grammatical glue — annotating it split a proper name in half."""
    entries = [
        {"phonetic": "Joseph", "arabic_script": "عليه السلام"},
        {"phonetic": "ibn", "arabic_script": "بن"},
    ]
    bd = book(tmp_path, "## 1. A\n\nSalih ibn Joseph spoke.\n", entries)
    assert apply_inline_arabic(bd) == 0


def test_a_term_with_no_script_is_skipped(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nThe Umma gathered.\n", [{"phonetic": "Umma", "arabic_script": ""}])
    assert apply_inline_arabic(bd) == 0


def test_a_missing_glossary_is_not_an_error(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("## 1. A\n\nText.\n", encoding="utf-8")
    assert apply_inline_arabic(bd) == 0


# ─── the gloss rule ──────────────────────────────────────────────────────────
# The book's own convention is `English meaning (*transliteration*)`. Once the
# Arabic script is beside a term the romanisation earns nothing — the meaning is
# already the running prose — so the script REPLACES it rather than nesting
# inside it. Found live 2026-07-21: "his gate (*bab* (باب))", the same word three
# ways, two brackets deep.
NATIQ = {"phonetic": "al-Imam al-Natiq", "arabic_script": "الإمام الناطق"}
IMAM = {"phonetic": "Imam", "arabic_script": "الإمام"}
BAB = {"phonetic": "bab", "arabic_script": "باب"}
JAFAR = {"phonetic": "Jafar ibn Mansur al-Yaman", "arabic_script": "جعفر بن منصور اليمن"}
TUR = {"phonetic": "Tur", "arabic_script": "الطور"}


def test_the_script_replaces_a_transliteration_gloss(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nhis gate (*bab*) opened.\n", [BAB])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "his gate (باب) opened." in out
    assert "bab" not in out, "the romanisation should be gone, not nested"


def test_an_unemphasised_gloss_is_replaced_too(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nhis gate (bab) opened.\n", [BAB])
    apply_inline_arabic(bd)
    assert "his gate (باب) opened." in read(bd)


def test_a_personal_name_keeps_its_transliteration(tmp_path: Path) -> None:
    """A reader needs "Jafar ibn Mansur al-Yaman" romanised; they do not need
    "bab" romanised once the script is beside it."""
    bd = book(tmp_path, "## 1. A\n\nThe author is Jafar ibn Mansur al-Yaman.\n", [JAFAR])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "Jafar ibn Mansur al-Yaman (جعفر بن منصور اليمن)" in out


def test_a_name_inside_a_gloss_bracket_also_keeps_it(tmp_path: Path) -> None:
    """The replace rule must not strip a name down to bare script."""
    bd = book(tmp_path, "## 1. A\n\nthe author (*Jafar ibn Mansur al-Yaman*) wrote it.\n", [JAFAR])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "Jafar ibn Mansur al-Yaman" in out, "a name must stay romanised"
    assert "جعفر بن منصور اليمن" in out


def test_a_term_outside_any_bracket_is_appended_not_replaced(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nHe mentions Tur once.\n", [TUR])
    apply_inline_arabic(bd)
    assert "Tur (الطور) once" in read(bd)


def test_overlapping_entries_do_not_print_the_idea_twice(tmp_path: Path) -> None:
    """The bare "Imam" (الإمام) sits inside "al-Imam al-Natiq" (الإمام الناطق).
    Annotating both printed the same idea twice in one breath."""
    bd = book(tmp_path, "## 1. A\n\nthe speaking Imam (*al-Imam al-Natiq*) rules.\n", [NATIQ, IMAM])
    apply_inline_arabic(bd)
    out = read(bd)
    assert "the speaking Imam (الإمام الناطق) rules." in out
    assert out.count("الإمام") == 1


def test_the_whole_live_passage(tmp_path: Path) -> None:
    """The exact sentence from the real edition that prompted this rule."""
    body = (
        "## 1. A\n\nvocabulary: the speaking Imam (*al-Imam al-Natiq*), his gate "
        "(*bab*), his successor (*wasi*), his summoners (*duat*).\n"
    )
    entries = [
        NATIQ,
        IMAM,
        BAB,
        {"phonetic": "wasi", "arabic_script": "الوصي"},
        {"phonetic": "duat", "arabic_script": "الدعاة"},
    ]
    bd = book(tmp_path, body, entries)
    apply_inline_arabic(bd)
    assert "the speaking Imam (الإمام الناطق), his gate (باب), his successor (الوصي), his summoners (الدعاة)." in read(
        bd
    )


def test_the_gloss_rule_is_idempotent(tmp_path: Path) -> None:
    bd = book(tmp_path, "## 1. A\n\nhis gate (*bab*) opened.\n", [BAB])
    apply_inline_arabic(bd)
    once = read(bd)
    apply_inline_arabic(bd)
    assert read(bd) == once  # normalize -> re-derive lands on the same bytes


# ─── the annotation policy: once, intelligently, and only where it helps ──────
def test_a_teach_term_is_introduced_once_in_the_book_not_per_chapter(tmp_path: Path) -> None:
    body = "## 1. A\n\nThe natiq spoke first.\n\n## 2. B\n\nThe natiq spoke again.\n"
    bd = book(tmp_path, body, [{"phonetic": "natiq", "arabic_script": "الناطق", "annotation_class": "teach"}])
    assert apply_inline_arabic(bd) == 1
    out = read(bd)
    assert out.count("الناطق") == 1
    assert "The natiq (الناطق) spoke first." in out
    assert "The natiq spoke again." in out  # chapter 2 uses the term plainly


def test_a_gloss_carries_the_script_alone_with_no_romanization(tmp_path: Path) -> None:
    """Zero transliteration inside a gloss (Asif, 2026-08-02).

    A teach-class gloss used to become `(bab, باب)` — name AND script — on the
    reasoning that a reader without Arabic could otherwise never say the book's
    core terms. That is retired: the Arabic on this page is always vowelled,
    which is what makes it readable to the person the edition is printed for, and
    the romanization keeps its home in the podcast lane where pronunciation is
    the point.
    """
    bd = book(
        tmp_path,
        "## 1. A\n\nHe is his gate (*bab*) among them.\n",
        [{"phonetic": "bab", "arabic_script": "باب", "annotation_class": "teach"}],
    )
    assert apply_inline_arabic(bd) == 1
    out = read(bd)
    assert "his gate (باب) among them." in out
    assert "bab" not in out, "no Latin-script Arabic may survive inside the gloss"


def test_re_vowelling_the_glossary_does_not_double_annotate(tmp_path: Path) -> None:
    """The measured failure: `Tur (اَلطُّور), الطور)`.

    The inverse pass used to match the glossary's `arabic_script` byte for byte,
    so an annotation written when a term was BARE became unrecognisable the
    moment `5a-glossary-vowel` added its marks — neither removed nor reseeded,
    and a second paren written beside it. Keying on the consonantal skeleton
    fixes it, and is sound because a vowelling may add marks but never alters a
    letter (`_vowelling.rejection_reason`).

    Script-only glosses make this the difference between untidy and unrecoverable:
    with the romanization gone, a stale paren cannot be attributed to any term.
    """
    bare = "الطور"
    vowelled = "اَلطُّور"
    bd = book(
        tmp_path,
        "## 1. A\n\nHe climbed the mount (*Tur*) at dawn.\n",
        [{"phonetic": "Tur", "arabic_script": bare, "annotation_class": "teach"}],
    )
    assert apply_inline_arabic(bd) == 1
    assert f"the mount ({bare}) at dawn." in read(bd)

    # The glossary is re-vowelled AFTER the overlay already exists.
    write_glossary(bd, [{"phonetic": "Tur", "arabic_script": vowelled, "annotation_class": "teach"}])
    apply_inline_arabic(bd)

    out = read(bd)
    assert out.count("(") - out.count("(*") == 1, f"exactly one paren survives, got: {out!r}"
    assert vowelled in out and bare not in out, "and it carries the NEW script"


def test_familiar_and_silent_terms_are_never_annotated(tmp_path: Path) -> None:
    """Mount Sinai, Quran, famous prophets — the English form IS the word."""
    body = "## 1. A\n\nThe light of Sinai shone, as Joseph knew.\n"
    bd = book(
        tmp_path,
        body,
        [
            {
                "phonetic": "Sinai",
                "arabic_script": "الطور",
                "annotation_class": "familiar",
                "english_equivalent": "Mount Sinai",
            },
            {"phonetic": "Joseph", "arabic_script": "يوسف", "annotation_class": "silent"},
        ],
    )
    assert apply_inline_arabic(bd) == 0
    assert read(bd) == body


def test_a_name_term_keeps_its_romanisation_and_gains_script_once(tmp_path: Path) -> None:
    body = "## 1. A\n\nSalih spoke.\n\n## 2. B\n\nSalih answered.\n"
    bd = book(tmp_path, body, [{"phonetic": "Salih", "arabic_script": "صالح", "annotation_class": "name"}])
    assert apply_inline_arabic(bd) == 1
    out = read(bd)
    assert "Salih (صالح) spoke." in out
    assert out.count("صالح") == 1


def test_no_annotation_when_the_script_is_in_the_quotation_block_beside_it(tmp_path: Path) -> None:
    """The Adam case: the annotation sat in the translation line directly under
    the vowelled Quranic block that already spells آدم. The reader was looking at
    the script twice in two lines."""
    body = (
        "## 1. A\n\n> يَا بَنِي آدَمَ قَدْ أَنْزَلْنَا عَلَيْكُمْ لِبَاسًا\n\nO children of Adam, We have sent down upon you a garment.\n"
    )
    bd = book(tmp_path, body, [{"phonetic": "Adam", "arabic_script": "آدم", "annotation_class": "name"}])
    assert apply_inline_arabic(bd) == 0
    assert read(bd) == body


def test_an_unclassified_book_composes_exactly_as_before(tmp_path: Path) -> None:
    """No class on any entry -> legacy first-use-per-chapter behaviour, so books
    that predate the policy are byte-identical under it."""
    body = "## 1. A\n\nAllah is one.\n\n## 2. B\n\nAllah is one.\n"
    bd = book(tmp_path, body, [ALLAH])
    assert apply_inline_arabic(bd) == 2
    assert read(bd).count("الله") == 2


def test_an_unknown_annotation_class_is_refused(tmp_path: Path) -> None:
    import pytest
    from _annotation_policy import AnnotationPolicyError

    bd = book(tmp_path, "## 1. A\n\nAllah.\n", [{**ALLAH, "annotation_class": "maybee"}])
    with pytest.raises(AnnotationPolicyError, match="maybee"):
        apply_inline_arabic(bd)


def test_a_reclassification_removes_the_annotation_it_no_longer_wants(tmp_path: Path) -> None:
    """Annotations are DERIVED state. A term annotated before the policy existed
    loses its script the moment it is classified familiar — otherwise the old
    apparatus would be fossilised in the prose forever."""
    bd = book(tmp_path, "## 1. A\n\nHe called upon Allah in the morning.\n", [ALLAH])
    apply_inline_arabic(bd)
    assert "Allah (الله)" in read(bd)
    # The policy arrives: Allah is familiar.
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump(
            {"schema_version": 1, "entries": [{**ALLAH, "annotation_class": "familiar"}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    apply_inline_arabic(bd)
    out = read(bd)
    assert "الله" not in out
    assert "He called upon Allah in the morning." in out


def test_per_chapter_repeats_collapse_when_a_term_becomes_teach(tmp_path: Path) -> None:
    body = "## 1. A\n\nThe natiq spoke.\n\n## 2. B\n\nThe natiq answered.\n"
    entry = {"phonetic": "natiq", "arabic_script": "الناطق"}
    bd = book(tmp_path, body, [entry])
    apply_inline_arabic(bd)
    assert read(bd).count("الناطق") == 2  # legacy: once per chapter
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump(
            {"schema_version": 1, "entries": [{**entry, "annotation_class": "teach"}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    apply_inline_arabic(bd)
    assert read(bd).count("الناطق") == 1  # policy: once in the book


def test_every_gloss_of_a_term_converts_not_only_the_first(tmp_path: Path) -> None:
    """CONVERSION is not ANNOTATION, and only the second is rationed.

    Both wore the same shape and were folded through the same once-per-book
    `pending`, so the second time the author glossed a term it kept its
    romanization — one page reading `governance (سِيَاسَة)` and the next
    `governance (siyasa)`. Changing what is inside a bracket the author already
    wrote adds no apparatus, so it is unconditional; adding a NEW bracket is
    apparatus and stays rationed (the test above).
    """
    body = (
        "## 1. A\n\nHe wrote of governance (*siyasa*) at length.\n\n"
        "## 2. B\n\nAnd returned to governance (*siyasa*) once more.\n"
    )
    bd = book(tmp_path, body, [{"phonetic": "siyasa", "arabic_script": "سِيَاسَة", "annotation_class": "teach"}])

    apply_inline_arabic(bd)
    out = read(bd)

    assert out.count("(سِيَاسَة)") == 2, f"both glosses convert, got: {out!r}"
    assert "siyasa" not in out, "no Latin-script Arabic survives in a gloss"


def test_a_reversed_gloss_keeps_its_english_translation(tmp_path: Path) -> None:
    """`*Qutb* (pole)` must NOT become `*Qutb* (قُطْب)`.

    The book glosses both ways round: `the ranks (hudud)` puts the
    transliteration in the bracket, `*Qutb* (pole)` puts the MEANING there.
    Converting the second destroys the translation and leaves the Arabic term
    glossed by itself. Caught on the real book, where `pole` had reached the
    glossary as a term — it sits inside a bracket exactly where a transliteration
    would, and the OCR has قطب nearby, so the fill gave it script.
    """
    entries = [
        {"phonetic": "qutb", "arabic_script": "قُطْب", "annotation_class": "teach"},
        {"phonetic": "pole", "arabic_script": "قُطْب", "annotation_class": "teach"},
    ]
    bd = book(tmp_path, "## 1. A\n\nthe terms cluster: *Qutb* (pole), and so on.\n", entries)

    apply_inline_arabic(bd)
    out = read(bd)

    assert "*Qutb* (pole)" in out, f"the English translation was destroyed: {out!r}"


def test_the_ordinary_direction_still_converts(tmp_path: Path) -> None:
    """The guard above must be narrow enough not to block the normal shape."""
    bd = book(
        tmp_path,
        "## 1. A\n\nthe ranks (hudud) of the hierarchy.\n",
        [{"phonetic": "hudud", "arabic_script": "حُدُود", "annotation_class": "teach"}],
    )
    apply_inline_arabic(bd)
    assert "the ranks (حُدُود) of the hierarchy." in read(bd)


# ─── Two shapes the conversion must NOT touch (2026-08-02) ──────────────────
# Both were found by running the apparatus over the seven Islamic books and
# diffing the result sentence by sentence. Neither had a test, and neither was
# visible in any count: the page kept the same number of brackets.
from _book_gloss import _convert_glosses, _script_already_precedes  # noqa: E402
from _book_inline_arabic import _normalize_annotations  # noqa: E402

_LETTERS = [{"phonetic": "Kun", "script": "كُن", "style": "teach"}]


def test_a_word_discussed_as_letters_keeps_its_pronunciation():
    """`كُن (Kun)` is the correct printed form, not a gloss awaiting conversion.

    Converting it produced `كُن (كُن)` — the script said twice, the pronunciation
    gone, in a sentence whose subject is which two letters the word is made of.
    It is also BK-N4, a P0 in the challenger spec, and the carve-out Asif kept
    when he scoped the zero-transliteration rule to Arabic vocabulary.
    """
    line = "from them is derived كُن (Kun), which is two letters"
    out, n = _convert_glosses(line, _LETTERS, {"Kun": _LETTERS[0]})
    assert n == 0
    assert out == line


def test_an_ordinary_gloss_still_converts():
    terms = [{"phonetic": "bab", "script": "بَاب", "style": "teach"}]
    out, n = _convert_glosses("his gate (bab) opened", terms, {"bab": terms[0]})
    assert n == 1
    assert out == "his gate (بَاب) opened"


def test_the_guard_compares_by_skeleton_not_bytes():
    # The script in the prose carries the book's vowelling; the glossary's copy
    # carries `vowel_glossary`'s. Byte comparison would miss the match and
    # convert anyway.
    assert _script_already_precedes("derived كُنْ ", len("derived كُنْ "), "كُن")
    assert not _script_already_precedes("derived nothing ", len("derived nothing "), "كُن")


def test_a_bracket_holding_the_authors_english_is_not_the_machines_output():
    """`(script, 'what it means')` must survive normalisation intact.

    `normalize_arabic` DISCARDS non-Arabic characters, so this bracket reduced to
    the same skeleton as a bare `(script)` and was claimed as this pass's own
    annotation — then rewritten, deleting the translation. The sentence it
    happened in exists to say what the two names MEAN.
    """
    terms = [{"phonetic": "Ubayd Allah", "script": "عُبَيْدُ اللَّهِ", "style": "teach"}]
    body = "He said: Ubayd Allah (عُبَيْدُ اللَّهِ, 'little servant of Allah'), son of Abd Allah."
    assert _normalize_annotations(body, terms) == body


def test_a_pure_machine_annotation_still_folds():
    # The guard must not cost normalisation its actual job.
    terms = [{"phonetic": "Ubayd Allah", "script": "عُبَيْدُ اللَّهِ", "style": "teach"}]
    body = "He said: Ubayd Allah (عُبَيْدُ اللَّهِ), son of Abd Allah."
    assert _normalize_annotations(body, terms) == "He said: Ubayd Allah, son of Abd Allah."


def test_a_term_is_not_annotated_when_its_script_is_already_beside_it():
    """The book's vowelling of a run is rarely the glossary's.

    `_script_already_near` compared bytes, so `عُبَيْدُ اللَّهِ` standing in the
    prose neither contained nor was contained by `عُبَيْدُ اللّٰه` from the
    glossary, and the pass annotated a name whose script sat three characters
    away — printing it twice in one breath and stranding the author's own
    translation after the duplicate.
    """
    from _book_inline_arabic import _script_already_near

    prose = "Ubayd Allah (عُبَيْدُ اللَّهِ, 'little servant of Allah'), son of"
    at = prose.index(" (")
    assert _script_already_near(prose, at, "عُبَيْدُ اللّٰه") is True
    assert _script_already_near(prose, at, "اَلْحُجَج") is False


def test_the_retired_gloss_form_folds_across_a_vowelling_difference():
    """`(bab, باب)` must fold even when the two vowellings differ.

    The fold was an exact string replace, so it required the prose's marks on a
    run to equal the glossary's byte for byte — and they usually do not, because
    different passes marked them at different times. It therefore caught 7 of the
    13 retired brackets in `the-master-and-the-disciple` and left six printing the
    romanisation the 2026-08-02 rule retired.
    """
    from _book_inline_arabic import _normalize_annotations

    terms = [{"phonetic": "Tur", "script": "الطور", "style": "teach"}]
    out = _normalize_annotations("he reached the Mount (Tur, اَلطُّور) at dawn", terms)
    assert out == "he reached the Mount (*Tur*) at dawn"


def test_a_phonetic_beside_an_UNRELATED_script_is_not_folded():
    # The skeleton match is what makes the fold safe: same phonetic, different
    # word, and the bracket is somebody else's.
    from _book_inline_arabic import _normalize_annotations

    terms = [{"phonetic": "Tur", "script": "الطور", "style": "teach"}]
    line = "he reached the Mount (Tur, الشمس) at dawn"
    assert _normalize_annotations(line, terms) == line


# ─── A corrected glossary script must not strand its old annotation ─────────
def test_a_second_annotation_is_never_written_beside_a_first(tmp_path: Path) -> None:
    """A glossary row gets CORRECTED, not just vowelled.

    `al-anwaar-al-lateefah` paired `adam` — non-existence — with `آدَم`, Adam the
    prophet. `عَدَم` and `آدَم` are different words with different skeletons, so
    the fold cannot recognise the old bracket as its own (and should not: the
    skeleton key is what makes vowelling safe). The pass wrote a second beside
    it: `*adam* (عَدَم) (آدَم)`. Two annotations of one term is never right.
    """
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from _book_inline_arabic import _script_already_near

    line = "pulling them out of an *adam* (آدَم), a nothingness"
    at = line.index("*adam*")
    assert _script_already_near(line, at, "عَدَم") is True


def test_an_honorific_formula_is_not_an_annotation() -> None:
    """`Khidr (ع)` says *peace be upon him*. Counting it would keep the name off
    the page in script for ever."""
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from _book_inline_arabic import _script_already_near

    line = "And accept the counsel of Khidr (ع) when he said:"
    assert _script_already_near(line, line.index("Khidr"), "اَلْخِضْر") is False


def test_the_term_s_own_script_still_suppresses_a_repeat() -> None:
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from _book_inline_arabic import _script_already_near

    line = "the counsel of Khidr (اَلْخِضْر) when he said:"
    assert _script_already_near(line, line.index("Khidr"), "الخضر") is True
