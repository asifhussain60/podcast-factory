"""The two prose lanes stay distinct deliverables — the invariant the Book
Composer's lane switch depends on.

A book that has been podcasted carries TWO English texts of the same Arabic
source:

  * ``book/book.md``   — the reading edition, what becomes ``book/book.pdf``.
  * ``chapters/*.txt`` — the NotebookLM upload source.

They are independently translated, independently segmented (this repo's first
case: 9 book chapters against 20 podcast chapters, with non-corresponding
titles), and the podcast lane deliberately carries material the book does not:
a leading italic narration-framing paragraph written for NotebookLM,
interleaved teaching commentary, and cited references with source attributions.

The Composer flips between them read-only precisely BECAUSE no positional edit
can be mirrored across them. These tests fail if someone erases that
distinction — by copying articulated book prose over a chapter source (which
would delete the framing, commentary and citations that make it a NotebookLM
source at all) or by stripping the framing out of the podcast lane.

Deliberately property-based, not value-pinned: every assertion holds for any
podcasted book, so a legitimate re-compose or a new book cannot break it.
Books without both lanes are skipped, not failed.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# The content root, overridable so these gates can be FALSIFIED — broken on
# purpose to prove they fail — against a scratch copy of a book rather than
# against `content/` itself. A gate you can only test by mutating the real
# corpus is a gate nobody dares test.
CONTENT = Path(os.environ.get("PODCAST_CONTENT_ROOT") or REPO / "content")

# An ATTRIBUTED cited reference — the podcast lane's teaching apparatus, which
# names the translator or the collection it is quoting:
#   "(Quran 14:7, Sahih International rendering)"
#   "(reported in al-Hindi, *Kanz al-Ummal*, hadith 41723)"
#   "(Nahj al-Balagha, Saying 113, Reza translation)"
# Deliberately NOT a bare locator like "(Quran 12:105)": the reading edition
# does use those, and treating them as podcast apparatus made this test fail on
# a legitimate reference. What separates the lanes is the ATTRIBUTION — the book
# renders scripture through its own apparatus and never names a translator
# inline (measured 2026-07-26: 0 in the reading edition, 22 across the podcast
# chapter sources).
ATTRIBUTED_CITATION_RE = re.compile(
    r"\((?:Quran\s+\d+:\d+,\s*[^)]+|Nahj al-Balagha[^)]*|reported in [^)]+"
    r"|[^)]*hadith\s+\d+)\)",
    re.I,
)


def _podcasted_books() -> list[Path]:
    """Book dirs carrying BOTH a reading edition and podcast chapter sources."""
    found: list[Path] = []
    for bucket in sorted(CONTENT.glob("*/")):
        if bucket.name.startswith("_") or bucket.name == "knowledge-base":
            continue
        for book in sorted(p for p in bucket.iterdir() if p.is_dir()):
            if (book / "book" / "book.md").is_file() and list((book / "chapters").glob("*.txt")):
                found.append(book)
    return found


BOOKS = _podcasted_books()
IDS = [f"{b.parent.name}/{b.name}" for b in BOOKS]

if not BOOKS:  # pragma: no cover - depends on working-copy content
    pytest.skip("no book carries both prose lanes", allow_module_level=True)


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_podcast_chapters_keep_their_narration_framing(book: Path) -> None:
    """Every chapter source opens with the italic framing NotebookLM is given.

    This is the paragraph that makes the file a podcast SOURCE rather than a
    slice of the book. Mirroring book prose over it is what would delete it.
    """
    chapters = sorted((book / "chapters").glob("*.txt"))
    framed, missing = [], []
    for txt in chapters:
        lines = [ln.strip() for ln in txt.read_text(encoding="utf-8").splitlines()]
        head = [ln for ln in lines[:8] if ln]
        # First heading, then an italic framing paragraph.
        if any(ln.startswith("*") and ln.endswith("*") for ln in head):
            framed.append(txt.name)
        else:
            missing.append(txt.name)

    # NOT asserted universally. An earlier pipeline generation authored chapters
    # with no narration framing at all (see the sibling citation test), so a book
    # with none is a legacy shape, not a defect — and a gate that reds for a
    # non-defect is a gate that stops being believed. What IS a defect is a book
    # that had the framing and lost it in SOME chapters, which is the shape "book
    # prose copied over a chapter source" leaves behind.
    if not framed:
        pytest.skip("this book's chapter sources predate narration framing")
    assert not missing, (
        f"{len(missing)} of {len(chapters)} chapter sources lost their narration "
        f"framing while {len(framed)} kept it (book prose copied over them?): {missing}"
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_the_reading_edition_never_names_a_translator_inline(book: Path) -> None:
    """The direction that always holds: the book carries no attributed citation.

    The reading edition renders scripture through its own apparatus. An
    attributed citation appearing in book.md means podcast-lane prose reached
    the reading edition — the exact failure the read-only lane exists to make
    impossible.
    """
    book_md = (book / "book" / "book.md").read_text(encoding="utf-8")
    hits = ATTRIBUTED_CITATION_RE.findall(book_md)
    assert not hits, (
        "the reading edition picked up the podcast lane's attributed citation "
        f"style ({len(hits)} occurrence(s)) — podcast prose reached book.md: {hits[:3]}"
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_podcast_lane_apparatus_stays_in_the_podcast_lane(book: Path) -> None:
    """Where a book's chapter sources DO cite with attribution, book.md doesn't.

    Not every book's podcast lane carries this apparatus (an earlier pipeline
    generation authored chapters without it — `ayyuhal-walad` has none), so the
    presence of citations is not asserted as universal; what IS asserted is that
    none of the ones a book does have crossed into the reading edition.
    """
    found: set[str] = set()
    for txt in sorted((book / "chapters").glob("*.txt")):
        found.update(ATTRIBUTED_CITATION_RE.findall(txt.read_text("utf-8")))
    if not found:
        pytest.skip("this book's chapter sources carry no attributed citations")

    book_md = (book / "book" / "book.md").read_text(encoding="utf-8")
    crossed = sorted(c for c in found if c in book_md)
    assert not crossed, f"{len(crossed)} podcast-lane citation(s) appear verbatim in the reading edition: {crossed[:3]}"


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_the_lanes_are_separately_segmented(book: Path) -> None:
    """No chapter-to-chapter mapping exists, and none may be assumed.

    The Composer must never carry a positional edit from one lane to the other.
    The guard here is that the two chapter TITLE sets do not coincide: if a
    future change made them line up, the mirroring assumption would silently
    look safe and this test is the place that argues about it first.
    """
    book_titles = {
        re.sub(r"^##\s+\d*\.?\s*", "", h).strip().casefold()
        for h in re.findall(r"^##\s+.+$", (book / "book" / "book.md").read_text("utf-8"), re.M)
    }
    podcast_titles = set()
    for txt in sorted((book / "chapters").glob("*.txt")):
        m = re.search(r"^#\s+(.+)$", txt.read_text("utf-8"), re.M)
        if m:
            podcast_titles.add(m.group(1).strip().casefold())

    if not book_titles or not podcast_titles:
        pytest.skip("one lane has no chapter headings to compare")
    assert book_titles != podcast_titles, (
        "the two lanes' chapter titles became identical — re-examine whether "
        "the Composer's no-mirroring rule still has the reason it was written for"
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_podcast_lane_prose_is_not_a_copy_of_the_reading_edition(book: Path) -> None:
    """The same passage is worded differently in each lane.

    Compared as long shared runs rather than word overlap: two translations of
    one source share vocabulary everywhere, but a COPY shares whole sentences.
    """
    book_md = (book / "book" / "book.md").read_text(encoding="utf-8")
    book_sentences = {
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", book_md))
        if len(s.strip()) >= 120  # long enough that a match cannot be chance
    }
    assert book_sentences, "the reading edition has no long sentences to compare"

    duplicated: list[str] = []
    for txt in sorted((book / "chapters").glob("*.txt")):
        flat = re.sub(r"\s+", " ", txt.read_text("utf-8"))
        for s in re.split(r"(?<=[.!?])\s+", flat):
            s = s.strip()
            if len(s) >= 120 and s in book_sentences:
                duplicated.append(f"{txt.name}: {s[:80]}…")

    # A handful of shared long sentences is possible where both lanes quote the
    # same verbatim translation of a verse; wholesale sharing is a copy.
    assert len(duplicated) <= 3, (
        f"{len(duplicated)} long sentences appear verbatim in BOTH lanes — one "
        f"lane looks copied from the other. First: {duplicated[:3]}"
    )


@pytest.mark.parametrize("book", BOOKS, ids=IDS)
def test_articulation_state_is_intact(book: Path) -> None:
    """The lane switch is a display change — it must not disturb articulation.

    Asserted as a CONSISTENCY property rather than pinned numbers: every chapter
    the reading edition has was adapted, and none was reverted. Pinning the
    literal count (9 adapted / 0 reverted on 2026-07-26) would turn a legitimate
    re-compose into a red gate, which is how a test stops being believed.

    ``adapted == 0 and reverted == 0`` is what the Composer's
    ``articulationWarnings`` is computed from, so this is also the durable half
    of "articulationWarnings is still empty" — the TypeScript side of that
    computation is covered by ``articulation.test.ts``.
    """
    report = book / "_system" / "book-fluency-report.json"
    if not report.is_file():
        pytest.skip("no articulation report — the contract does not apply here")

    data = json.loads(report.read_text(encoding="utf-8"))
    chapters = re.findall(r"^##\s+.+$", (book / "book" / "book.md").read_text("utf-8"), re.M)
    assert data.get("reverted") == 0, (
        f"articulation reports {data.get('reverted')} reverted chapter(s) — "
        "the reading edition regressed to un-articulated prose"
    )
    # Front matter (the introduction) is apparatus, not an adapted chapter, so
    # adapted is <= the heading count rather than equal to it.
    adapted = data.get("adapted")
    assert isinstance(adapted, int) and adapted > 0, f"adapted={adapted!r}"
    assert adapted <= len(chapters), (
        f"articulation claims {adapted} adapted chapters but the edition has {len(chapters)} headings"
    )
