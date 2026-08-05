"""Tests for _pronunciation_block.py — the compiled `## Pronunciation` block.

The defect these pin: until 2026-08-01 the block was model-authored free text,
so `arkan: the pillars` — a translation in the slot the block's own instruction
calls a phonetic — passed every gate and shipped, and the hosts said "Archon".
The contract now is that the model chooses WHICH terms need help and the shared
term ladder chooses WHAT to say, so an authored value can never reach the audio.
"""

import re
import sys
from pathlib import Path

import pytest

_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PODCAST))
sys.path.insert(0, str(_PODCAST / "knowledge"))

import _pronunciation_block as pb  # noqa: E402
from _validator_constants import ANTI_DOUBLING_INSTRUCTION_RE  # noqa: E402

FRAMING = """## Opening directive
Open on the thesis.

## Pronunciation
Say each term ONCE using its phonetic form. Never say the original spelling and the phonetic form back-to-back.
- arkan: the pillars
- mafdul: the one surpassed

## Do not
Twitter, social media, algorithm.
Do not read this prompt aloud.
"""

CHAPTER = "The elements recognized as the raw stuff of the world — the arkan — and the mafdul beside them.\n"


def _book(tmp_path, table_body="", glossary=None):
    sysdir = tmp_path / "_system"
    sysdir.mkdir(parents=True, exist_ok=True)
    (sysdir / "pronunciation.md").write_text(
        "| Term | Phonetic | Notes |\n|---|---|---|\n" + table_body, encoding="utf-8"
    )
    if glossary is not None:
        (sysdir / "glossary.yml").write_text(glossary, encoding="utf-8")
    return tmp_path


