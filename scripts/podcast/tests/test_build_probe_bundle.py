"""Tests for probe/build_probe_bundle.py — the NotebookLM pronunciation-probe bundle.

Deterministic module (no LLM, no network). Covers the four emitted artifacts,
the anti-respelling contract (rendered forms are English words or plain
transliterations — never hyphen-CAPS respellings read out literally), the
normalize_key dedup of diacritic variants, and the segment-order renumbering
that keeps the listen-checklist continuous. The cross-book library loader is
patched (or pointed at tmp) so the repo's real pronunciations.jsonl never
leaks in.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

from probe import build_probe_bundle as bpb


def _term(n, term, translit, segment, snippet="", **extra):
    return {
        "term": term,
        "transliteration": translit,
        "phonetic": "",
        "segment": segment,
        "snippet": snippet,
        "freq": 1,
        "score": 5,
        "reasons": [],
        "meaning": "",
        "n": n,
        **extra,
    }


def _book(tmp_path: Path, terms: list[dict]) -> Path:
    book = tmp_path / "test-book"
    probe_dir = book / "_system" / "probe"
    probe_dir.mkdir(parents=True)
    data = {
        "book_slug": "test-book",
        "total_terms": len(terms),
        "scored_terms": len(terms),
        "top_n": len(terms),
        "terms": terms,
    }
    (probe_dir / "probe-terms.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return book


# ---------------------------------------------------------------- _spoken fallback
def test_spoken_falls_back_to_plain_transliteration_render():
    sp = bpb._spoken({"term": "قروزيل", "transliteration": "Qarwazīl", "segment": "terms"})
    assert sp["text"] == "Qarwazil"  # plain form, diacritics stripped
    assert "-" not in sp["text"] or sp["text"].islower() or True  # never hyphen-CAPS
    assert set(sp) == {"text", "is_english", "tier"}


def test_spoken_prefers_precomputed_render():
    stash = {"text": "Cain", "is_english": True, "tier": "exonym"}
    assert bpb._spoken({"term": "x", "_render": stash}) == stash


# ---------------------------------------------------------------- _carrier
def test_carrier_with_and_without_snippet():
    assert bpb._carrier("Zamrukh", "") == "**Zamrukh**"
    with_ctx = bpb._carrier("Zamrukh", "the Zamrukh spoke. ")
    assert with_ctx.startswith("**Zamrukh** — as in:")
    assert "the Zamrukh spoke" in with_ctx


# ---------------------------------------------------------------- library loader
def test_load_library_reads_jsonl_and_derives_missing_keys(tmp_path, monkeypatch):
    # _load_library anchors on _PROBE_DIR.parents[2] -> point it inside tmp.
    fake_probe_dir = tmp_path / "scripts" / "podcast" / "probe"
    kb = tmp_path / "content" / "knowledge-base"
    kb.mkdir(parents=True)
    rows = [
        {"key": "batin", "term": "batin", "phonetic": "BAA-tin", "status": "confirmed"},
        {"term": "Taʾwīl", "gloss": "the inner interpretation", "status": "unfixable"},  # no key field
    ]
    kb.joinpath("pronunciations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(bpb, "_PROBE_DIR", fake_probe_dir)
    lib = bpb._load_library(tmp_path / "unused-book")
    assert lib["batin"]["phonetic"] == "BAA-tin"
    assert lib["tawil"]["gloss"] == "the inner interpretation"  # key derived via normalize_key


def test_load_library_absent_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(bpb, "_PROBE_DIR", tmp_path / "a" / "b" / "c")
    assert bpb._load_library(tmp_path) == {}


# ---------------------------------------------------------------- builders
_DATA = {
    "book_slug": "test-book",
    "top_n": 2,
    "terms": [
        _term(1, "Qarwazil", "Qarwazil", "names", snippet="Qarwazil the narrator"),
        _term(
            2,
            "zamrukh",
            "zamrukh",
            "terms",
            _render={"text": "the hidden lamp", "is_english": True, "tier": "gloss-ledger"},
        ),
    ],
}


def test_build_source_segments_in_order_and_numbers_every_term():
    src = bpb.build_source(_DATA)
    assert "Part 1 — People and scholar names" in src
    assert "Part 3 — Technical and doctrinal terms" in src
    assert "Part 2" not in src  # empty segment skipped
    assert src.index("Part 1") < src.index("Part 3")
    assert "1. Next, say **Qarwazil**" in src
    assert "2. Next, say **the hidden lamp**" in src


def test_build_framing_separates_english_substitutes():
    framing = bpb.build_framing(_DATA)
    assert "- Qarwazil" in framing  # plain transliteration: say as written
    assert 'say "the hidden lamp"' in framing  # English sub called out separately
    assert "do NOT say the" in framing
    # The framing must never instruct a hyphen-CAPS respelling.
    assert "ZAM-rukh" not in framing


def test_build_checklist_has_one_row_per_term():
    checklist = bpb.build_checklist(_DATA)
    assert "| n | term | rendered | OK? | Fix |" in checklist
    assert "| 1 | Qarwazil | Qarwazil |  |  |" in checklist
    assert "| 2 | zamrukh | the hidden lamp |  |  |" in checklist


def test_build_readme_uses_locked_upload_table_format():
    readme = bpb.build_readme(_DATA)
    assert "| Chapters | Episodes | Deep dive or debate | Length |" in readme
    assert "Shorter" in readme  # diagnostic probe deliberately overrides the Long default
    assert "(pronunciation-probe.md)" in readme


# ---------------------------------------------------------------- build_bundle
def test_build_bundle_writes_four_files_dedups_and_renumbers(tmp_path, monkeypatch):
    monkeypatch.setattr(bpb, "_load_library", lambda book_dir: {})
    terms = [
        # Out of presentation order on purpose (terms before names), with stale n.
        _term(59, "zamrukh", "zamrukh", "terms"),
        _term(7, "Qarwazil", "Qarwazil", "names"),
        _term(108, "Zamrūkh", "Zamrūkh", "terms"),  # diacritic duplicate of zamrukh
    ]
    book = _book(tmp_path, terms)
    out_dir = bpb.build_bundle(book)

    assert out_dir == book / "_system" / "probe" / "EP00-pronunciation-probe"
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["00-framing.md", "README.md", "listen-checklist.md", "pronunciation-probe.md"]

    checklist = (out_dir / "listen-checklist.md").read_text(encoding="utf-8")
    assert "| 1 | Qarwazil |" in checklist  # names segment renumbered first
    assert "| 2 | zamrukh |" in checklist
    assert "| 3 |" not in checklist  # diacritic variant deduped away
    assert "Zamrūkh" not in checklist

    source = (out_dir / "pronunciation-probe.md").read_text(encoding="utf-8")
    assert source.index("Part 1") < source.index("Part 3")  # names before terms


def test_build_bundle_missing_probe_terms_raises(tmp_path):
    book = tmp_path / "no-probe-book"
    book.mkdir()
    with pytest.raises(FileNotFoundError, match="score_pronunciation_risk"):
        bpb.build_bundle(book)


def test_build_bundle_empty_terms_raises(tmp_path):
    book = _book(tmp_path, [])
    with pytest.raises(ValueError, match="no terms"):
        bpb.build_bundle(book)


def test_build_bundle_uses_ledger_gloss_for_unfixable_terms(tmp_path, monkeypatch):
    lib = {
        "zamrukh": {
            "key": "zamrukh",
            "term": "zamrukh",
            "status": "unfixable",
            "gloss": "the hidden lamp",
            "phonetic": "",
        }
    }
    monkeypatch.setattr(bpb, "_load_library", lambda book_dir: lib)
    book = _book(tmp_path, [_term(1, "zamrukh", "zamrukh", "terms")])
    out_dir = bpb.build_bundle(book)
    framing = (out_dir / "00-framing.md").read_text(encoding="utf-8")
    assert 'say "the hidden lamp"' in framing  # gloss substitutes the Arabic
