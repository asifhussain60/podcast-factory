"""Tests for probe/score_pronunciation_risk.py — the 0probe risk ranker.

Covers the pure logic: the phonetics-table parser, transliteration
normalisation, the risk-score heuristic (its job is ordering, so tests assert
relative order + reason tags, not magic numbers), snippet-gloss extraction
guards, al-article dedup merging, and the build_probe_terms contract
(ledger-settled terms are DROPPED, frequency-first ordering, top-N cap).
All book state under tmp_path; the cross-book ledger is patched to a
tmp-backed (empty or seeded) library so the repo's real library never leaks in.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from probe import score_pronunciation_risk as spr

PHONETICS_MD = """\
| Term | Transliteration | Phonetic | First occurrence |
|------|-----------------|----------|------------------|
| باطن | batin | BAA-tin | the batin (inner meaning) of the verse |
| تأويل | taʾwil | ta-WEEL | the taʾwil of scripture |
| Ibn Sina | Ibn Sina | ib-un SEE-nah | Ibn Sina the philosopher |
"""

REFINED_MD = """\
<!-- page 1 -->
Front matter mentioning batin batin batin (should be sliced off).
<!-- page 3 -->
The batin is discussed here, and the batin again: batin. The taʾwil appears once.
"""


def _book(tmp_path: Path, phonetics: str = PHONETICS_MD, refined: str = REFINED_MD) -> Path:
    book = tmp_path / "test-book"
    text_dir = book / "_system" / "source" / "text"
    text_dir.mkdir(parents=True)
    (text_dir / "_phonetics.md").write_text(phonetics, encoding="utf-8")
    (text_dir / "refined-english.md").write_text(refined, encoding="utf-8")
    return book


def _patch_ledger(monkeypatch, tmp_path: Path, seed=None):
    """Point ledger.load at a tmp-backed library (empty unless seeded)."""
    lib = spr.ledger.load(tmp_path / "ledger.jsonl")
    for term, kw in seed or []:
        lib.record(term, **kw)
    monkeypatch.setattr(spr.ledger, "load", lambda path=None: lib)
    return lib


# ---------------------------------------------------------------- parsing + normalising
def test_parse_phonetics_md_skips_header_and_divider(tmp_path):
    path = tmp_path / "_phonetics.md"
    path.write_text(PHONETICS_MD, encoding="utf-8")
    rows = spr._parse_phonetics_md(path)
    assert [r["term"] for r in rows] == ["باطن", "تأويل", "Ibn Sina"]
    assert rows[0]["transliteration"] == "batin"
    assert rows[0]["phonetic"] == "BAA-tin"
    assert "inner meaning" in rows[0]["snippet"]


def test_normalise_translit_folds_diacritics_and_ayn():
    assert spr._normalise_translit("Taʾwīl") == "tawil"
    assert spr._normalise_translit("al-Ghazālī") == "al-ghazali"


# ---------------------------------------------------------------- risk scoring
def test_score_row_tags_phoneme_hazards_and_frequency():
    row = {"term": "Qaʿim", "transliteration": "Qaʿim", "phonetic": "kaa-EEM", "snippet": ""}
    score, reasons = spr.score_row(row, freq=10)
    assert "ayn/hamza" in reasons
    assert "qaf" in reasons
    assert "x10 in text" in reasons
    easy_score, easy_reasons = spr.score_row(
        {"term": "safar", "transliteration": "safar", "phonetic": "sa-far", "snippet": ""}, freq=0
    )
    assert score > easy_score  # ordering is the contract, not the exact number
    assert easy_reasons == []


def test_score_row_flags_proper_names_and_syllable_load():
    row = {"term": "Ibn Sina", "transliteration": "Ibn Sina", "phonetic": "ib-un-see-nah", "snippet": ""}
    _, reasons = spr.score_row(row, freq=0)
    assert "proper name" in reasons
    assert "4 syllables" in reasons


# ---------------------------------------------------------------- snippet gloss guards
def test_snippet_meaning_requires_parenthetical_right_after_term():
    assert spr._extract_snippet_meaning("the batin (inner meaning) of the verse", "batin") == "inner meaning"
    # The docstring's own false-positive example: umma must NOT inherit wasi's gloss.
    assert spr._extract_snippet_meaning("wasi (executor) appointed for the umma", "umma") == ""
    assert spr._extract_snippet_meaning("wasi (executor) appointed for the umma", "wasi") == "executor"


def test_snippet_meaning_rejects_honorifics_and_self_reference():
    assert spr._extract_snippet_meaning("Ali (peace be upon him) said", "Ali") == ""
    assert spr._extract_snippet_meaning("batin (batin) again", "batin") == ""


# ---------------------------------------------------------------- article dedup
def test_dedup_merges_al_variant_into_bare_form():
    scored = [
        {"term": "batin", "transliteration": "batin", "freq": 4, "score": 5, "reasons": ["x4 in text"], "meaning": ""},
        {
            "term": "al-batin",
            "transliteration": "al-batin",
            "freq": 2,
            "score": 4,
            "reasons": ["x2 in text"],
            "meaning": "the inner",
        },
    ]
    out = spr._dedup_article_variants(scored)
    assert len(out) == 1
    merged = out[0]
    assert merged["term"] == "batin"  # bare form is canonical
    assert merged["freq"] == 6
    assert any(r.startswith("x6 in text") and "al-batin" in r for r in merged["reasons"])
    assert merged["meaning"] == "the inner"  # falls back to whichever member has one


def test_dedup_never_strips_allah_or_ali():
    scored = [
        {"term": "Allah", "transliteration": "Allah", "freq": 9, "score": 3, "reasons": [], "meaning": ""},
        {"term": "Ali", "transliteration": "Ali", "freq": 5, "score": 2, "reasons": [], "meaning": ""},
    ]
    out = spr._dedup_article_variants(scored)
    assert len(out) == 2  # only the hyphenated "al-" article merges


# ---------------------------------------------------------------- body slicing
def test_body_start_page_and_slice(tmp_path):
    book = _book(tmp_path)
    cr = book / "_system" / "source" / "text" / "content-range.md"
    cr.write_text("body_starts_at_page: 3\n", encoding="utf-8")
    assert spr._body_start_page(book) == 3
    sliced = spr._slice_to_body(REFINED_MD, 3)
    assert "Front matter" not in sliced
    assert sliced.startswith("<!-- page 3 -->")
    # Unknown marker: full text returned unchanged.
    assert spr._slice_to_body(REFINED_MD, 99) == REFINED_MD


# ---------------------------------------------------------------- build_probe_terms
def test_build_probe_terms_orders_by_frequency_and_numbers(tmp_path, monkeypatch):
    _patch_ledger(monkeypatch, tmp_path)
    result = spr.build_probe_terms(_book(tmp_path))
    assert result["total_terms"] == 3
    assert result["skipped_confirmed"] == 0
    terms = result["terms"]
    assert [t["n"] for t in terms] == list(range(1, len(terms) + 1))
    # No content-range.md here, so the whole text counts: batin = 6 occurrences.
    freqs = [t["freq"] for t in terms]
    assert freqs == sorted(freqs, reverse=True)  # frequency-first ordering
    batin = next(t for t in terms if t["transliteration"] == "batin")
    assert batin["meaning"] == "inner meaning"  # mined from the snippet parenthetical
    assert batin["segment"] == "terms"
    ibn_sina = next(t for t in terms if t["transliteration"] == "Ibn Sina")
    assert ibn_sina["segment"] == "names"


def test_build_probe_terms_drops_ledger_settled_terms(tmp_path, monkeypatch):
    _patch_ledger(
        monkeypatch,
        tmp_path,
        seed=[
            ("باطن", {"phonetic": "BAA-tin", "status": "confirmed"}),
            ("تأويل", {"phonetic": "", "status": "unfixable", "gloss": "the inner interpretation"}),
        ],
    )
    result = spr.build_probe_terms(_book(tmp_path))
    assert result["skipped_confirmed"] == 1
    assert result["skipped_unfixable"] == 1
    assert [t["transliteration"] for t in result["terms"]] == ["Ibn Sina"]


def test_build_probe_terms_respects_top_n_and_body_slice(tmp_path, monkeypatch):
    _patch_ledger(monkeypatch, tmp_path)
    book = _book(tmp_path)
    (book / "_system" / "source" / "text" / "content-range.md").write_text("body_starts_at_page: 3\n", encoding="utf-8")
    result = spr.build_probe_terms(book, top_n=1)
    assert result["top_n"] == 1
    assert len(result["terms"]) == 1
    # With front matter sliced off, batin counts only its 3 body occurrences.
    assert result["terms"][0]["transliteration"] == "batin"
    assert result["terms"][0]["freq"] == 3


def test_build_probe_terms_missing_phonetics_raises(tmp_path, monkeypatch):
    _patch_ledger(monkeypatch, tmp_path)
    book = tmp_path / "empty-book"
    book.mkdir()
    with pytest.raises(FileNotFoundError, match="phase 0c"):
        spr.build_probe_terms(book)
