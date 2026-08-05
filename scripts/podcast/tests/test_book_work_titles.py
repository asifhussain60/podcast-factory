"""A cited book prints under the name a reader can read (Asif, 2026-08-05).

Every case here is a shape `ayyuhal-walad` chapter 1 actually printed, plus the
one the rule deliberately refuses: an author naming his own work bare.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _book_work_titles import collapse_work_titles  # noqa: E402

IHYA = "Ihya al-Ulum ad-Din"
MINHAJ = "Minhaj ul-Abideen ila Jannatu Rabbul Alamin"


def test_a_glossed_title_prints_as_its_english_alone() -> None:
    body = f"among them {IHYA} (Revival of the Knowledge of the Path to God), and others"
    out, records = collapse_work_titles(body, [IHYA])
    assert out == "among them Revival of the Knowledge of the Path to God, and others"
    assert records[0]["action"] == "englished"


def test_the_overlays_script_is_dropped_on_the_way_to_the_english() -> None:
    """`Arbaeen (أَرْبَعُون) (Forty Steps)` — the exact printed shape."""
    body = "among them Arbaeen (أَرْبَعُون) (Forty Steps), and others"
    out, _ = collapse_work_titles(body, ["Arbaeen"])
    assert out == "among them Forty Steps, and others"


def test_the_duplicated_italic_title_is_walked_past() -> None:
    """The compose said the title twice and the overlay annotated the INNER copy,
    so between the title and its translation sat a nested bracket."""
    body = f"among them {MINHAJ} (*Minhaj ul-Abideen ila Jannatu Rabbul 'Alamin* (منهاج العابدين إلى جنة رب العالمين)) (The Best Way for the Worshippers of God), and others"
    out, _ = collapse_work_titles(body, [MINHAJ])
    assert out == "among them The Best Way for the Worshippers of God, and others"
    assert "(" not in out and ")" not in out


def test_a_bare_title_is_left_exactly_as_the_author_wrote_it() -> None:
    """THE HALF OF THE RULE THAT REFUSES. No English on the page means no English
    is invented — this is Ghazali's own sentence."""
    body = "look into the Ihya and the others of my writings"
    out, records = collapse_work_titles(body, ["Ihya"])
    assert out == body
    assert records == []


def test_a_bare_title_carrying_script_loses_the_script_and_keeps_its_name() -> None:
    body = f"his own larger works — the *{IHYA}* (إِحْيَاءُ عُلُومِ الدِّيْن), the others"
    out, records = collapse_work_titles(body, [IHYA])
    assert out == f"his own larger works — the *{IHYA}*, the others"
    assert records[0]["action"] == "stripped-brackets"


def test_emphasis_around_the_title_goes_with_it() -> None:
    body = f"among them *{IHYA}* (Revival of the Sciences), and others"
    out, _ = collapse_work_titles(body, [IHYA])
    assert out == "among them Revival of the Sciences, and others"


def test_running_the_pass_twice_changes_nothing_the_second_time() -> None:
    body = f"among them {IHYA} (Revival of the Sciences) and Arbaeen (أَرْبَعُون) (Forty Steps)."
    once, _ = collapse_work_titles(body, [IHYA, "Arbaeen"])
    twice, records = collapse_work_titles(once, [IHYA, "Arbaeen"])
    assert once == twice
    assert records == []


def test_every_occurrence_on_a_line_is_handled_not_just_the_first() -> None:
    body = f"{IHYA} (Revival of the Sciences) and again {IHYA} (Revival of the Sciences)."
    out, records = collapse_work_titles(body, [IHYA])
    assert out == "Revival of the Sciences and again Revival of the Sciences."
    assert len(records) == 2


def test_a_quotation_line_is_never_rewritten() -> None:
    """`_SKIP_LINE` — a block quote is the source speaking, not the edition's prose."""
    body = f"> {IHYA} (Revival of the Sciences)"
    out, records = collapse_work_titles(body, [IHYA])
    assert out == body
    assert records == []


def test_the_title_inside_a_longer_word_is_not_a_title() -> None:
    body = "the Ihyaic tradition (something else) continues"
    out, records = collapse_work_titles(body, ["Ihya"])
    assert out == body
    assert records == []


def test_no_work_title_terms_means_the_body_is_returned_untouched() -> None:
    body = f"among them {IHYA} (Revival of the Sciences)"
    out, records = collapse_work_titles(body, [])
    assert out == body
    assert records == []


def test_a_glossary_ayn_the_prose_dropped_still_matches() -> None:
    """The reason chapter 1 nested the title inside itself.

    `simplify_transliteration` drops an ayn INSIDE a word but keeps one at the
    start of a word, so the glossary's `Rabbul 'Alamin` never matched the
    running `Rabbul Alamin` — only the italic duplicate, which had kept its ayns.
    """
    from _book_work_titles import _spellings

    spellings = _spellings("Minhaj ul-'Abideen ila Jannatu Rabbul 'Alamin")
    assert MINHAJ in spellings, spellings
    assert _spellings("Ihya al-Ulum ad-Din") == ["Ihya al-Ulum ad-Din"]


def test_a_bracket_that_merely_mentions_the_title_is_not_a_duplicate() -> None:
    """`startswith`, not containment: a note ABOUT the book is not its name."""
    from _book_work_titles import _repeats

    assert _repeats("*Ihya al-Ulum ad-Din* (إحياء)", "Ihya al-Ulum ad-Din")
    assert not _repeats("a work he finished long before the Ihya al-Ulum ad-Din", "Ihya al-Ulum ad-Din")


def test_the_reversed_shape_loses_its_bracket() -> None:
    """The author put the English in the sentence and the title in the bracket.
    The English is already there, so the bracket is the second name the rule
    removes — the shape chapter 9 printed."""
    body = "We have treated this at length in the Revival of the Sciences of Religion (*Ihya Ulum ad-Din*), so seek it there."
    out, records = collapse_work_titles(body, ["Ihya Ulum ad-Din"])
    assert out == "We have treated this at length in the Revival of the Sciences of Religion, so seek it there."
    assert records[0]["action"] == "dropped-second-name"


def test_the_reversed_shape_does_not_eat_a_translation_bracket() -> None:
    body = f"among them {IHYA} (Revival of the Sciences), and others"
    out, _ = collapse_work_titles(body, [IHYA])
    assert out == "among them Revival of the Sciences, and others"
