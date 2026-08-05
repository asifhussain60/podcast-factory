"""Tests for the pure Quranic Arabic Corpus morphology parser.

Runs against tests/fixtures/morphology-excerpt.txt — a synthetic excerpt in the
exact shape of the real file (documented Fatiha sample rows + rows shaped to
exercise SUFFIX segments, KEY:VALUE features, and attribute reordering).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _morphology_parse import MorphologyParseError, group_words, parse_segments  # noqa: E402

EXCERPT = REPO / "tests" / "fixtures" / "morphology-excerpt.txt"


def _segments() -> list[dict]:
    return list(parse_segments(EXCERPT.read_text(encoding="utf-8").splitlines()))


def test_header_and_blank_lines_are_skipped_and_all_rows_parse() -> None:
    segs = _segments()
    assert len(segs) == 12
    assert all(s["location"]["chapter"] in (1, 2) for s in segs)


def test_location_parses_into_four_ints() -> None:
    first = _segments()[0]
    assert first["location"] == {"chapter": 1, "verse": 1, "word": 1, "segment": 1}


def test_features_are_extracted_by_key_not_position() -> None:
    segs = _segments()
    # (2:45:2:2) deliberately lists ROOT before LEM before POS.
    reordered = next(s for s in segs if s["form"] == "{lS~abori")
    assert reordered["root"] == "Sbr"
    assert reordered["lemma"] == "Sabor"
    assert reordered["pos"] == "N"
    assert reordered["features"] == {"M": True, "GEN": True}


def test_stem_prefix_suffix_types_and_nullable_root_lemma() -> None:
    segs = _segments()
    prefix = segs[0]
    assert prefix["segment_type"] == "PREFIX"
    assert prefix["root"] is None and prefix["lemma"] is None and prefix["pos"] is None
    suffix = next(s for s in segs if s["segment_type"] == "SUFFIX")
    assert suffix["features"] == {"PRON": "2MP"}
    assert suffix["root"] is None


def test_buckwalter_specials_survive_as_data() -> None:
    segs = _segments()
    allah = next(s for s in segs if s["location"]["verse"] == 1 and s["location"]["word"] == 2)
    assert allah["form"] == "{ll~ahi"
    assert allah["lemma"] == "{ll~ah"
    assert allah["root"] == "Alh"


def test_verb_flags_and_keyed_mood() -> None:
    verb = next(s for s in _segments() if s["tag"] == "V")
    assert verb["features"]["(X)"] is True
    assert verb["features"]["IMPV"] is True
    assert verb["features"]["MOOD"] == "JUS"
    assert verb["root"] == "Ewn"


def test_group_words_reassembles_consecutive_segments() -> None:
    words = list(group_words(_segments()))
    assert len(words) == 6
    first_word = words[0]  # bismi = bi + somi
    assert [s["form"] for s in first_word] == ["bi", "somi"]
    keys = [(w[0]["location"]["chapter"], w[0]["location"]["verse"], w[0]["location"]["word"]) for w in words]
    assert keys == [(1, 1, 1), (1, 1, 2), (1, 1, 3), (1, 1, 4), (2, 45, 1), (2, 45, 2)]


def test_malformed_rows_raise_with_line_number() -> None:
    with pytest.raises(MorphologyParseError, match="line 2"):
        list(parse_segments(["header", "(1:1:1:1)\tbi\tP"]))  # 3 cols
    with pytest.raises(MorphologyParseError, match="LOCATION"):
        list(parse_segments(["(1:1:x:1)\tbi\tP\tPREFIX|bi+"]))
    with pytest.raises(MorphologyParseError, match="FEATURES"):
        list(parse_segments(["(1:1:1:1)\tbi\tP\tbi+|PREFIX"]))
