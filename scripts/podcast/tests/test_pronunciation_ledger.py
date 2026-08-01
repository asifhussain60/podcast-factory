"""Tests for knowledge/pronunciation_ledger.py — the cross-book pronunciation library.

Covers the docstring contract: normalize_key collisions (diacritics / ayn /
case), is_house_style rejection of non-spoken forms (IPA, Arabic script, raw
transliteration diacritics), record() validation (status, house style,
unfixable-requires-gloss), the merge-on-upsert semantics, and the atomic
save() -> load() round-trip. All I/O under tmp_path — never the repo library.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_KNOW = Path(__file__).resolve().parents[1] / "knowledge"
if str(_KNOW) not in sys.path:
    sys.path.insert(0, str(_KNOW))

import pronunciation_ledger as pl


# ---------------------------------------------------------------- normalize_key
def test_normalize_key_diacritics_and_plain_collide():
    assert pl.normalize_key("al-Ghazālī") == pl.normalize_key("al-Ghazali")


def test_normalize_key_folds_ayn_hamza_and_case():
    assert pl.normalize_key("Taʾwīl") == "tawil"
    assert pl.normalize_key("ʿAli") == pl.normalize_key("Ali")


def test_normalize_key_preserves_article_and_hyphens_collapses_whitespace():
    assert pl.normalize_key("  al-Batin   al-Zahir ") == "al-batin al-zahir"


# ---------------------------------------------------------------- is_house_style
@pytest.mark.parametrize(
    "phonetic",
    ["gha-zaa-lee", "bait al-ma'a-MOOR", "is-raa-FEEL", "Cain"],
)
def test_house_style_accepts_spoken_respellings(phonetic):
    assert pl.is_house_style(phonetic)


@pytest.mark.parametrize(
    "phonetic",
    [
        "",  # empty
        "   ",  # whitespace only
        "/al ʔiˈmaːm/",  # IPA with delimiters + stress marks
        "الباطن",  # raw Arabic script
        "gha-zā-lī",  # leftover transliteration macrons
        "123",  # no latin letter at all
    ],
)
def test_house_style_rejects_non_spoken_forms(phonetic):
    assert not pl.is_house_style(phonetic)


# ---------------------------------------------------------------- record()
def _lib(tmp_path: Path) -> pl.PronunciationLibrary:
    return pl.load(tmp_path / "pronunciations.jsonl")


def test_record_and_lookup_by_variant_spelling(tmp_path):
    lib = _lib(tmp_path)
    lib.record("al-Ghazali", "gha-zaa-lee", source_book="kitab-al-riyad")
    hit = lib.lookup("al-Ghazālī")  # diacritic variant resolves
    assert hit is not None
    assert hit.phonetic == "gha-zaa-lee"
    assert hit.source_books == ["kitab-al-riyad"]
    assert "al-Ghazali" in lib
    assert len(lib) == 1


def test_record_merges_books_and_variants_on_upsert(tmp_path):
    lib = _lib(tmp_path)
    lib.record("batin", "BAA-tin", source_book="book-a", mangled_variants=["bay-tin"])
    entry = lib.record("batin", "BAA-tin", source_book="book-b", mangled_variants=["battin"])
    assert entry.source_books == ["book-a", "book-b"]
    assert entry.mangled_variants == ["battin", "bay-tin"]
    assert len(lib) == 1  # upsert, not duplicate


def test_record_rejects_invalid_status(tmp_path):
    with pytest.raises(ValueError, match="status"):
        _lib(tmp_path).record("x", "eks", status="candidate")


def test_record_rejects_non_house_style_confirmed_phonetic(tmp_path):
    with pytest.raises(ValueError, match="house style"):
        _lib(tmp_path).record("imam", "/ʔiˈmaːm/", status="confirmed")


def test_record_unfixable_requires_gloss(tmp_path):
    lib = _lib(tmp_path)
    with pytest.raises(ValueError, match="gloss"):
        lib.record("dhikr", "", status="unfixable")
    entry = lib.record("dhikr", "", status="unfixable", gloss="the remembrance")
    assert entry.status == "unfixable"
    assert entry.gloss == "the remembrance"


# ---------------------------------------------------------------- save / load
def test_save_load_round_trip_sorted_by_key(tmp_path):
    path = tmp_path / "pronunciations.jsonl"
    lib = pl.load(path)
    lib.record("Zahir", "ZAA-hir")
    lib.record("Amr", "AM-r", transliteration="ʿAmr", arabic_script="عمر")
    n = lib.save()
    assert n == 2

    lines = path.read_text(encoding="utf-8").splitlines()
    keys = [json.loads(ln)["key"] for ln in lines]
    assert keys == sorted(keys)  # docstring: rewritten sorted by key

    lib2 = pl.load(path)
    hit = lib2.lookup("amr")
    assert hit is not None
    assert hit.transliteration == "ʿAmr"
    assert hit.arabic_script == "عمر"
    assert lib2.lookup("Zahir").phonetic == "ZAA-hir"


def test_load_missing_file_is_empty_library(tmp_path):
    lib = pl.load(tmp_path / "absent.jsonl")
    assert len(lib) == 0
    assert lib.lookup("anything") is None
    assert lib.all() == []


def test_load_malformed_json_line_raises_with_location(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"term": "ok", "phonetic": "oh-KAY"}\n{not json}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r":2:"):
        pl.load(path)


def test_load_defaults_key_and_ignores_unknown_fields(tmp_path):
    path = tmp_path / "lib.jsonl"
    row = {"term": "Taʾwil", "phonetic": "ta-WEEL", "future_field": True}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    lib = pl.load(path)
    hit = lib.lookup("tawil")  # key derived via normalize_key(term)
    assert hit is not None
    assert hit.key == "tawil"
    assert hit.phonetic == "ta-WEEL"


# ------------------------------------------- ASCII keying (2026-08-01 migration)
def test_a_script_term_is_keyed_by_its_romanisation(tmp_path):
    # normalize_key does not transliterate, so keying on a script `term` made a
    # script key -- and every consumer looks up by the romanised form. 145 of
    # the library's 211 rows were written that way and had never been found.
    lib = pl.load(tmp_path / "l.jsonl")
    e = lib.record("إبليس", "", status="unfixable", gloss="Satan", transliteration="Iblis")
    assert e.key == "iblis"
    assert lib.lookup("Iblis") is e


def test_the_script_lookup_still_works_after_the_key_moves(tmp_path):
    # The probe holds raw script in its `term` field while the framing compiler
    # holds the romanisation; both must find the same row.
    lib = pl.load(tmp_path / "l.jsonl")
    lib.record("إبليس", "", status="unfixable", gloss="Satan", transliteration="Iblis")
    assert lib.lookup("إبليس") is lib.lookup("Iblis")
    assert "إبليس" in lib and "Iblis" in lib


def test_an_ascii_term_keys_exactly_as_before(tmp_path):
    lib = pl.load(tmp_path / "l.jsonl")
    assert lib.record("arkan", "ar-KAAN", transliteration="arkan").key == "arkan"


def test_a_script_term_with_no_romanisation_keeps_its_script_key(tmp_path):
    # Nothing to key from, so nothing is invented.
    lib = pl.load(tmp_path / "l.jsonl")
    assert pl.entry_key("إبليس", "") == pl.normalize_key("إبليس")
    assert lib.record("إبليس", "", status="unfixable", gloss="Satan").key == pl.normalize_key("إبليس")


def test_recording_the_same_term_both_ways_upserts_one_row(tmp_path):
    lib = pl.load(tmp_path / "l.jsonl")
    lib.record("إبليس", "", status="unfixable", gloss="Satan", transliteration="Iblis")
    lib.record("Iblis", "", status="unfixable", gloss="the devil", transliteration="Iblis")
    assert len(lib) == 1
    assert lib.lookup("Iblis").gloss == "the devil"


def test_the_live_library_has_no_unheard_respelling_reachable():
    """The 92 pattern-generated respellings must stay inert.

    They were bulk-written on 2026-06-08, none carries a heard variant, and they
    are syllable splits a generator produced -- `i-blis`, `a-sas`, `Adam ->
    AA-dam`. Promoting them would put 92 unheard respellings into the rung that
    decides what hosts say, at corpus scale.
    """
    import json
    import re

    path = pl.LIBRARY_PATH
    if not path.exists():
        pytest.skip("library not present in this checkout")
    arabic = re.compile(r"[؀-ۿ]")
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        r = json.loads(raw)
        if arabic.search(r["key"]) or r["status"] != "confirmed":
            continue
        assert r.get("mangled_variants") or r["confirmed_date"] != "2026-06-08", (
            f"{r['term']} is a 2026-06-08 bulk row and is now reachable"
        )
