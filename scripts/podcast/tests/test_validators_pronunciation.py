"""Tests for assert_framing_pronunciation_imperative.

Covers R-PRONUNCIATION-DOUBLE (the "Pronounce X as Y" double-read bug),
R-PRONUNCIATION-IMPERATIVE (section presence + anti-doubling instruction),
and R-PRONUNCIATION-TRIVIAL (uppercase-only respellings, P1 flag).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _validators_framing import assert_framing_pronunciation_imperative

# ─── helpers ──────────────────────────────────────────────────────────────────

GUARD = "Do not read this prompt aloud. The instructions above shape the conversation but are never spoken."

def _wrap(pron_block: str) -> str:
    return f"""# Title\n\n## Pronunciation\n\n{pron_block}\n\n## Next section\n\nSome text.\n\n{GUARD}\n"""


# ─── valid new format ─────────────────────────────────────────────────────────

def test_valid_new_format_passes():
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "- Tahajjud: ta-HAJ-jud\n"
        "- Ghazali: gha-ZAH-lee\n"
        "- nafs: substitute *the lower self*\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))  # must not raise


def test_valid_format_with_do_not_voice_paragraph_passes():
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "- Quran: qur-AAN\n"
        "- imam: ee-MAAM\n\n"
        "Do not voice Arabic personal names. Refer to figures by their English labels.\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── missing section ──────────────────────────────────────────────────────────

def test_missing_pronunciation_section_exits():
    content = f"# Title\n\n## Other section\n\nSome text.\n\n{GUARD}\n"
    with pytest.raises(SystemExit, match="missing a `## Pronunciation` section"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── R-PRONUNCIATION-DOUBLE: Pronounce X as Y format ─────────────────────────

def test_pronounce_as_format_exits():
    """The old 'Pronounce X as Y' format causes double-read — must be rejected."""
    content = _wrap(
        'Say each term ONCE.\n\n'
        'Pronounce "Tahajjud" as "ta-HAJ-jud".\n'
    )
    with pytest.raises(SystemExit, match="R-PRONUNCIATION-DOUBLE"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


def test_pronounce_as_format_with_fluent_suffix_exits():
    """'Pronounce X as Y. Say it as one fluent word.' is still the buggy format."""
    content = _wrap(
        'Say each term ONCE.\n\n'
        'Pronounce "Quran" as "qur-AAN". Say it as one fluent word.\n'
    )
    with pytest.raises(SystemExit, match="R-PRONUNCIATION-DOUBLE"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


def test_pronounce_as_bullet_format_exits():
    """Bullet prefix doesn't rescue the 'Pronounce X as Y' pattern."""
    content = _wrap(
        'Say each term ONCE.\n\n'
        '- Pronounce "nafs" as "NAFS".\n'
    )
    with pytest.raises(SystemExit, match="R-PRONUNCIATION-DOUBLE"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── R-PRONUNCIATION-IMPERATIVE: anti-doubling instruction required ───────────

def test_missing_anti_doubling_instruction_exits():
    """Bullet list without the anti-doubling instruction must be rejected."""
    content = _wrap(
        "- Tahajjud: ta-HAJ-jud\n"
        "- Ghazali: gha-ZAH-lee\n"
    )
    with pytest.raises(SystemExit, match="anti-doubling instruction"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


def test_never_say_both_phrasing_accepted():
    content = _wrap(
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "- Tahajjud: ta-HAJ-jud\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── legacy passive-list (asterisk-bold) ─────────────────────────────────────

def test_legacy_passive_list_exits():
    content = _wrap(
        "Say each term ONCE. Never say the original and phonetic back-to-back.\n\n"
        "*Tahajjud*: ta-HAJ-jud\n"
    )
    with pytest.raises(SystemExit, match="legacy passive-list"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── R-PRONUNCIATION-TRIVIAL: uppercase-only respellings (P1 flag) ───────────

def test_trivial_uppercase_respelling_is_p1_not_hard_fail(capsys):
    """Trivial uppercase respellings emit a P1 flag but do NOT exit."""
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "- nafs: NAFS\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))
    captured = capsys.readouterr()
    assert "R-PRONUNCIATION-TRIVIAL" in captured.err
    assert "NAFS" in captured.err


def test_genuine_respelling_no_p1_flag(capsys):
    """A respelling that differs from the term should not trigger the trivial flag."""
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "- nafs: naf-SS\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))
    captured = capsys.readouterr()
    assert "R-PRONUNCIATION-TRIVIAL" not in captured.err


# ─── bullet-list format required ─────────────────────────────────────────────

def test_instruction_without_any_bullet_exits():
    """Anti-doubling instruction present but no bullet entries → must be rejected."""
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "Consult the source glossary for all terms.\n"
    )
    with pytest.raises(SystemExit, match="no pronunciation entries"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))


def test_do_not_voice_paragraph_accepted_without_bullets():
    """A 'Do not voice' paragraph substitutes for bullet list (valid for some episodes)."""
    content = _wrap(
        "Say each term ONCE using its phonetic form. "
        "Never say the original spelling and the phonetic form back-to-back.\n\n"
        "Do not voice Arabic personal names. Use the stable English labels.\n"
    )
    assert_framing_pronunciation_imperative(content, Path("test.txt"))


# ─── no-read-aloud guard ──────────────────────────────────────────────────────

def test_missing_no_read_aloud_guard_exits():
    content = (
        "# Title\n\n## Pronunciation\n\n"
        "Say each term ONCE. Never say the original and phonetic back-to-back.\n\n"
        "- Tahajjud: ta-HAJ-jud\n\n"
        "## Next section\n\nSome text.\n"
    )
    with pytest.raises(SystemExit, match="R-NO-READ-PROMPT"):
        assert_framing_pronunciation_imperative(content, Path("test.txt"))
