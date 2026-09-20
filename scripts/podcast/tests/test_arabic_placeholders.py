"""Every prose-rewriting route protects inline Arabic the same way.

isaf-al-talib, bk-28: the translation model dropped `⟪ar:…⟫` Qur'an spans three times even with retries,
because a model cannot reliably copy script it can see and the retry prompt could only NAME the words.
c069b1d3 fixed that for the translation route by swapping each span for a `[[ARn]]` token before the call
and restoring the exact source span after. 0book-fluency and 0book-voice rewrite the same prose under the
same retention gate, so they had the same exposure. The mechanism now lives in ONE module and all three
routes use it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _arabic_placeholders as ph  # noqa: E402

SPAN1 = "⟪ar:وَاعْلَمُوا أَنَّمَا⟫"
SPAN2 = "⟪ar:وَابْنِ السَّبِيلِ⟫"
TEXT = f"Know that {SPAN1} whatever you take as spoils, and the wayfarer {SPAN2} has a share."


def test_spans_become_tokens_and_come_back_as_plain_arabic_never_the_marker():
    """cd9b1398 (isaf-al-talib): restoring the ⟪ar:…⟫ wrapper printed raw marker syntax into the book. The table now
    holds only the Arabic, so the restored text is the source with each marker replaced by its script."""
    p = ph.ArabicPlaceholders()
    protected = p.protect(TEXT)
    assert "وَاعْلَمُوا" not in protected and "[[AR1]]" in protected and "[[AR2]]" in protected
    restored = p.restore(protected)
    assert "⟪" not in restored and "⟫" not in restored
    assert restored == TEXT.replace("⟪ar:", "").replace("⟫", "")
    assert p.table == {"[[AR1]]": "وَاعْلَمُوا أَنَّمَا", "[[AR2]]": "وَابْنِ السَّبِيلِ"}


def test_the_model_is_told_to_keep_every_token_only_when_there_are_tokens():
    p = ph.ArabicPlaceholders()
    assert p.note == ""
    p.protect(TEXT)
    assert "[[AR1]]" in p.note and "exactly once" in p.note


def test_text_without_arabic_is_untouched():
    p = ph.ArabicPlaceholders()
    assert p.protect("plain English") == "plain English" and p.restore("plain English") == "plain English"


def test_a_token_the_model_dropped_is_simply_absent_so_the_retention_gate_can_see_it():
    p = ph.ArabicPlaceholders()
    p.protect(TEXT)
    assert "وَاعْلَمُوا" not in p.restore("Know that whatever you take as spoils.")


def test_an_unknown_token_the_model_invented_is_left_visible_not_guessed():
    p = ph.ArabicPlaceholders()
    p.protect(SPAN1)
    assert "[[AR9]]" in p.restore("text [[AR9]]")


def test_the_windowed_routes_already_shield_arabic_before_the_model_call():
    """Fluency, 0book-voice and the Composer's rearticulate all run through `_run_pass`, which swaps every
    Arabic run for a `[[ARABIC_nnn]]` token BEFORE handing a window to the model and restores it after —
    so the bk-28 failure mode (a model dropping script it could see) was only ever live on the translation
    route, which now uses the shared `[[ARn]]` mechanism above. This pins the ordering so it cannot be
    quietly removed: the protection must come before the call."""
    src = (Path(__file__).resolve().parents[1] / "_book_voice.py").read_text(encoding="utf-8")
    assert "_protect_arabic_runs(" in src and "candidate = fn(" in src
    assert src.index("_protect_arabic_runs(") < src.index("candidate = fn(")
    companion = (Path(__file__).resolve().parents[1] / "_book_voice_companion.py").read_text(encoding="utf-8")
    assert "_run_pass" in companion, "the voice route must keep going through the protected window pass"


def test_the_translation_route_still_uses_the_shared_mechanism():
    import _translation_chunk as tc

    p = ph.ArabicPlaceholders()
    table: dict[str, str] = {}
    assert tc._protect_spans(TEXT, table) == p.protect(TEXT)