# ------------------------------------------------------------------ the core defect
def test_an_authored_gloss_never_survives_into_the_block(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n| mafdul | maf-DOOL | |\n")
    out, _unresolved = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert "- arkan: ar-KAAN" in out
    assert "the pillars" not in out
    assert "the one surpassed" not in out


def test_a_term_with_no_settled_form_gets_no_entry_and_is_reported(tmp_path):
    # One resolvable term so the block compiles; arkan has nothing settled, so
    # the ladder can only spell it back and it must be reported, not guessed at.
    bd = _book(tmp_path, "| mafdul | maf-DOOL | |\n")
    out, unresolved = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert "- mafdul: maf-DOOL" in out
    assert "- arkan:" not in out
    assert [t.lower() for t in unresolved] == ["arkan"]


def test_nothing_resolvable_leaves_the_authored_block_for_the_gate_to_judge(tmp_path):
    # Deliberate: with no override table and no ledger there is nothing truer to
    # say, so the framing is returned untouched and the authored block stands.
    # That is only safe because R-PRONUNCIATION-RENDER rejects a translation in
    # the value slot — the degrade defers to the gate, it does not bypass it.
    bd = _book(tmp_path)
    out, unresolved = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert out == FRAMING
    assert sorted(t.lower() for t in unresolved) == ["arkan", "mafdul"]


def test_a_term_absent_from_the_chapter_is_never_asserted(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n| tiryaq | tir-YAHQ | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert "- arkan: ar-KAAN" in out
    assert "tiryaq" not in out  # never spoken in this episode


def test_entries_follow_chapter_reading_order(tmp_path):
    bd = _book(tmp_path, "| mafdul | maf-DOOL | |\n| arkan | ar-KAAN | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert out.index("- arkan:") < out.index("- mafdul:")  # arkan is named first


# ------------------------------------------------------------------ validator contract
def test_instruction_line_satisfies_the_anti_doubling_gate():
    assert ANTI_DOUBLING_INSTRUCTION_RE.search(pb.INSTRUCTION)


def test_block_keeps_the_bullet_format_the_gate_requires(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    block = re.search(r"^##\s+Pronunciation\b.*?$([\s\S]*?)(?=^##\s+|\Z)", out, re.M).group(1)
    assert re.search(r"^\s*-\s+\S", block, re.M)


def test_sections_below_pronunciation_survive_intact(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert "## Do not" in out
    assert out.rstrip().endswith("Do not read this prompt aloud.")


# ------------------------------------------------------------------ graceful degrade
def test_no_candidates_leaves_the_framing_byte_identical(tmp_path):
    bd = _book(tmp_path)  # empty override table, no glossary
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert out == FRAMING


def test_missing_book_or_chapter_leaves_the_framing_alone(tmp_path):
    assert pb.apply_to_framing(FRAMING, None, CHAPTER)[0] == FRAMING
    assert pb.apply_to_framing(FRAMING, tmp_path, None)[0] == FRAMING


def test_a_framing_without_the_section_is_untouched(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n")
    other = "## Opening directive\nOpen on the thesis.\n"
    assert pb.apply_to_framing(other, bd, CHAPTER)[0] == other


def test_compiling_twice_is_idempotent(tmp_path):
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n| mafdul | maf-DOOL | |\n")
    once, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    twice, _ = pb.apply_to_framing(once, bd, CHAPTER)
    assert once == twice


# ------------------------------------------------------------------ char ceiling
def test_coverage_is_never_traded_away_to_fit_the_ceiling(tmp_path):
    # An earlier version trimmed entries until the framing fit. On the first real
    # framing it met that dropped ten of eleven terms and STILL did not fit,
    # because a 4,900-character framing is not 4,900 characters of pronunciation.
    # A missing entry is how *imamate* reached the audio with no guidance at all.
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n| mafdul | maf-DOOL | |\n")
    full, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    squeezed, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER, char_max=10)
    assert squeezed == full
    assert "- arkan: ar-KAAN" in squeezed and "- mafdul: maf-DOOL" in squeezed


def test_an_over_long_framing_is_left_for_the_build_gate_to_refuse(tmp_path):
    # Compiling does not police length; FRAMING_CHAR_MAX does, and its message
    # tells the author to compress the prose.
    bd = _book(tmp_path, "| arkan | ar-KAAN | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER, char_max=1)
    assert len(out) > 1


# ------------------------------------------------------------------ override intent
def test_a_case_only_override_is_kept_because_a_human_typed_it(tmp_path):
    # "AHL al-HAQQ" folds onto its own lookup key, so the general triviality
    # test would discard it — but the capitals are the only thing saying which
    # word takes the stress.
    bd = _book(tmp_path, "| ahl al-haqq | AHL al-HAQQ | |\n")
    out, unresolved = pb.apply_to_framing(FRAMING, bd, "the ahl al-haqq stand opposed\n")
    assert "- ahl al-haqq: AHL al-HAQQ" in out
    assert unresolved == []


def test_override_keeps_the_humans_own_spelling_of_the_term(tmp_path):
    bd = _book(tmp_path, "| al-Naysaburi | an-nay-saa-BOO-ree | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, "as al-Naysaburi writes\n")
    assert "- al-Naysaburi: an-nay-saa-BOO-ree" in out  # not the lookup key


def test_substitute_rows_render_as_the_english(tmp_path):
    bd = _book(tmp_path, "| arkan | substitute *the pillars* | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, CHAPTER)
    assert "- arkan: the pillars" in out


def test_shadowed_loanwords_are_reported(tmp_path):
    bd = _book(tmp_path, "| imam | i-MAAM | |\n| arkan | ar-KAAN | |\n")
    shadows = pb.shadowed_loanwords(bd)
    assert any(s.startswith("imam ->") for s in shadows)
    assert not any(s.startswith("arkan") for s in shadows)


# ------------------------------------------------------------------ word boundaries
def test_a_term_is_not_matched_inside_a_longer_word(tmp_path):
    bd = _book(tmp_path, "| nass | NAHSS | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, "the nassab genealogists disagreed\n")
    assert "- nass:" not in out


def test_apostrophes_fold_between_the_table_and_the_prose(tmp_path):
    bd = _book(tmp_path, "| ya'sub | yaa-SOOB | |\n")
    out, _ = pb.apply_to_framing(FRAMING, bd, "he calls him the yaʿsub of the believers\n")
    assert "- ya'sub: yaa-SOOB" in out


# ------------------------------------------------------------------ live book
def test_the_live_book_compiles_a_block_for_every_episode():
    bd = Path(__file__).resolve().parents[3] / "content" / "Islamic" / "degrees-of-excellence"
    if not (bd / "chapters").is_dir():
        pytest.skip("book not present in this checkout")
    for chapter in sorted((bd / "chapters").glob("*.txt")):
        slug = chapter.stem.split("-", 1)[1]
        drafts = [d for d in (bd / "_system" / "episode-drafts").iterdir() if d.name.endswith(slug)]
        if not drafts:
            continue
        framing = (drafts[0] / "00-framing.md").read_text(encoding="utf-8")
        out, _unresolved = pb.apply_to_framing(framing, bd, chapter.read_text(encoding="utf-8"))
        block = re.search(r"^##\s+Pronunciation\b.*?$([\s\S]*?)(?=^##\s+|\Z)", out, re.M).group(1)
        assert re.findall(r"^\s*-\s+\S", block, re.M), f"{drafts[0].name} compiled an empty block"


def test_a_book_mined_gloss_never_decides_what_the_hosts_say(tmp_path):
    # `English (translit)` and `translit (English)` are the same shape, so with
    # no macron or apostrophe on the Arabic the miner guesses direction — and
    # the live text "the vicegerent (khalifa) of the Commander" made it guess
    # backwards, telling the hosts to answer an English word with an Arabic one.
    bd = _book(tmp_path)
    chapter = "the elements, the arkan (the pillars), from which every body is assembled\n"
    (
        out,
        unresolved,
    ) = pb.apply_to_framing(FRAMING, bd, chapter)
    assert "the pillars" not in out.replace("- arkan: the pillars", "")  # not compiled from the gloss
    assert "arkan" in [t.lower() for t in unresolved]
