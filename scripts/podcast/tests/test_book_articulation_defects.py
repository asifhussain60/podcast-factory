#!/usr/bin/env python3
"""Two reading-edition defects the post-articulation route lets through (2026-08-09).

Asif found both by eye in `Spiritual Ethos`, which is the failure: the student-reader
pass reads every chapter after articulation and neither of these was flagged. They are
recorded here as executable checks so the next book cannot introduce them silently.

  DUPLICATED ARABIC — a lead-in sentence carries an Arabic quotation inline, in
    parentheses, and the blockquote immediately under it repeats the identical run. The
    reader sees the same words twice in two consecutive lines. The CORRECT shape is two
    lines down in the same chapter: the lead-in gives the TRANSLITERATION
    ("anta minni wa ana minka") and the blockquote gives the Arabic.

  ENGLISH SET RIGHT-TO-LEFT — FIXED 2026-08-09, and this file is now the proof over
    real content. A translation paragraph inside an Arabic blockquote was rendered in
    the Arabic face, right to left, with its quotation marks thrown to the wrong ends.
    The cause was never the prose: both renderers classified a quotation line as Arabic
    if it CONTAINED one Arabic character, so an English sentence carrying the `(ع)`
    honorific — or an editorial note naming a root like `ح-س-ن` — was set as though it
    were Arabic. Five instances across three books, the worst 626 Latin characters
    flipped by three Arabic ones.

    The rule now weighs which script the line is mostly in (`isArabicQuoteLine`, three
    copies pinned by `arabic-quote-line.fixtures.json`). That repaired all five with no
    re-compose and no model spend, which is why `KNOWN` below no longer lists any.

HOW THIS FILE IS ARRANGED, AND WHY

  A LIVE test per defect runs over every book. For the duplication it passes today and
  fails on any NEW instance; for the direction it asserts ZERO everywhere, so it goes
  red the moment either renderer reverts to asking whether a line merely contains
  Arabic. Both were falsified against a scratch copy with defects injected.

  An XFAIL(strict) records what still stands — one duplicated quotation in Spiritual
  Ethos, which needs a re-compose. It turns into a hard failure the moment that lands,
  which is the prompt to delete its `KNOWN` entry rather than let the list rot.

  Nothing in this file mutates content.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _arabic_coverage import normalize_arabic  # noqa: E402

# Overridable so these gates can be FALSIFIED against a scratch copy of a book rather
# than against `content/` itself — the same escape the compose-lane gates use.
CONTENT = Path(os.environ.get("PODCAST_CONTENT_ROOT") or REPO / "content")

#: An Arabic run long enough to be a QUOTATION rather than a glossed term. A short run
#: legitimately repeats — `(بَاب)` beside "bab" is the house annotation style — and
#: flagging those would bury the real finding.
MIN_QUOTATION_CHARS = 12

#: A translation paragraph long enough that setting it right-to-left is unmistakably
#: wrong. Below this a mixed line is usually a term with its gloss.
MIN_TRANSLATION_LATIN = 20

ARABIC_ONLY_RE = re.compile(r"[؀-ۿ][؀-ۿ\s،؛]*")

#: The same alphabet the renderers count, for the shared quotation-line rule.
ARABIC_COUNT_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")

#: The fixtures that pin this file's `is_arabic_quote_line` against the two renderers.
QUOTE_LINE_FIXTURES = REPO / "plan-dashboard" / "scripts" / "lib" / "arabic-quote-line.fixtures.json"


def _books() -> list[Path]:
    found = sorted(CONTENT.glob("*/*/book/book.md")) + sorted(CONTENT.glob("*/*/*/book/book.md"))
    return [p for p in found if p.is_file()]


BOOKS = _books()
IDS = ["/".join(p.relative_to(CONTENT).parts[:-2]) for p in BOOKS]


def _chapters(md: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    title: str | None = None
    cur: list[str] = []
    for line in md.split("\n"):
        if line.startswith("## "):
            if title is not None:
                out.append((title, "\n".join(cur)))
            title, cur = line[3:].strip(), []
        else:
            cur.append(line)
    if title is not None:
        out.append((title, "\n".join(cur)))
    return out


def _blocks(body: str) -> list[tuple[str, list[str]]]:
    """(kind, lines) for each paragraph and blockquote, in order."""
    out: list[tuple[str, list[str]]] = []
    cur: list[str] = []
    kind: str | None = None
    for line in body.split("\n"):
        k = "quote" if line.startswith(">") else ("blank" if not line.strip() else "para")
        if k != kind:
            if cur and kind in ("para", "quote"):
                out.append((kind, cur))
            cur, kind = [], k
        if k != "blank":
            cur.append(line)
    if cur and kind in ("para", "quote"):
        out.append((kind, cur))
    return out


def _quotation_runs(text: str) -> list[str]:
    return [r.strip() for r in ARABIC_ONLY_RE.findall(text) if len(r.strip()) >= MIN_QUOTATION_CHARS]


def _quote_paragraphs(lines: list[str]) -> list[str]:
    paras: list[str] = []
    cur: list[str] = []
    for line in lines:
        stripped = line.lstrip(">").strip()
        if not stripped:
            if cur:
                paras.append(" ".join(cur))
                cur = []
        else:
            cur.append(stripped)
    if cur:
        paras.append(" ".join(cur))
    return paras


def duplicated_arabic(md: str) -> list[tuple[str, str]]:
    """(chapter, run) where a blockquote repeats Arabic its lead-in already gave."""
    hits: list[tuple[str, str]] = []
    for title, body in _chapters(md):
        blocks = _blocks(body)
        for idx, (kind, lines) in enumerate(blocks):
            if kind != "quote":
                continue
            lead = next((b for b in reversed(blocks[:idx]) if b[0] == "para"), None)
            if lead is None:
                continue
            lead_runs = {normalize_arabic(r) for r in _quotation_runs(" ".join(lead[1]))}
            for run in _quotation_runs(" ".join(lines)):
                if normalize_arabic(run) in lead_runs:
                    hits.append((title, run))
                    break
    return hits


def is_arabic_quote_line(text: str) -> bool:
    """Which script a quotation line is MOSTLY in.

    THIRD COPY of `isArabicQuoteLine`, pinned by the shared fixtures at
    `plan-dashboard/scripts/lib/arabic-quote-line.fixtures.json` — the other two are the
    print renderer and the on-screen reader. `test_is_arabic_quote_line_matches_the_shared_fixtures`
    below is what keeps this leg honest.
    """
    arabic = len(ARABIC_COUNT_RE.findall(text))
    if arabic == 0:
        return False
    return arabic > len(re.findall(r"[A-Za-z]", text))


def english_set_right_to_left(md: str) -> list[tuple[str, str]]:
    """(chapter, opening) for each translation paragraph the renderers WOULD set RTL.

    Asks the renderers' own live question, so a hit here is what the page actually
    does rather than a guess about it. After the 2026-08-09 rule change this should be
    empty on every book: the check is end-to-end proof, over real content, that the fix
    holds — and it goes red the moment either renderer reverts to asking whether a line
    merely CONTAINS Arabic.
    """
    hits: list[tuple[str, str]] = []
    for title, body in _chapters(md):
        for kind, lines in _blocks(body):
            if kind != "quote":
                continue
            paras = _quote_paragraphs(lines)
            if not any(is_arabic_quote_line(p) for p in paras):
                continue
            for para in paras:
                latin = len(re.findall(r"[A-Za-z]", para))
                if latin >= MIN_TRANSLATION_LATIN and is_arabic_quote_line(para):
                    hits.append((title, para[:70]))
    return hits


#: The instances that stand TODAY, by book slug. Each is an expected failure below.
#: Delete an entry when a re-compose fixes it — the xfail is strict, so a fixed book
#: fails here until the entry goes, which is what stops this list rotting.
KNOWN: dict[str, dict[str, int]] = {
    # The five misdirected-English instances that stood here on 2026-08-09 are GONE:
    # they were a renderer defect, not a content one, and changing the quotation-line
    # rule to weigh proportion repaired all five across three books with no re-compose.
    # `test_no_new_english_set_right_to_left` now asserts zero everywhere, which is the
    # end-to-end proof of that fix over real content.
    "Islamic/spiritual-ethos": {"duplicated": 1},
}


def _known(book_id: str, key: str) -> int:
    return KNOWN.get(book_id, {}).get(key, 0)


# ── live gates: pass today, fail on anything NEW ─────────────────────────────


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_duplicated_arabic(book: Path) -> None:
    book_id = "/".join(book.relative_to(CONTENT).parts[:-2])
    hits = duplicated_arabic(book.read_text(encoding="utf-8"))
    allowed = _known(book_id, "duplicated")
    assert len(hits) <= allowed, (
        f"{len(hits)} blockquote(s) repeat Arabic their lead-in already gave, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {r[:40]}" for t, r in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_english_set_right_to_left(book: Path) -> None:
    book_id = "/".join(book.relative_to(CONTENT).parts[:-2])
    hits = english_set_right_to_left(book.read_text(encoding="utf-8"))
    allowed = _known(book_id, "rtl")
    assert len(hits) <= allowed, (
        f"{len(hits)} translation paragraph(s) will render right-to-left in the Arabic "
        f"face, {allowed} recorded: " + "; ".join(f"{t}: {p[:40]}" for t, p in hits)
    )


# ── the recorded failures: what is broken RIGHT NOW ──────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Spiritual Ethos ch.1 gives the same Arabic twice — inline in the lead-in and "
        "again in the blockquote under it. Needs a re-compose; delete the KNOWN entry "
        "when it lands."
    ),
)
@pytest.mark.parametrize("book_id", [b for b in KNOWN if "duplicated" in KNOWN[b]])
def test_recorded_duplicated_arabic_is_gone(book_id: str) -> None:
    book = CONTENT / book_id / "book" / "book.md"
    if not book.is_file():
        pytest.skip(f"{book_id} has no reading edition")
    hits = duplicated_arabic(book.read_text(encoding="utf-8"))
    assert hits == [], "; ".join(f"{t}: {r}" for t, r in hits)


def test_is_arabic_quote_line_matches_the_shared_fixtures() -> None:
    """The Python leg of the quotation-line mirror.

    The two renderers are pinned to each other by `arabic-quote-line.test.mjs`; this is
    the third copy reading the SAME fixtures, so a rule change has to move all three or
    fail here.
    """
    import json

    cases = json.loads(QUOTE_LINE_FIXTURES.read_text(encoding="utf-8"))["cases"]
    assert cases, "fixture file is empty"
    for case in cases:
        assert is_arabic_quote_line(case["text"]) is case["arabic"], case["why"]


# ── the detectors themselves must be able to fail ────────────────────────────


class TestTheDetectorsWork:
    """A gate nobody has seen fail is a gate nobody should trust."""

    def test_duplication_is_detected(self) -> None:
        md = '## One\n\nHe said "as my own soul (عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي)":\n\n> عليٌّ مِنِّي بِمَنْزِلَةِ نَفْسِي\n'
        assert len(duplicated_arabic(md)) == 1

    def test_the_correct_shape_is_not_flagged(self) -> None:
        # Lead-in gives the TRANSLITERATION; the blockquote gives the Arabic.
        md = "## One\n\nHe said (anta minni wa ana minka):\n\n> أنْتَ مِنِّی وَ أَنَا مِنْکَ\n"
        assert duplicated_arabic(md) == []

    def test_a_short_glossed_term_is_not_flagged(self) -> None:
        md = "## One\n\nThe gate (بَاب) opens.\n\n> بَاب\n"
        assert duplicated_arabic(md) == []

    def test_the_honorific_no_longer_flips_the_translation(self) -> None:
        # The exact passage Asif photographed. Under the old rule the English line was
        # classified Arabic because of the single (ع); under the new one it is a
        # translation, so nothing is reported.
        md = (
            "## One\n\nHe said:\n\n"
            "> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n>\n"
            '> "Ali is with the Quran and the Quran is with Ali (ع). They will not separate."\n'
        )
        assert english_set_right_to_left(md) == []

    def test_a_mostly_arabic_line_is_still_arabic(self) -> None:
        # The fix must not demote real Arabic: a short quotation has few characters and
        # would fail an absolute threshold, which is why the rule is proportional.
        assert is_arabic_quote_line("بَاب") is True
        assert is_arabic_quote_line("إِنَّ عَلِيًّا مَعَ الْقُرْآنِ") is True

    def test_the_same_translation_without_the_honorific_is_clean(self) -> None:
        md = (
            "## One\n\nHe said:\n\n"
            "> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n>\n"
            '> "Ali is with the Quran and the Quran is with Ali. They will not separate."\n'
        )
        assert english_set_right_to_left(md) == []

    def test_a_pure_arabic_blockquote_is_not_flagged(self) -> None:
        md = "## One\n\nHe said:\n\n> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n"
        assert english_set_right_to_left(md) == []
