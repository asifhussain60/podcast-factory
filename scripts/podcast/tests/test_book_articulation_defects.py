#!/usr/bin/env python3
"""Four reading-edition defects the post-articulation route lets through (2026-08-09).

Asif found every one of them BY EYE in a shipped edition, which is the failure each
records: the student-reader pass reads each chapter after articulation and flagged none
of them. They are executable here so the next book cannot introduce them silently.

  DUPLICATED ARABIC       a lead-in gives an Arabic quotation inline and the blockquote
                          under it repeats the identical run — the same words twice in
                          two consecutive lines.

  ENGLISH SET RIGHT-TO-LEFT
                          FIXED at the renderer 2026-08-09, and this file is now the
                          proof over real content. Both renderers used to classify a
                          quotation line as Arabic if it CONTAINED one Arabic character,
                          so an English sentence carrying `(ع)` — or an editorial note
                          naming a root like `ح-س-ن` — was set in the Arabic face with
                          its quotation marks thrown to the wrong ends. Five instances
                          across three books, the worst 626 Latin characters flipped by
                          three Arabic ones. The rule now weighs which script the line
                          is MOSTLY in, which repaired all five with no re-compose.

  ROMANIZED ARABIC        a whole Arabic sentence printed in the English character set.
                          Asif's rule of 2026-08-02 — quoted verbatim in
                          `_book_inline_arabic` — is that book.md carries zero English
                          transliteration of Arabic "terms, words, paragraphs,
                          sentences, etc.". `_book_substitution` implements it for
                          glossary TERMS only, gated on a term being classed `teach`, so
                          a whole SENTENCE matches nothing and 14 of them run in two
                          shipped editions.

  HONORIFIC OVERUSE       `(ع)` after every occurrence of every name — 54 in one chapter
                          of Spiritual Ethos, 78 unattributed in one chapter of
                          Mukhtasar 2. Capped at once per figure per chapter (Asif,
                          2026-08-09). The Prophet's is deliberately not counted: his is
                          mandatory rather than capped, so counting it would report the
                          convention working as though it were the defect.

HOW THIS FILE IS ARRANGED, AND WHY

  The detectors themselves live in `_book_defects`, not here. Three callers need the
  same answer — this file, the compose review gate, and the `pf-compose-fix` skill — and
  a private copy is how two of them start disagreeing about what a defect is.

  A LIVE test per defect runs over every book and is ceilinged by `KNOWN`: it passes
  today and fails on anything NEW. An XFAIL(strict) per defect records what still
  stands, so the moment a repair lands the xfail turns into a hard failure — which is
  the prompt to delete the `KNOWN` entry rather than let the list rot.

  Nothing in this file mutates content.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _book_defects import (  # noqa: E402
    duplicated_arabic,
    english_set_right_to_left,
    honorific_overuse,
    is_arabic_quote_line,
    is_romanized_arabic,
    prophet_wrong_honorific,
    romanized_arabic,
)

# Overridable so these gates can be FALSIFIED against a scratch copy of a book rather
# than against `content/` itself — the same escape the compose-lane gates use.
CONTENT = Path(os.environ.get("PODCAST_CONTENT_ROOT") or REPO / "content")

#: The fixtures that pin the quotation-line rule against the two renderers.
QUOTE_LINE_FIXTURES = REPO / "plan-dashboard" / "scripts" / "lib" / "arabic-quote-line.fixtures.json"


def _books() -> list[Path]:
    found = sorted(CONTENT.glob("*/*/book/book.md")) + sorted(CONTENT.glob("*/*/*/book/book.md"))
    return [p for p in found if p.is_file()]


BOOKS = _books()
IDS = ["/".join(p.relative_to(CONTENT).parts[:-2]) for p in BOOKS]


#: What stands TODAY, by book. Each non-zero entry is an expected failure below.
#:
#: `romanized` counts sentences; `honorific` counts (chapter, figure) pairs that exceed
#: one use per chapter — NOT raw honorifics, which run into the hundreds. Neither can be
#: repaired without editing prose, and Asif's instruction of 2026-08-09 stands: no book
#: goes back through the pipeline for now. So they are recorded, not fixed.
KNOWN: dict[str, dict[str, int]] = {
    # The five misdirected-English instances that stood here on 2026-08-09 are GONE:
    # they were a renderer defect, not a content one, and weighing proportion repaired
    # all five across three books with no re-compose. `test_no_new_english_set_right_to_left`
    # now asserts zero everywhere, which is the end-to-end proof of that fix.
    "Islamic/ayyuhal-walad": {"honorific": 7, "prophet": 21},
    "Islamic/degrees-of-excellence": {"romanized": 1, "honorific": 8, "prophet": 1},
    "Islamic/kitab-al-riyad": {"honorific": 16, "prophet": 14},
    "Islamic/mukhtasar-ul-asar-1": {"honorific": 43, "prophet": 27},
    "Islamic/mukhtasar-ul-asar-2": {"honorific": 27, "prophet": 52},
    "Islamic/spiritual-ethos": {"duplicated": 1, "romanized": 13, "honorific": 14, "prophet": 3},
    "Islamic/the-master-and-the-disciple": {"honorific": 1},
}


def _known(book_id: str, key: str) -> int:
    return KNOWN.get(book_id, {}).get(key, 0)


def _book_id(book: Path) -> str:
    return "/".join(book.relative_to(CONTENT).parts[:-2])


def _recorded(key: str) -> list[str]:
    return [b for b, counts in KNOWN.items() if counts.get(key)]


# ── live gates: pass today, fail on anything NEW ─────────────────────────────


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_duplicated_arabic(book: Path) -> None:
    hits = duplicated_arabic(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "duplicated")
    assert len(hits) <= allowed, (
        f"{len(hits)} blockquote(s) repeat Arabic their lead-in already gave, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {r[:40]}" for t, r in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_english_set_right_to_left(book: Path) -> None:
    hits = english_set_right_to_left(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "rtl")
    assert len(hits) <= allowed, (
        f"{len(hits)} translation paragraph(s) will render right-to-left in the Arabic "
        f"face, {allowed} recorded: " + "; ".join(f"{t}: {p[:40]}" for t, p in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_romanized_arabic(book: Path) -> None:
    hits = romanized_arabic(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "romanized")
    assert len(hits) <= allowed, (
        f"{len(hits)} Arabic sentence(s) printed in the English character set, "
        f"{allowed} recorded: " + "; ".join(f"{t}: {r[:40]}" for t, r in hits)
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_honorific_overuse(book: Path) -> None:
    hits = honorific_overuse(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "honorific")
    assert len(hits) <= allowed, (
        f"{len(hits)} figure(s) carry a compact honorific more than once in a chapter, "
        f"{allowed} recorded: " + "; ".join(f"{t}/{f}×{n}" for t, f, n in hits[:5])
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_no_new_prophet_wrong_honorific(book: Path) -> None:
    hits = prophet_wrong_honorific(book.read_text(encoding="utf-8"))
    allowed = _known(_book_id(book), "prophet")
    assert len(hits) <= allowed, (
        f"{len(hits)} mention(s) give the Prophet a honorific that is not his, "
        f"{allowed} recorded: " + "; ".join(m for _, m in hits[:5])
    )


# ── the recorded failures: what is broken RIGHT NOW ──────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Spiritual Ethos ch.1 gives the same Arabic twice — inline in the lead-in and "
        "again in the blockquote under it. Repairable in the Book Composer without a "
        "re-compose; delete the KNOWN entry when it lands."
    ),
)
@pytest.mark.parametrize("book_id", _recorded("duplicated"))
def test_recorded_duplicated_arabic_is_gone(book_id: str) -> None:
    hits = duplicated_arabic((CONTENT / book_id / "book" / "book.md").read_text(encoding="utf-8"))
    assert hits == [], "; ".join(f"{t}: {r}" for t, r in hits)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "14 Arabic sayings print in the English character set, against the rule locked "
        "2026-08-02. Two of them have no Arabic anywhere on disk — not in the book, not "
        "in the source scan, not in the hadith corpus — so their script cannot be "
        "sourced and must never be recalled by a model on a religious text."
    ),
)
@pytest.mark.parametrize("book_id", _recorded("romanized"))
def test_recorded_romanized_arabic_is_gone(book_id: str) -> None:
    hits = romanized_arabic((CONTENT / book_id / "book" / "book.md").read_text(encoding="utf-8"))
    assert hits == [], "; ".join(f"{t}: {r[:50]}" for t, r in hits)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The compact honorific follows every occurrence of every name — 54 for Ali in "
        "one chapter of Spiritual Ethos. Capped at once per figure per chapter (Asif, "
        "2026-08-09); the cap is not implemented yet."
    ),
)
@pytest.mark.parametrize("book_id", _recorded("honorific"))
def test_recorded_honorific_overuse_is_gone(book_id: str) -> None:
    hits = honorific_overuse((CONTENT / book_id / "book" / "book.md").read_text(encoding="utf-8"))
    assert hits == [], "; ".join(f"{t}/{f}×{n}" for t, f, n in hits[:5])


@pytest.mark.xfail(
    strict=True,
    reason=(
        "118 mentions across six books give the Prophet the honorific of the Imams — "
        "`The Messenger of Allah (ع)`, 52 times in Mukhtasar 2 alone. His is the "
        "ligature (Asif, 2026-08-09), and this is wrong under any reading of the "
        "convention, so it does not wait on the cap policy."
    ),
)
@pytest.mark.parametrize("book_id", _recorded("prophet"))
def test_recorded_prophet_wrong_honorific_is_gone(book_id: str) -> None:
    hits = prophet_wrong_honorific((CONTENT / book_id / "book" / "book.md").read_text(encoding="utf-8"))
    assert hits == [], "; ".join(m for _, m in hits[:5])


def test_is_arabic_quote_line_matches_the_shared_fixtures() -> None:
    """The Python leg of the quotation-line mirror.

    The two renderers are pinned to each other by `arabic-quote-line.test.mjs`; this is
    the third copy reading the SAME fixtures, so a rule change has to move all three or
    fail here.
    """
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
        md = "## One\n\nHe said, and the words are these:\n\n> أنْتَ مِنِّی وَ أَنَا مِنْکَ\n"
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

    def test_a_pure_arabic_blockquote_is_not_flagged(self) -> None:
        md = "## One\n\nHe said:\n\n> إِنَّ عَلِيًّا مَعَ الْقُرْآنِ وَالْقُرْآنُ مَعَ عَلِيٍّ\n"
        assert english_set_right_to_left(md) == []

    def test_the_sentence_asif_photographed_is_detected(self) -> None:
        md = (
            '## One\n\nThe epigraph names it: "I am the city of knowledge and Ali (ع) is '
            "its gate\" (Ana madinatul-ilm wa 'Ali babuha; Fa-man aradal-ilm fal-yatil-bab).\n"
        )
        hits = romanized_arabic(md)
        assert len(hits) == 1 and hits[0][1].startswith("Ana madinatul-ilm")

    def test_a_persons_name_is_never_reported_as_romanized(self) -> None:
        # The false positive that the first draft produced on Kitab al-Riyad. A name
        # stays romanized by the annotation policy; substituting one would be a defect.
        assert is_romanized_arabic("al-Numan ibn Muhammad ibn Hayyun al-Maghribi") is False

    def test_english_prose_in_brackets_is_not_romanized_arabic(self) -> None:
        assert is_romanized_arabic("the argument of the chapter, which is that") is False
        assert is_romanized_arabic("a narrow approach to the material") is False

    def test_a_single_glossed_term_is_left_to_the_annotation_policy(self) -> None:
        # One or two romanized words are a TERM. Which terms carry an inline annotation
        # is the annotation policy's decision, and this check must not reach into it.
        assert is_romanized_arabic("mawaddah") is False
        assert is_romanized_arabic("nafi al-jins") is False

    def test_arabic_script_is_never_reported_as_romanized(self) -> None:
        assert is_romanized_arabic("أنا مدينة العلم وعليٌّ بابها") is False

    def test_honorific_overuse_is_detected_and_capped_per_chapter(self) -> None:
        md = "## One\n\nAli (ع) said. Later Ali (ع) said again.\n\n## Two\n\nAli (ع) said once.\n"
        hits = honorific_overuse(md)
        assert hits == [("One", "Ali", 2)], hits

    def test_the_prophets_ligature_is_not_counted_as_overuse(self) -> None:
        # His is mandatory rather than capped (Asif, 2026-08-09), so counting it here
        # would report the convention working as though it were the defect.
        md = "## One\n\nThe Prophet Muhammad ﷺ said. Again the Prophet Muhammad ﷺ said.\n"
        assert honorific_overuse(md) == []

    def test_the_prophet_carrying_someone_elses_honorific_is_detected(self) -> None:
        md = "## One\n\nThe Messenger of Allah (ع) said, and the Prophet (ع) confirmed it.\n"
        assert len(prophet_wrong_honorific(md)) == 2

    def test_an_imam_named_muhammad_keeps_his_own_honorific(self) -> None:
        # The reason the rule matches how the edition NAMES the Prophet rather than the
        # bare word: this corpus also carries Jafar ibn Muhammad and Abu Jafar Muhammad
        # ibn Ali, for whom `(ع)` is correct.
        md = "## One\n\nAl-Sadiq Jafar ibn Muhammad (ع) said, and Abu Jafar Muhammad ibn Ali (ع) agreed.\n"
        assert prophet_wrong_honorific(md) == []

    def test_the_prophets_own_ligature_is_not_a_wrong_honorific(self) -> None:
        assert prophet_wrong_honorific("## One\n\nThe Messenger of Allah ﷺ said.\n") == []
