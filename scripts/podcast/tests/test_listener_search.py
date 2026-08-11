"""The publish-time half of the search index.

What is pinned here is the part that cannot be seen from the browser: that a
passage is extracted from the RENDERED html rather than the markdown, that its
`quote` is the whole block exactly as `textContent` will hold it, and that the
fold does what the corpus needs. The TypeScript half is pinned against the same
fold by listener/test/search-fold.test.ts through a generated fixture.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _listener_search import (  # noqa: E402
    arabic_share,
    blocks_of,
    fold,
    passages_for,
)

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "listener"
    / "test"
    / "fixtures"
    / "search-fold.fixtures.json"
)


# ---------------------------------------------------------------------------
# fold
# ---------------------------------------------------------------------------


def test_fixtures_are_this_functions_output():
    """The generated file still describes THIS fold.

    The TypeScript side asserts it matches the fixtures. If the fixtures were
    regenerated from a changed Python fold and the TypeScript was not updated,
    that test fails there. If the Python changes and the fixtures are NOT
    regenerated, nothing there would notice — so it is noticed here.
    """
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for case in data["cases"]:
        assert fold(case["in"]) == case["out"], case["in"]


@pytest.mark.parametrize(
    "a, b",
    [
        ("اَلْكِرْمَانِيّ", "الكرماني"),  # vowelled vs bare
        ("ولی", "ولي"),  # farsi yeh vs arabic yeh
        ("کتاب", "كتاب"),  # keheh vs kaf
        ("ہے", "هے"),  # heh goal vs heh
        ("أبو", "ابو"),  # alif hamza vs alif
        ("Ismaʿili", "Ismaili"),  # transliteration vs house style
        ("Qur'an", "Quran"),
    ],
)
def test_spellings_the_corpus_mixes_fold_together(a, b):
    assert fold(a) == fold(b)


def test_fold_keeps_word_boundaries():
    # Unlike `normalize_arabic`, which strips them to make one skeleton.
    assert " " in fold("بسم الله الرحمن")
    assert fold("a  b\tc") == "a b c"


def test_fold_leaves_nothing_readable_as_query_syntax():
    assert fold('a" OR b* : (c)') == "a or b c"


def test_uthmani_midword_alif_is_folded_before_marks_are_stripped():
    # Strip the dagger first and the maqsura left behind folds to ya, so the
    # mushaf's spelling and a modern one stop matching. Order is the contract.
    assert fold("يُلَقَّىٰهَا") == fold("يلقاها")


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------


def test_block_text_is_what_textcontent_will_hold():
    """Including the caption, which is the whole point.

    The reading page finds a passage with `blockTextsOf`, which is
    `element.textContent`. A quotation renders as a caption band followed by the
    Arabic and `textContent` runs the two together — so the stored quote must
    too, or every quotation's deep link orphans.
    """
    html = (
        '<blockquote class="quran k-quote">'
        '<span class="q-band"><span class="q-kind">Al-Fatihah: 1</span></span>'
        '<p class="ar"><span class="ar-inline">بِسْمِ ٱللَّهِ</span></p>'
        "</blockquote>"
    )
    (block,) = blocks_of(html)
    assert block.text == "Al-Fatihah: 1بِسْمِ ٱللَّهِ"
    assert block.arabic == "بِسْمِ ٱللَّهِ"
    assert block.label == "Al-Fatihah: 1"


def test_blocks_are_top_level_only():
    html = "<p>One <em>with emphasis</em></p><blockquote><p>Two</p></blockquote>"
    assert [b.text for b in blocks_of(html)] == ["One with emphasis", "Two"]


def test_inline_elements_run_together_exactly_as_the_dom_does():
    # No space is inserted at an element boundary, because textContent inserts
    # none. A stored quote that differed here would never resolve.
    assert blocks_of("<p><em>foo</em><strong>bar</strong></p>")[0].text == "foobar"


def test_entities_are_decoded():
    assert blocks_of("<p>a &amp; b</p>")[0].text == "a & b"


def test_empty_and_void_elements_do_not_make_blocks():
    assert blocks_of("<p></p><hr/><p>real</p>")[0].text == "real"


def test_arabic_share_separates_a_quotation_from_a_glossed_term():
    assert arabic_share("اللَّهُ وَلِيُّ الَّذِينَ") == 1.0
    assert arabic_share("al-Kirmani (اَلْكِرْمَانِيّ) wrote") < 0.5
    assert arabic_share("no arabic here") == 0.0
    assert arabic_share("") == 0.0


# ---------------------------------------------------------------------------
# passages
# ---------------------------------------------------------------------------


@dataclass
class FakeChapter:
    anchor: str
    idx: int
    title: str
    html: str


@dataclass
class FakeEpisode:
    number: int
    title: str
    blurb: str | None = None


@dataclass
class FakeBook:
    slug: str = "a-book"
    title: str = "A Book"
    blurb: str | None = None
    chapters: list = None
    episodes: list = None

    def __post_init__(self):
        self.chapters = self.chapters or []
        self.episodes = self.episodes or []


def test_headings_are_not_indexed_as_passages():
    book = FakeBook(
        chapters=[FakeChapter("ch-1", 1, "One", "<h2>One</h2><p>The body.</p>")]
    )
    rows, _ = passages_for(book)
    assert [r.quote for r in rows] == ["The body."]
    # The chapter title still travels on the row, so a hit can say where it is.
    assert rows[0].heading == "One"


def test_prefix_is_always_empty_for_a_whole_block():
    # resolveAnchor compares a prefix against the text BEFORE the hit within its
    # block. A block quote starts at offset 0, where that is the empty string, so
    # a non-empty prefix would fail every comparison and orphan the link.
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", "<p>a</p><p>b</p>")])
    rows, _ = passages_for(book)
    assert [r.prefix for r in rows] == ["", ""]


def test_episodes_are_indexed_with_their_number():
    book = FakeBook(episodes=[FakeEpisode(3, "The Third", "About it")])
    rows, _ = passages_for(book)
    assert rows[0].kind == "episode"
    assert rows[0].episode_number == 3
    assert "third" in rows[0].body_fold


def test_ordinal_follows_document_order():
    book = FakeBook(
        chapters=[FakeChapter("ch-1", 1, "One", "<p>first</p><p>second</p><p>third</p>")]
    )
    rows, _ = passages_for(book)
    assert [r.ordinal for r in rows] == [0, 1, 2]


def test_arabic_column_carries_the_isolated_run_not_the_caption():
    html = (
        '<blockquote><span class="q-kind">Saying</span>'
        '<p class="ar"><span class="ar-inline">محمد بن احمد النسفي</span></p></blockquote>'
    )
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", html)])
    (row,), _ = passages_for(book)
    assert row.arabic == "محمد بن احمد النسفي"
    assert row.label == "Saying"
    # The caption must not be searchable AS Arabic, or an English word would
    # match the verse scope.
    assert "saying" not in row.arabic_fold


def test_a_non_quranic_quotation_gets_no_reference():
    html = '<blockquote><p class="ar"><span class="ar-inline">محمد بن احمد النسفي</span></p></blockquote>'
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", html)])
    (row,), _ = passages_for(book)
    assert row.surah is None and row.ayah is None
    assert row.kind == "chapter"


def test_english_prose_carrying_a_glossed_term_stays_prose():
    html = "<p>al-Kirmani (اَلْكِرْمَانِيّ) wrote the book.</p>"
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", html)])
    (row,), _ = passages_for(book)
    assert row.kind == "chapter"
    assert row.arabic is None
    # Still findable in Arabic, because the fold keeps it in the body column.
    assert "الكرماني" in row.body_fold


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


def test_english_prose_glossing_several_terms_is_not_a_quotation():
    """The share is judged on the WHOLE block, never on the isolated Arabic.

    Measuring the isolated run classified every glossing paragraph as Arabic —
    its Arabic is 100% Arabic by definition — which filled the verse scope with
    English prose and offered ordinary paragraphs to the mushaf as verse
    candidates.
    """
    html = (
        '<p>The first of those friends is <span class="ar-inline">ولی</span>. '
        'This word comes from <span class="ar-inline">مُوَالات</span>, '
        'which is a kind of protection.</p>'
    )
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", html)])
    (row,), _ = passages_for(book)
    assert row.kind == "chapter"
    assert row.arabic is None
    assert row.arabic_fold == ""


def test_sibling_arabic_runs_are_not_glued_together():
    """`ولي` beside `موالات` must not become `وليموالات`.

    Each glossed term is its own span. Joined without a separator they formed a
    word that appears in no book and that no search can match.
    """
    html = (
        '<p class="ar"><span class="ar-inline">ولي</span>'
        '<span class="ar-inline">موالات</span></p>'
    )
    (block,) = blocks_of(html)
    assert block.arabic == "ولي موالات"


def test_a_real_quotation_is_still_recognised_through_its_caption():
    html = (
        '<blockquote><span class="q-kind">Saying</span>'
        '<p class="ar"><span class="ar-inline">لَمَّا كُنْتُ وَلِيدًا ضَمَّنِي إِلَى صَدْرِهِ</span></p>'
        "</blockquote>"
    )
    book = FakeBook(chapters=[FakeChapter("ch-1", 1, "One", html)])
    (row,), _ = passages_for(book)
    # The caption is six Latin letters against a long Arabic run, so the block is
    # still overwhelmingly Arabic and is still a quotation.
    assert row.arabic is not None
    assert row.arabic_fold != ""
