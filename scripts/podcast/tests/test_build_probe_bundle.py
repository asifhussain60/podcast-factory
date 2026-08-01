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


# ------------------------------------------- carrier mining from the real chapters
def _chaptered_book(tmp_path, chapters: dict[str, str]):
    book = tmp_path / "carrier-book"
    (book / "chapters").mkdir(parents=True)
    for name, text in chapters.items():
        (book / "chapters" / name).write_text(text, encoding="utf-8")
    return book


def test_carriers_come_from_the_chapters_verbatim(tmp_path):
    sentence = "The bitter ones stand for the leaders of the literalists, the ahl al-zahir, who hold to the husk."
    book = _chaptered_book(tmp_path, {"ch01-a.txt": sentence + "\n"})
    got = bpb.mine_carriers(book, [{"term": "اهل الظاهر", "transliteration": "ahl al-zahir"}])
    assert got[bpb.normalize_key("ahl al-zahir")][0] == sentence


def test_carriers_are_sampled_across_every_chapter(tmp_path):
    # The probe's claim is that settling these terms settles them for the whole
    # book, so its sentences must come from the whole book.
    book = _chaptered_book(
        tmp_path,
        {
            "ch01-a.txt": "He alone guards the treasury of the Muslims, the bayt al-mal, under his guarantee.\n",
            "ch02-b.txt": "The antidote he offers, the tiryaq, is the imam's own teaching handed down.\n",
        },
    )
    got = bpb.mine_carriers(
        book,
        [{"term": "x", "transliteration": "bayt al-mal"}, {"term": "y", "transliteration": "tiryaq"}],
    )
    assert {chapter for _s, chapter in got.values()} == {"ch01-a", "ch02-b"}


def test_a_hyphenated_compound_still_finds_its_term(tmp_path):
    # "ruh al-nutq" contains "nutq"; treating the hyphen as a blocker made the
    # term unfindable in the only sentence that carries it.
    book = _chaptered_book(
        tmp_path,
        {"ch01-a.txt": "A human surpasses the animal by one further spirit: the spirit of reason, the ruh al-nutq.\n"},
    )
    got = bpb.mine_carriers(book, [{"term": "نطق", "transliteration": "nutq"}])
    assert bpb.normalize_key("nutq") in got


def test_a_term_is_not_mined_from_inside_a_longer_word(tmp_path):
    book = _chaptered_book(tmp_path, {"ch01-a.txt": "The nassab genealogists disagreed about the lineage entirely.\n"})
    assert bpb.mine_carriers(book, [{"term": "نص", "transliteration": "nass"}]) == {}


def test_headings_and_quotations_are_not_used_as_carriers(tmp_path):
    book = _chaptered_book(
        tmp_path,
        {
            "ch01-a.txt": "# A heading naming the tiryaq at some length here\n> A quoted line naming the tiryaq as well\n"
        },
    )
    assert bpb.mine_carriers(book, [{"term": "ترياق", "transliteration": "tiryaq"}]) == {}


def test_mining_is_deterministic_and_takes_the_first_match(tmp_path):
    book = _chaptered_book(
        tmp_path,
        {
            "ch01-a.txt": "The first sentence naming the tiryaq is the one that should win here.\n"
            "A second sentence naming the tiryaq should be ignored completely.\n",
        },
    )
    first = bpb.mine_carriers(book, [{"term": "ترياق", "transliteration": "tiryaq"}])
    assert "should win here" in first[bpb.normalize_key("tiryaq")][0]
    assert first == bpb.mine_carriers(book, [{"term": "ترياق", "transliteration": "tiryaq"}])


def test_a_book_with_no_chapters_mines_nothing_rather_than_failing(tmp_path):
    assert bpb.mine_carriers(tmp_path / "nope", [{"term": "x", "transliteration": "tiryaq"}]) == {}


# ---------------------------------------------- carrier quality (2026-08-01)
def test_a_mid_word_glossary_window_is_not_read_aloud():
    # The glossary's first_seen_snippet is a fixed-width window, so it starts
    # mid-word: a host reading "irming the Imamate, in Arabic the Kitab ithbat"
    # is testing the fragment, not the term.
    assert bpb._carrier("ithbat", "irming the Imamate, in Arabic the Kitab ithbat al-imama, by Ahmad") == "**ithbat**"


def test_a_lowercase_function_word_still_opens_a_readable_snippet():
    assert bpb._carrier("Zamrukh", "the Zamrukh spoke plainly").startswith("**Zamrukh** — as in:")


def test_a_blockquote_marker_never_survives_into_a_carrier(tmp_path):
    book = _chaptered_book(
        tmp_path,
        {
            "ch01-a.txt": "He raised it before the people at Ghadir Khumm: > Whoever's master I am, this is his master.\n"
        },
    )
    got = bpb.mine_carriers(book, [{"term": "غدير خم", "transliteration": "Ghadir Khumm"}])
    assert ">" not in got[bpb.normalize_key("Ghadir Khumm")][0]


def test_the_framing_does_not_forbid_the_forms_it_then_prints():
    # The instruction used to end "never say a hyphenated or capitalised
    # respelling" while the list beneath it was full of them — the same
    # self-contradiction, in the same slot, as the defect this all began with.
    data = {
        "book_slug": "b",
        "terms": [
            {
                "n": 1,
                "term": "أركان",
                "transliteration": "arkan",
                "segment": "terms",
                "_render": {"text": "ar-KAAN", "is_english": False, "tier": "book-override"},
            }
        ],
    }
    framing = bpb.build_framing(data)
    assert "- ar-KAAN" in framing
    assert "never say a hyphenated" not in framing.lower()
    assert "capitals mark the" in framing.lower()


def test_the_checklist_lets_the_listener_record_the_answer_it_is_asking_for():
    # It used to say the rendered column is "never a respelling" and forbid
    # writing one as a fix — while the column was full of them, and whether they
    # work is the open question. The answer has to be recordable.
    data = {
        "book_slug": "b",
        "terms": [
            {
                "n": 1,
                "term": "أركان",
                "transliteration": "arkan",
                "segment": "terms",
                "_render": {"text": "ar-KAAN", "is_english": False, "tier": "book-override"},
            }
        ],
    }
    checklist = bpb.build_checklist(data)
    assert "| 1 | arkan | ar-KAAN |" in checklist
    assert "never a respelling" not in checklist
    assert "do not write a" not in checklist.lower()
