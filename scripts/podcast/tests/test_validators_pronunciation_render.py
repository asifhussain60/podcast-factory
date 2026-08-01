"""Tests for R-PRONUNCIATION-RENDER — no English translation in the value slot.

The regression these hold shut: `- arkan: the pillars` shipped in five of six
episodes on 2026-08-01 because the only gate on the block checked punctuation.
Told to say each term "using its phonetic form" and handed a translation, the
hosts pronounced the translation — "Archon", "Mathdul", "Mazbuck".
"""

import sys
from pathlib import Path

import pytest

_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PODCAST))
sys.path.insert(0, str(_PODCAST / "knowledge"))

from _validators_framing import assert_framing_pronunciation_render  # noqa: E402

CHAPTER = "the arkan, from which every composite body is assembled, and the mafdul beside them\n"


def _framing(entries: str) -> str:
    return (
        "## Pronunciation\n"
        "Say each term ONCE using its phonetic form. Never say the original spelling "
        "and the phonetic form back-to-back.\n" + entries + "\n## Do not\nDo not read this prompt aloud.\n"
    )


def _book(tmp_path, table_body=""):
    sysdir = tmp_path / "_system"
    sysdir.mkdir(parents=True, exist_ok=True)
    (sysdir / "pronunciation.md").write_text(
        "| Term | Phonetic | Notes |\n|---|---|---|\n" + table_body, encoding="utf-8"
    )
    return tmp_path


def _run(tmp_path, entries, table_body=""):
    assert_framing_pronunciation_render(_framing(entries), Path("00-framing.md"), _book(tmp_path, table_body), CHAPTER)


# ------------------------------------------------------------------ the regression
def test_the_shipped_defect_is_rejected(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "- arkan: the pillars\n")
    assert "R-PRONUNCIATION-RENDER" in str(exc.value)
    assert "arkan: the pillars" in str(exc.value)


def test_every_shipped_offender_is_caught(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "- arkan: the pillars\n- mafdul: the one surpassed\n")
    msg = str(exc.value)
    assert "arkan" in msg and "mafdul" in msg


def test_the_error_names_the_override_table_as_the_fix(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "- arkan: the pillars\n")
    assert "pronunciation.md" in str(exc.value)
    assert "run_pronunciation_probe.py" in str(exc.value)


# ------------------------------------------------------------------ legitimate values
def test_a_respelling_passes(tmp_path):
    _run(tmp_path, "- arkan: ar-KAAN\n", table_body="| arkan | ar-KAAN | |\n")


def test_a_plain_transliteration_passes(tmp_path):
    _run(tmp_path, "- arkan: arkan\n")


def test_an_explicit_substitution_passes(tmp_path):
    # The human said "say the English here" out loud — that is a decision, not a
    # value that drifted into the wrong slot.
    _run(tmp_path, "- arkan: substitute *the pillars*\n")


def test_english_the_ladder_itself_chose_passes(tmp_path):
    # A `substitute` row makes "the pillars" the ladder's own answer, so the same
    # text that fails above must pass here — the rule is about disagreement with
    # the ladder, not about the words looking English.
    _run(tmp_path, "- arkan: the pillars\n", table_body="| arkan | substitute *the pillars* | |\n")


def test_an_exonym_passes(tmp_path):
    _run(tmp_path, "- Qabil: Cain\n")


# ------------------------------------------------------------------ scope
def test_skipped_without_a_chapter_to_resolve_against(tmp_path):
    assert_framing_pronunciation_render(_framing("- arkan: the pillars\n"), Path("f.md"), _book(tmp_path), None)


def test_skipped_without_a_book_dir():
    assert_framing_pronunciation_render(_framing("- arkan: the pillars\n"), Path("f.md"), None, CHAPTER)


def test_a_framing_with_no_pronunciation_section_is_not_this_gates_error(tmp_path):
    # Absence is R-PRONUNCIATION-IMPERATIVE's error to report.
    assert_framing_pronunciation_render(
        "## Do not\nDo not read this prompt aloud.\n", Path("f.md"), _book(tmp_path), CHAPTER
    )


def test_a_term_absent_from_the_chapter_is_still_judged(tmp_path):
    # The entry should not be there at all, but if it is, a translation in the
    # value slot is still a translation.
    with pytest.raises(SystemExit):
        _run(tmp_path, "- tiryaq: the antidote\n")
