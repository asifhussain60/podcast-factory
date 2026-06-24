"""test_arabic_recitation_path.py — the ElevenLabs Arabic-injection chain.

Regression guard for the 2026-06-13 fix. Two root causes had left the
ElevenLabs path emitting ZERO Arabic (and the reader showing none):

  1. build_glossary anchored the glossary `phonetic` field on the Arabic `term`
     column. The phonetic field is the match key for the render-time Arabic
     injection, the reader overlay, and the PLS dictionary — all of which match
     ROMANIZED text. An Arabic anchor never fires.
  2. The Arabic-recitation gate keyed only off a flag, not the engine.

These tests pin both fixes: the glossary anchor is romanized, Arabic is available
to persisted chapters, Arabic is recited for TEACHING terms on the ElevenLabs
path, incidental terms are NOT recited, and the NotebookLM dialogue-render route
stays phonetic even with the flag set.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def _mk_book(tmp_path, *, engine, recitation):
    bd = tmp_path / "bk"
    sysd = bd / "_system"
    sysd.mkdir(parents=True)
    (sysd / "series-config.yaml").write_text(
        f"audio_engine: {engine}\n"
        f"elevenlabs_arabic_recitation: {str(recitation).lower()}\n",
        encoding="utf-8")
    (sysd / "glossary.yml").write_text(
        "schema_version: 2\n"
        "entries:\n"
        "  - phonetic: \"ta'wil\"\n"
        "    transliteration: \"ta'wil\"\n"
        "    arabic_script: \"تأويل\"\n"
        "    audio_phonetic: \"taa-weel\"\n"
        "    first_seen_snippet: \"x\"\n"
        "    teaching_relevance: \"teaching\"\n"
        "  - phonetic: \"Fatimid\"\n"
        "    transliteration: \"Fatimid\"\n"
        "    arabic_script: \"فاطمي\"\n"
        "    audio_phonetic: \"fa-ti-mid\"\n"
        "    first_seen_snippet: \"x\"\n"
        "    teaching_relevance: \"incidental\"\n",
        encoding="utf-8")
    return bd


def _turns(text):
    from _dialogue_script import Turn
    return [Turn(speaker="A", text=text)]


def test_elevenlabs_injects_arabic_for_teaching_term(tmp_path):
    from pronunciation_compiler import compile_turns_for_render
    bd = _mk_book(tmp_path, engine="elevenlabs", recitation=True)
    out = compile_turns_for_render(bd, _turns("The method turns on ta'wil here."))
    assert "تأويل" in out[0].text   # تأويل recited
    assert "ta'wil" not in out[0].text                       # romanized replaced


def test_incidental_term_not_recited(tmp_path):
    from pronunciation_compiler import compile_turns_for_render
    bd = _mk_book(tmp_path, engine="elevenlabs", recitation=True)
    out = compile_turns_for_render(bd, _turns("Under the Fatimid judges."))
    assert "فاطمي" not in out[0].text  # فاطمي NOT recited
    assert "Fatimid" in out[0].text                            # stays English


def test_notebooklm_stays_phonetic_even_with_flag(tmp_path):
    # Dialogue render stays engine-aware; persisted Islamic chapters carry Arabic
    # separately through inject_chapter_arabic.py.
    from pronunciation_compiler import compile_turns_for_render
    bd = _mk_book(tmp_path, engine="notebooklm", recitation=True)
    out = compile_turns_for_render(bd, _turns("The method turns on ta'wil here."))
    assert "تأويل" not in out[0].text  # NO Arabic
    assert "ta'wil" in out[0].text                              # phonetic kept


def test_glossary_phonetic_anchor_is_romanized():
    # build_glossary must map the ROMANIZED transliteration into `phonetic`,
    # never the Arabic `term` column, and seed arabic_script from an Arabic term.
    import build_glossary
    rows = [{"term": "تأويل", "transliteration": "ta'wil",
             "phonetic": "taa-weel", "first_seen_snippet": "x"}]
    out = build_glossary.emit_glossary_yaml(rows)
    assert "phonetic: \"ta'wil\"" in out                       # romanized anchor
    assert "arabic_script: \"تأويل\"" in out  # arabic seeded
    assert "phonetic: \"تأويل\"" not in out   # NOT the arabic term


def test_glossary_fallback_scans_chapters_when_phonetics_missing(tmp_path):
    import build_glossary
    bd = tmp_path / "bk"
    chapters = bd / "chapters"
    chapters.mkdir(parents=True)
    (chapters / "ch01.txt").write_text(
        "The path of tawhid and tanzih leads through alam al-ruh.",
        encoding="utf-8",
    )

    rows = build_glossary.rows_from_chapter_fallback(bd)
    out = build_glossary.emit_glossary_yaml(rows)

    assert "phonetic: \"tawhid\"" in out
    assert "arabic_script: \"توحيد\"" in out
    assert "phonetic: \"alam al-ruh\"" in out
    assert "arabic_script: \"عالم الروح\"" in out


def test_inject_chapter_arabic_persists_script_from_glossary(tmp_path):
    from inject_chapter_arabic import chapter_arabic_status, inject_book
    bd = _mk_book(tmp_path, engine="notebooklm", recitation=False)
    chapters = bd / "chapters"
    chapters.mkdir()
    chapter = chapters / "ch01.txt"
    chapter.write_text("The method turns on ta'wil here.", encoding="utf-8")

    result = inject_book(bd)

    text = chapter.read_text(encoding="utf-8")
    assert result["injections"] == 1
    assert "ta'wil (تأويل)" in text
    assert chapter_arabic_status(bd)["ok"] is True


def test_inject_chapter_arabic_is_idempotent(tmp_path):
    from inject_chapter_arabic import inject_book
    bd = _mk_book(tmp_path, engine="notebooklm", recitation=False)
    chapters = bd / "chapters"
    chapters.mkdir()
    chapter = chapters / "ch01.txt"
    chapter.write_text("The method turns on ta'wil (تأويل) here.", encoding="utf-8")

    result = inject_book(bd)

    assert result["injections"] == 0
    assert chapter.read_text(encoding="utf-8").count("تأويل") == 1
