"""test_para_blocks.py — the Python half of the prose-block mirror pair.

Runs the SHARED fixtures at plan-dashboard/scripts/lib/para-blocks.fixtures.json,
which plan-dashboard/scripts/lib/para-blocks.test.mjs runs too. The stake: this
side writes `_system/arabic-alignment.json` keyed by these fingerprints and the
Composer looks paragraphs up by them, so the two halves disagreeing does not show
LESS Arabic — it shows the WRONG Arabic above a paragraph, confidently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _para_blocks import (  # noqa: E402
    blocks_fingerprint,
    fingerprints,
    para_fingerprint,
    prose_blocks,
)

FIXTURES = Path(__file__).resolve().parents[3] / "plan-dashboard" / "scripts" / "lib" / "para-blocks.fixtures.json"


@pytest.fixture(scope="module")
def fx() -> dict:
    assert FIXTURES.exists(), f"shared fixtures missing: {FIXTURES}"
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_prose_blocks_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["proseBlocks"]:
        assert prose_blocks(case["in"]) == case["out"], case.get("_why", case["in"])


def test_para_fingerprint_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["paraFingerprint"]:
        same = para_fingerprint(case["a"]) == para_fingerprint(case["b"])
        assert same is case["equal"], case.get("_why", case["a"])


def test_blocks_fingerprint_matches_shared_fixtures(fx: dict) -> None:
    for case in fx["blocksFingerprint"]:
        same = blocks_fingerprint(case["a"]) == blocks_fingerprint(case["b"])
        assert same is case["equal"], case.get("_why", case["a"])


# ── This half's own coverage ───────────────────────────────────────────────


def test_a_fingerprint_is_a_short_stable_hex_name() -> None:
    fp = para_fingerprint("The Master replied.")
    assert len(fp) == 16 and all(c in "0123456789abcdef" for c in fp)
    assert fp == para_fingerprint("The Master replied.")


def test_fingerprints_line_up_with_prose_blocks() -> None:
    body = "One.\n\n> quoted\n\nTwo.\n\n## head\n\nThree."
    assert len(fingerprints(body)) == len(prose_blocks(body)) == 3


def test_the_real_book_splits_into_only_paragraphs() -> None:
    """On the real edition every prose block renders as exactly one <p>.

    Measured: 696 blocks across 8 chapters with zero lists, tables, code fences or
    images. That is what makes the ordinal mapping from block N to the Nth `<p>`
    sound. This test is the tripwire for a future book where it is not — the
    Composer asserts the same equality at runtime and disables the reveal, but
    catching it here says WHICH book and WHICH block.
    """
    import re

    book = Path(__file__).resolve().parents[3] / "content/Islamic/the-master-and-the-disciple/book/book.md"
    if not book.exists():  # pragma: no cover - content may be absent in a bare checkout
        pytest.skip("book not present")
    odd = []
    for chunk in re.split(r"(?m)^##\s+", book.read_text(encoding="utf-8"))[1:]:
        # The split consumes the `## ` marker, so the chunk OPENS with the heading
        # text ("3. The Boy at the Door…") — which would read as a numbered-list
        # item. Drop that first line; the body is what renders as paragraphs.
        body = chunk.split("\n", 1)[1] if "\n" in chunk else ""
        for b in prose_blocks(body):
            if re.match(r"^\s*([-*+]\s|\d+\.\s|\||```|!\[)", b):
                odd.append(b[:40])
    assert not odd, f"blocks that will not render as a single <p>: {odd[:3]}"
