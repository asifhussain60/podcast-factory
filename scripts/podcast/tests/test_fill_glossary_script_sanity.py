"""test_fill_glossary_script_sanity.py — a malformed arabic_script fill must
never reach glossary.yml, regardless of which pass (OCR-grounded or
lexicon-fallback) produced it.

RCA (sharh-al-masail-ghulam-hussain, 2026-08-18): the OCR-grounded pass filled
"dirham" as "در هما" — not a real word, a stray space splitting one Arabic
token into two. Nothing caught it: `harvested_confidence` measures whether the
ENGLISH term was detected with certainty at HARVEST time, not whether the
SCRIPT a later fill pass supplied is well-formed, so the malformed fill carried
the exact same "weak" label as eleven other perfectly good fills and there was
no way to single it out short of a human reading all thirteen by eye.
`_script_is_well_formed` is a cheap, deterministic check applied to every fill
from every pass, before it is ever written — see its docstring in
fill_glossary_arabic.py for the two rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _authoring._core as authoring_core
import fill_glossary_arabic as fg


class TestScriptIsWellFormed:
    def test_the_dirham_regression_is_rejected(self):
        # The exact live defect: a single transliterated word filled as two
        # space-separated Arabic tokens.
        assert fg._script_is_well_formed("dirham", "در هما") is False

    def test_a_correct_single_word_fill_passes(self):
        assert fg._script_is_well_formed("dirham", "دِرْهَم") is True

    def test_a_latin_character_is_rejected(self):
        assert fg._script_is_well_formed("fiqh", "فِقهh") is False

    def test_an_empty_script_is_rejected(self):
        assert fg._script_is_well_formed("fiqh", "") is False
        assert fg._script_is_well_formed("fiqh", "   ") is False

    def test_a_script_with_no_arabic_characters_is_rejected(self):
        assert fg._script_is_well_formed("fiqh", "???") is False

    def test_a_genuinely_multi_word_phonetic_may_fill_to_multiple_tokens(self):
        # "dar al-hikmah" is legitimately several Arabic words — the rule only
        # bounds script tokens BY the phonetic's own word count, never forbids
        # multi-token fills outright.
        assert fg._script_is_well_formed("dar al-hikmah", "دار الحكمة") is True

    def test_a_single_word_phonetic_may_still_carry_the_definite_article_glued_on(self):
        # An Arabic word carrying its definite article (ال) is ONE token, not two.
        assert fg._script_is_well_formed("hikmah", "الحكمة") is True


def _write_glossary(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fg.emit_glossary_yml(entries, {}), encoding="utf-8")


def _fake_claude_call(batches_by_call: list[dict[str, str]]):
    calls = {"n": 0}

    def _run(prompt, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        fills = batches_by_call[i] if i < len(batches_by_call) else {}
        lines = []
        for phon, script in fills.items():
            lines.append(f'  - phonetic: "{phon}"')
            lines.append(f'    arabic_script: "{script}"')
        return 0, "\n".join(lines), ""

    return _run, calls


def test_a_malformed_ocr_grounded_fill_is_never_written_to_the_glossary(tmp_path, monkeypatch):
    book_dir = tmp_path / "some-book"
    glossary_path = book_dir / "_system" / "glossary.yml"
    entries = [
        {"phonetic": "dirham", "transliteration": "dirham", "arabic_script": "", "first_seen_snippet": "a (dirham)"},
        {"phonetic": "fiqh", "transliteration": "fiqh", "arabic_script": "", "first_seen_snippet": "(fiqh)"},
    ]
    _write_glossary(glossary_path, entries)
    ocr_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    ocr_path.parent.mkdir(parents=True, exist_ok=True)
    ocr_path.write_text("dirham and fiqh both appear in the source scan.", encoding="utf-8")

    # OCR-grounded pass returns the live defect shape for "dirham" (malformed —
    # must be rejected) and a well-formed fill for "fiqh" (must pass through).
    # Lexicon-fallback then only ever sees whatever OCR-grounded left empty —
    # "dirham" falls through to it and is refused there too.
    fake_run, calls = _fake_claude_call(
        [
            {"dirham": "در هما", "fiqh": "فِقْه"},  # ocr-grounded
            {},  # lexicon-fallback: refuses (empty reply == no fill)
        ]
    )
    monkeypatch.setattr(authoring_core, "_run_claude_p", fake_run)
    monkeypatch.setattr(sys, "argv", ["fill_glossary_arabic.py", "--book-dir", str(book_dir), "--batch-size", "10"])
    monkeypatch.setattr(fg, "corpus_fill", lambda rows, ocr_text, db_path=None: {})

    rc = fg.main()
    assert rc == 0

    result_entries, _top = fg.parse_glossary_yml(glossary_path)
    by_phon = {e["phonetic"]: e for e in result_entries}

    assert by_phon["fiqh"]["arabic_script"] == "فِقْه"
    assert by_phon["dirham"]["arabic_script"] == ""  # malformed fill discarded, never written
    assert by_phon["dirham"].get("harvested_confidence") != "lexicon"  # never falsely stamped either
