"""test_fill_glossary_lexicon_fallback.py — pins the lexicon-fallback stage of
fill_glossary_arabic.py: it must run automatically, only over what the
OCR-grounded pass left empty, must stamp its fills as `harvested_confidence:
"lexicon"` (never silently indistinguishable from a source-attested fill), and
its prompt must instruct the model to refuse on non-Arabic rows rather than
invent script.

Regression test for the spiritual-ethos 2026-08-08 incident: genuine
Arabic/Islamic vocabulary that a book's own OCR never happens to print in
script used to have no automatic fill path at all — and a naive fallback
(dictionary lookup with no refusal check) risked inventing Arabic for English
words an earlier harvest step mis-tagged as glossed "terms" (e.g. "divine",
"Republic"). See `fill_glossary_arabic.py`'s module docstring and
`build_lexicon_prompt`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _authoring._core as authoring_core
import fill_glossary_arabic as fg


def test_lexicon_prompt_instructs_refusal_on_non_arabic_rows():
    prompt = fg.build_lexicon_prompt(
        [{"phonetic": "divine", "transliteration": "divine", "first_seen_snippet": "the (divine) Sun"}]
    )
    assert "CRITICAL FIRST CHECK" in prompt
    assert "EMPTY STRING" in prompt
    assert "divine" in prompt  # verbatim row echoed for the join


def test_lexicon_prompt_carries_every_row_verbatim():
    rows = [
        {"phonetic": "dhikr", "transliteration": "dhikr", "first_seen_snippet": "the remembrance (dhikr) of God"},
        {"phonetic": "fiqh", "transliteration": "fiqh", "first_seen_snippet": "jurisprudence (fiqh)"},
    ]
    prompt = fg.build_lexicon_prompt(rows)
    assert 'phonetic: "dhikr"' in prompt
    assert 'phonetic: "fiqh"' in prompt


def _write_glossary(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fg.emit_glossary_yml(entries, {}), encoding="utf-8")


def _fake_claude_call(batches_by_call: list[dict[str, str]]):
    """Returns a stand-in for the shared Claude wrapper."""
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


def test_lexicon_fallback_only_covers_what_ocr_left_empty(tmp_path, monkeypatch):
    book_dir = tmp_path / "some-book"
    glossary_path = book_dir / "_system" / "glossary.yml"
    entries = [
        {
            "phonetic": "dhikr",
            "transliteration": "dhikr",
            "arabic_script": "",
            "first_seen_snippet": "remembrance (dhikr)",
        },
        {
            "phonetic": "fiqh",
            "transliteration": "fiqh",
            "arabic_script": "",
            "first_seen_snippet": "jurisprudence (fiqh)",
        },
        {
            "phonetic": "divine",
            "transliteration": "divine",
            "arabic_script": "",
            "first_seen_snippet": "the (divine) Sun",
        },
    ]
    _write_glossary(glossary_path, entries)
    ocr_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    ocr_path.parent.mkdir(parents=True, exist_ok=True)
    ocr_path.write_text("dhikr appears here as ذِكْر in the source scan.", encoding="utf-8")

    # Pass 2 (OCR-grounded) finds "dhikr" in the scan; leaves fiqh + divine empty.
    # Pass 3 (lexicon-fallback) supplies fiqh from standard terminology and
    # correctly REFUSES on "divine" (not a real Arabic term) by omitting it.
    fake_run, calls = _fake_claude_call(
        [
            {"dhikr": "ذِكْر"},  # ocr-grounded batch
            {"fiqh": "فِقْه"},  # lexicon-fallback batch (divine deliberately absent = refusal)
        ]
    )
    monkeypatch.setattr(authoring_core, "_run_claude_p", fake_run)
    monkeypatch.setattr(sys, "argv", ["fill_glossary_arabic.py", "--book-dir", str(book_dir), "--batch-size", "10"])
    # Isolate passes 2/3 from pass 1 (deterministic corpus fill) — these tests
    # are about the OCR-grounded/lexicon-fallback split, not the corpus layer.
    monkeypatch.setattr(fg, "corpus_fill", lambda rows, ocr_text, db_path=None: {})

    rc = fg.main()
    assert rc == 0
    assert calls["n"] == 2  # exactly one OCR-grounded batch + one lexicon-fallback batch

    result_entries, _top = fg.parse_glossary_yml(glossary_path)
    by_phon = {e["phonetic"]: e for e in result_entries}

    assert by_phon["dhikr"]["arabic_script"] == "ذِكْر"
    assert by_phon["dhikr"].get("harvested_confidence") != "lexicon"  # source-attested, not dictionary-derived

    assert by_phon["fiqh"]["arabic_script"] == "فِقْه"
    assert by_phon["fiqh"]["harvested_confidence"] == "lexicon"  # stamped for reviewability

    assert by_phon["divine"]["arabic_script"] == ""  # refused, stays empty — never invented


def test_no_lexicon_pass_runs_when_ocr_grounded_fills_everything(tmp_path, monkeypatch):
    book_dir = tmp_path / "some-book"
    glossary_path = book_dir / "_system" / "glossary.yml"
    entries = [
        {
            "phonetic": "dhikr",
            "transliteration": "dhikr",
            "arabic_script": "",
            "first_seen_snippet": "remembrance (dhikr)",
        },
    ]
    _write_glossary(glossary_path, entries)
    ocr_path = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    ocr_path.parent.mkdir(parents=True, exist_ok=True)
    ocr_path.write_text("dhikr appears here as ذِكْر in the source scan.", encoding="utf-8")

    fake_run, calls = _fake_claude_call([{"dhikr": "ذِكْر"}])
    monkeypatch.setattr(authoring_core, "_run_claude_p", fake_run)
    monkeypatch.setattr(sys, "argv", ["fill_glossary_arabic.py", "--book-dir", str(book_dir), "--batch-size", "10"])
    # Isolate passes 2/3 from pass 1 (deterministic corpus fill) — these tests
    # are about the OCR-grounded/lexicon-fallback split, not the corpus layer.
    monkeypatch.setattr(fg, "corpus_fill", lambda rows, ocr_text, db_path=None: {})

    rc = fg.main()
    assert rc == 0
    assert calls["n"] == 1  # lexicon-fallback never invoked — nothing left for it to do
