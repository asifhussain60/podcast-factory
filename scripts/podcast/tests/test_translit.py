#!/usr/bin/env python3
"""The transliteration fold: plain house style, without eating the punctuation.

`simplify_transliteration` reduces scholarly Arabic transliteration to the plain
form the reading edition prints — `Jaʿfar` to `Jafar`, `Qur'an` to `Quran`. Its
hazard is that the character it removes, the apostrophe, is also an English
possessive, a clitic, a root radical and a quotation mark.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _translit import simplify_transliteration  # noqa: E402


# ─── Quotation marks are not ayns (2026-08-02) ──────────────────────────────
def test_single_quoted_speech_survives_the_fold():
    """`He said, 'Go now.'` must not print as `He said, Go now.`

    The closing mark of a quotation and a word-final ayn are locally identical —
    a letter before, a non-letter after — so judged alone both folded and the
    fold silently destroyed quoted speech: 7 quoted spans vanished from
    `the-master-and-the-disciple` and 18 from `asaas-al-taveel`. An OPENING quote
    is unambiguous, so pairing decides the closer.
    """
    assert simplify_transliteration("He said, 'Go now.'") == "He said, 'Go now.'"
    assert simplify_transliteration("'Go,' he said, 'now.'") == "'Go,' he said, 'now.'"
    assert simplify_transliteration("(عُبَيْدُ, 'little servant of Allah')") == "(عُبَيْدُ, 'little servant of Allah')"


def test_a_word_final_ayn_still_folds_when_no_quote_is_open():
    # The pairing must not become a licence to keep every trailing apostrophe.
    assert simplify_transliteration("the sama' of it") == "the sama of it"
    assert simplify_transliteration("Shia' and Qur'an") == "Shia and Quran"


def test_a_quote_opening_a_line_is_recognised():
    # `prev not in "-"` was False for the empty string, since "" is a substring
    # of everything — so a line that STARTS with a quotation lost its mark.
    assert simplify_transliteration("'Go now.'") == "'Go now.'"


def test_quote_state_does_not_leak_across_lines():
    # An unbalanced quote must cost at most one line, never turn every later ayn
    # into a closing mark.
    out = simplify_transliteration("he said 'go\nthe sama' of it")
    assert out.endswith("the sama of it")
