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

  ENGLISH SET RIGHT-TO-LEFT — a translation paragraph inside an Arabic blockquote is
    rendered in the Arabic face, right-to-left, with the quotation marks thrown to the
    wrong ends of the line. The cause is not the prose: `book-html.renderMd` classifies
    a quote paragraph as Arabic with `ARABIC_RE.test(p)`, which is true if the paragraph
    contains ONE Arabic character. An English sentence carrying the `(ع)` honorific — or
    an editorial note that names a root like `ح-س-ن` — trips it, so several hundred words
    of English are set as though they were Arabic. Verified against the real renderer:
    the same sentence with the honorific removed renders `<p class="tr">`, and with it
    renders `<p class="ar" dir="rtl" lang="ar">`.

HOW THIS FILE IS ARRANGED, AND WHY

  Each defect gets TWO tests:

    * a LIVE test over every book, which passes today and fails the moment a NEW
      instance appears. This is the forward protection, and it is the reason the checks
      are not written as one blanket xfail — a permanently red test protects nothing.
    * an XFAIL(strict) test per KNOWN instance, which is the record Asif asked for. It
      reports as an expected failure while the defect stands, and turns into a hard
      failure the moment the content is fixed — which is the prompt to delete the entry
      from `KNOWN` below.

  The known instances are NOT being fixed here: that needs a re-compose, which is a
  separate decision. Nothing in this file mutates content.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _arabic_coverage import ARABIC_RE, normalize_arabic  # noqa: E402

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


def english_set_right_to_left(md: str) -> list[tuple[str, str]]:
    """(chapter, opening) for each translation paragraph the renderer will set RTL.

    Mirrors `book-html.renderMd`'s own rule — `ARABIC_RE.test(paragraph)` inside a
    blockquote that contains Arabic — so a hit here is what the page actually does, not
    a guess about it.
    """
    hits: list[tuple[str, str]] = []
    for title, body in _chapters(md):
        for kind, lines in _blocks(body):
            if kind != "quote":
                continue
            paras = _quote_paragraphs(lines)
            if not any(ARABIC_RE.search(p) for p in paras):
                continue
            for para in paras:
                latin = len(re.findall(r"[A-Za-z]", para))
                arabic = len(re.findall(r"[؀-ۿ]", para))
                if latin >= MIN_TRANSLATION_LATIN and arabic > 0 and latin > 2 * arabic:
                    hits.append((title, para[:70]))
    return hits


#: The instances that stand TODAY, by book slug. Each is an expected failure below.
#: Delete an entry when a re-compose fixes it — the xfail is strict, so a fixed book
#: fails here until the entry goes, which is what stops this list rotting.
KNOWN: dict[str, dict[str, int]] = {
    "Islamic/spiritual-ethos": {"duplicated": 1, "rtl": 3},
    "Islamic/degrees-of-excellence": {"rtl": 1},
    "Islamic/the-master-and-the-disciple": {"rtl": 1},
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Translation paragraphs carrying the (ع) honorific — or an editorial note naming "
        "an Arabic root — are set right-to-left in the Arabic face by renderMd's "
        "one-Arabic-character rule. Delete the KNOWN entry when the book is recomposed "
        "or the classifier is changed to weigh proportion."
    ),
)
@pytest.mark.parametrize("book_id", [b for b in KNOWN if "rtl" in KNOWN[b]])
def test_recorded_english_is_no_longer_right_to_left(book_id: str) -> None:
    book = CONTENT / book_id / "book" / "book.md"
    if not book.is_file():
        pytest.skip(f"{book_id} has no reading edition")
    hits = english_set_right_to_left(book.read_text(encoding="utf-8"))
    assert hits == [], "; ".join(f"{t}: {p}" for t, p in hits)


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

    def test_the_honorific_trips_the_rtl_detector(self) -> None:
        md = (
            "## One\n\nHe said:\n\n"
            "> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n>\n"
            '> "Ali is with the Quran and the Quran is with Ali (ع). They will not separate."\n'
        )
        assert len(english_set_right_to_left(md)) == 1

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
