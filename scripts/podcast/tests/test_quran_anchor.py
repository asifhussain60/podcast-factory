"""Tests for canonical Quran anchoring in book compose (WS3).

Locks: (1) Quran citations are detected across the common source formats;
(2) the canonical-anchor block is byte-stable across calls (deterministic mirror
lookup, no LLM); (3) the anchor block instructs verbatim reproduction; (4) no
citation -> empty block (compose degrades to prior behavior).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_compose as C  # noqa: E402

# Skip the DB-backed tests cleanly if the mirror isn't present in this checkout.
_MIRROR = (SCRIPT_DIR.parents[1] / "content" / "knowledge-base" / "mirror.db").exists()


@pytest.mark.parametrize("text,expected", [
    ("As it says (Qur'an 2:255), the Throne verse.", [(2, 255)]),
    ("Quran 7:56 and Sura 18:110 and Q 53:39", [(7, 56), (18, 110), (53, 39)]),
    ("see Qur'an 2.255 (dot form)", [(2, 255)]),
    ("no citation here", []),
    ("out of range Quran 999:999 but valid Quran 2:255", [(2, 255)]),
    ("bare ratio 2:255 without a keyword is not a citation", []),
    ("dedupe Quran 2:255 ... again Qur'an 2:255", [(2, 255)]),
    ("bare Q citation Q 2:255", [(2, 255)]),
    # financial-quarter notation must NOT be read as Quran citations (P2 fix)
    ("revenue in Q1.20 and Q3.15 grew", []),
    ("guidance for Q1.2025 is strong", []),
    ("Q2.10 is a quarter not a verse", []),   # bare-Q form requires a colon, not a dot
    ("Q2:10 IS a verse", [(2, 10)]),
    ("the word aQuran2:255 mid-token", []),    # spelled prefix is word-boundary anchored
])
def test_detect_quran_refs(text, expected):
    assert C._detect_quran_refs(text) == expected


def test_no_refs_returns_empty_block():
    block, stats = C._quran_anchor_block("plain prose, no scripture")
    assert block == ""
    assert stats == {"cited": 0, "anchored": 0}


@pytest.mark.skipif(not _MIRROR, reason="mirror.db not present")
def test_anchor_block_is_deterministic():
    src = "He recited (Qur'an 2:255) and also Qur'an 7:56."
    b1, s1 = C._quran_anchor_block(src)
    b2, s2 = C._quran_anchor_block(src)
    assert b1 == b2 and s1 == s2          # byte-identical across calls
    assert s1["cited"] == 2 and s1["anchored"] == 2
    assert "CHARACTER-FOR-CHARACTER" in b1  # verbatim instruction present
    # Each cited verse's canonical Arabic appears in the block.
    assert "Qur'an 2:255" in b1 and "Qur'an 7:56" in b1


@pytest.mark.skipif(not _MIRROR, reason="mirror.db not present")
def test_anchor_carries_canonical_arabic():
    from source_library_mirror import quran_ayat_lookup
    canonical = (quran_ayat_lookup(7, 56) or {}).get("arabic", "").strip()
    block, _ = C._quran_anchor_block("Qur'an 7:56")
    assert canonical and canonical in block


def test_prompt_includes_anchor_when_present():
    prompt = C._compose_prompt("T", "body", {}, "", "",
                               quran_anchor="ANCHOR-SENTINEL-BLOCK")
    assert "ANCHOR-SENTINEL-BLOCK" in prompt
