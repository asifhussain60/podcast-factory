"""Arabic script never wears a romanization's italics.

Asif, 2026-08-31, looking at the Book Composer: "why is all the arabic
italicised?" Because italics mark a ROMANIZATION — that is this repo's own
convention, written into REQ-BA-127 — and Arabic restoration replaces the
romanization with script IN PLACE at three separate sites, leaving the marker
around the script that replaced it. `*dunya*` becomes `*دُنْيَا*`.

Eleven books carried it, 619 runs in one of them, and every automatic gate
passed all of them because nothing ever asked.

Half these tests are about what must NOT be touched. A repair that runs over
finished editions has to be provably conservative, or it is worse than the
defect it fixes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _arabic_emphasis import findings, is_script_only, repair  # noqa: E402

AR = "دُنْيَا"
VERSE = "لَا تَسُبُّوا الدُّنْيَا"


# ── what is a defect ────────────────────────────────────────────────────────
def test_italicised_arabic_is_stripped():
    assert repair(f"*{AR}*") == (AR, 1)


def test_an_italicised_arabic_phrase_is_stripped():
    assert repair(f"*{VERSE}*") == (VERSE, 1)


def test_underscore_emphasis_counts_too():
    assert repair(f"_{AR}_") == (AR, 1)


def test_a_quranic_verse_wrapped_in_invisible_bidi_marks_is_stripped():
    """The mushaf's own text arrives with a right-to-left mark before it and a
    left-to-right mark after. Those are formatting, not content — counting them
    as "something other than Arabic" left every such verse italicised, which is
    how eighteen survived the first repair of a real book."""
    text = f"*‏{VERSE} ‎*"
    out, n = repair(text)
    assert n == 1
    assert VERSE in out and "*" not in out


def test_arabic_with_its_own_punctuation_is_still_script_only():
    assert is_script_only("قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ،") is True


# ── what must NOT be touched ────────────────────────────────────────────────
def test_an_italicised_romanization_keeps_its_italics():
    """`*dunya*` is CORRECT — it is the marker REQ-BA-127 is written about."""
    assert repair("*dunya*") == ("*dunya*", 0)


def test_a_mixed_run_keeps_its_italics():
    """The romanization in it still earns the marker, and guessing at a partial
    strip is how a repair starts editing prose."""
    src = f"*dunya ({AR})*"
    assert repair(src) == (src, 0)


def test_an_english_sentence_containing_arabic_keeps_its_italics():
    src = f"*I seek refuge from the {AR} of this world*"
    assert repair(src) == (src, 0)


def test_bold_arabic_is_left_alone():
    """Bold is not the romanization marker. Arabic a human chose to bold is a
    decision, not this artifact."""
    src = f"**{AR}**"
    assert repair(src) == (src, 0)


def test_bare_arabic_is_untouched():
    assert repair(f"He said {AR} here") == (f"He said {AR} here", 0)


def test_plain_english_italics_are_untouched():
    assert repair("*the world*") == ("*the world*", 0)


def test_a_list_bullet_is_not_emphasis():
    src = f"* an item mentioning {AR}\n* another\n"
    assert repair(src) == (src, 0)


# ── the repair's safety property ────────────────────────────────────────────
def test_the_repair_changes_nothing_but_the_markers():
    """The property that makes it safe to run over a finished edition: strip the
    asterisks from both sides and the texts are identical."""
    src = f"He said *{AR}* and *dunya* and **{AR}** and {VERSE}."
    out, _ = repair(src)
    assert out.replace("*", "") == src.replace("*", "")


def test_the_repair_is_idempotent():
    once, n1 = repair(f"*{AR}* and *{VERSE}*")
    twice, n2 = repair(once)
    assert twice == once and n1 == 2 and n2 == 0


def test_findings_report_what_repair_would_change():
    assert findings(f"*{AR}* *dunya* *{VERSE}*") == [AR, VERSE]


def test_empty_and_none_safe():
    assert repair("") == ("", 0)
    assert findings("") == []


# ── the three sites that caused it ──────────────────────────────────────────
def test_both_romanization_to_script_sites_repair_after_replacing():
    """One cause, two call sites. A fix at one of them is a fix that comes back
    through the other.

    `vowel_book` also replaces runs in place and is deliberately NOT one of
    them: it puts VOWELLED ARABIC where bare Arabic was, so an italicised run it
    touches was already italicised before it ran. It can inherit the defect,
    never create it, and repairing there would run the whole text through the
    substitution once per run for no cause it owns."""
    import inspect

    import _verbatim_correct
    import compose_fix

    for mod in (_verbatim_correct, compose_fix):
        assert "_deitalicise" in inspect.getsource(mod), mod.__name__

    import vowel_book

    assert "_deitalicise" not in inspect.getsource(vowel_book)


def test_the_defect_module_reports_it_per_chapter():
    """`_book_defects` is read by the test that records what stands, the compose
    review gate, and the `pf-compose-fix` skill — so all three see this one."""
    from _book_defects import italicised_arabic

    md = f"# B\n\n## One\n\ntext *{AR}* here\n\n## Two\n\nclean\n"
    assert italicised_arabic(md) == [("One", AR)]
