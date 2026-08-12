"""What the Podcast Factory Library's advanced search is built from.

One job: turn a published book into the rows of `search_passage`. It runs inside
`publish_to_listener.py`, at the same moment and from the same `Book` object that
writes the chapters, which is what makes the index unable to describe a page that
is not there.

THE PASSAGES COME FROM THE RENDERED HTML, NOT THE MARKDOWN, and that is the whole
reason this module can exist without a fifth renderer. `*al-Riyad*` is four
characters longer in markdown than on screen, and a stored quote carrying the
asterisks would never match the text the reading page has in front of it — every
search result would land on its chapter and report that the passage had moved.
`Book.chapters[].html` is already the output of plan-dashboard's `renderMarkdown`
by the time this is called, so stripping its tags gives exactly the text the
browser will hold.

A PASSAGE IS ONE BLOCK, for two reasons that happen to agree. It is the unit the
reader can be shown — a paragraph, a quotation — where "somewhere in chapter 4"
is not an answer. And it is the unit `app/lib/anchor.ts` can find again after the
book is re-composed, since a block is what its `blocks` array holds.

WHAT THIS MODULE DOES NOT DO: decide who may read anything. Nothing here is
consulted at query time. Every read of these rows joins to the visibility
expression in `app/server/access.server.ts`, and there is no second copy of that
rule here or anywhere.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser

from _arabic_coverage import _ARABIC_FOLD, _ARABIC_TASHKEEL_RE, _UTHMANI_MIDWORD_ALIF_RE

try:  # The mushaf is a 30 MB tracked artifact; absence must degrade, never crash.
    from _mushaf import mushaf_available, mushaf_reference
except Exception:  # pragma: no cover - import guard only

    def mushaf_available() -> bool:
        return False

    def mushaf_reference(span: str) -> tuple[int, int] | None:
        return None


# ---------------------------------------------------------------------------
# Folding — one half of a mirror pair
# ---------------------------------------------------------------------------
# The other half is `fold` in listener/app/lib/search-fold.ts, and the two are
# pinned against each other by listener/test/fixtures/search-fold.fixtures.json.
# A divergence here does not raise anything: it makes a query silently match
# nothing, on precisely the vowelled Arabic this library is mostly made of. That
# is why it is pinned rather than trusted.
#
# The character rules are IMPORTED from _arabic_coverage rather than restated, so
# "what counts as a diacritic" has one answer in this repo. What differs is the
# ending: `normalize_arabic` strips everything that is not an Arabic letter,
# INCLUDING the spaces, because it exists to compare one run against another as a
# skeleton. A search index needs words, so this keeps the boundaries.

_LATIN_COMBINING_RE = re.compile(r"[̀-ͯ]")
_TATWEEL = "ـ"
# Straight and curly apostrophes, and the two accents people type for them.
_APOSTROPHES_RE = re.compile(r"['‘’´`]")

# Perso-Urdu letter forms, folded to their Arabic equivalents FOR SEARCH ONLY.
#
# This library is not uniformly Arabic-typed. The Sessions collection is Asif's
# own lectures, transcribed from markup written years ago on an Urdu-configured
# keyboard, so the same word is spelled with a different codepoint there than in
# the Arabic books. Counted across every published edition: 1,448 Farsi yeh
# against 3,264 Arabic yeh, 417 keheh against 1,599 Arabic kaf, 730 Urdu heh
# forms against 2,613 Arabic heh. Unfolded, a reader searching `ولي` matches the
# books and silently misses every lecture — the worst kind of miss, because the
# result page looks like a complete answer.
#
# WHY THIS IS NOT ADDED TO `_ARABIC_FOLD` UPSTREAM, which is the obvious tidier
# move: that table feeds `normalize_arabic`, and `normalize_arabic` is what
# decides whether a run of Arabic is Qur'an, whether a quotation is grounded in
# the OCR, and what the vowelling gate compares. Widening it would change those
# answers across the whole pipeline to make a search box better. Search folds
# more aggressively than provenance may, so it keeps its own table.
_SEARCH_FOLD = str.maketrans(
    {
        "ی": "ي",  # farsi yeh
        "ے": "ي",  # yeh barree
        "ک": "ك",  # keheh
        "گ": "ك",  # gaf — no Arabic equivalent; nearest for matching purposes
        "ہ": "ه",  # heh goal
        "ۃ": "ه",  # teh marbuta goal
        "ھ": "ه",  # heh doachashmee
        "ٹ": "ت",  # tteh
        "ڈ": "د",  # ddal
        "ڑ": "ر",  # rreh
        "ں": "ن",  # noon ghunna
        "ژ": "ز",
        "پ": "ب",
        "چ": "ج",
    }
)


def fold(text: str) -> str:
    """Lower-case, diacritic-free, word-preserving form used for matching.

    Order matters and is the same on both sides of the mirror:

      1. Uthmani mid-word alif, BEFORE anything strips marks. `ىٰ` before another
         letter is the long /a/ that modern spelling writes as a plain alif. Strip
         the dagger first and the maqsura left behind folds to ya, so the mushaf's
         spelling and the book's stop matching — the bug `_arabic_coverage`
         documents at length, inherited here for free by doing this first.
      2. Decompose, then drop combining marks: Latin accents and Arabic tashkeel
         both, so `Qur'ān` and `قُرْآن` fold the same way their unmarked forms do.
      3. Tatweel, which is decoration and never distinguishes two words.
      4. The letter-variant tables — alif carriers, maqsura, ta marbuta, then the
         Perso-Urdu forms — which is orthographic variation rather than marking,
         so decomposition misses all of it.
      5. Case, then everything that is not a letter or a digit becomes a space.
         Punctuation is a separator, never part of a token.
    """
    if not text:
        return ""

    out = _UTHMANI_MIDWORD_ALIF_RE.sub("ا", text)
    out = unicodedata.normalize("NFD", out)
    out = _LATIN_COMBINING_RE.sub("", out)
    out = _ARABIC_TASHKEEL_RE.sub("", out)
    out = out.replace(_TATWEEL, "")
    # Spacing modifier letters — the ayn and hamza of scholarly transliteration,
    # `Ismaʿili`. The house style already writes plain romanization, so these do
    # not occur in the corpus; they are dropped for what a READER types or pastes
    # from a bibliography, which should find the plain spelling the books use.
    # A category test rather than a list, so it cannot fall behind a new mark.
    out = "".join(ch for ch in out if unicodedata.category(ch) != "Lm")
    # Apostrophes are REMOVED, not turned into a separator, so `Qur'an` folds to
    # one token and matches `Quran` — which is how the house style spells it.
    # Split instead and a reader typing the apostrophe gets `qur AND an`, which
    # finds nothing: the AND needs a second token beginning `an`. The corpus
    # carries 3,187 of these and almost all are English possessives and
    # contractions (`Allah's`, `don't`), where joining is equally right —
    # `allahs` still matches a search for `allah` through the prefix wildcard.
    # This is the same decision as dropping the modifier letters above: an
    # apostrophe in this corpus is a hamza or an elision, never a word boundary.
    out = _APOSTROPHES_RE.sub("", out)
    out = out.translate(_ARABIC_FOLD)
    out = out.translate(_SEARCH_FOLD)
    out = out.lower()
    out = "".join(ch if ch.isalnum() else " " for ch in out)
    return " ".join(out.split())


# ---------------------------------------------------------------------------
# Rendered HTML -> the blocks the reader will actually have
# ---------------------------------------------------------------------------

# Elements that are not text and whose contents must not become a passage. A
# figure's caption is prose the reader sees, so `figure` is deliberately absent.
_SKIP = {"script", "style"}

# What counts as a top-level block. This mirrors what `blocksOf` walks in
# app/lib/anchor.ts — the element children of the chapter body — rather than
# guessing: anything the renderer emits at depth 0 is a block, whatever its tag.


@dataclass
class Block:
    """One top-level block of a rendered chapter, as three separate readings.

    `text` is what `blockTextsOf` in app/lib/anchor.ts will see — the element's
    `textContent`, whole and un-edited. It is the ANCHOR AUTHORITY and nothing may
    be trimmed out of it, however much it looks like chrome: a quotation renders
    as a band carrying `Saying` or `Al-Fatihah: 1` followed by the Arabic, and
    `textContent` runs the two together exactly as this does. Drop the band here
    and every quotation's deep link orphans, silently, on the material where
    landing on the right passage matters most.

    `arabic` and `label` are the same block read for DISPLAY, which is a different
    question: the search card sets the Arabic right-to-left in its own block and
    prints the citation above it, so it needs them apart. Isolating them here
    rather than re-parsing in the browser keeps a second HTML reading out of the
    Worker, which holds no markdown implementation for the same reason.
    """

    tag: str
    text: str
    arabic: str = ""
    label: str = ""


# Classes the rendered quotation markup uses. `ar` / `ar-inline` wrap the Arabic
# itself; `q-kind` is the band's caption — `Saying`, or the resolved citation.
_ARABIC_CLASSES = {"ar", "ar-inline"}
_LABEL_CLASSES = {"q-kind"}


def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
    for name, value in attrs:
        if name == "class" and value:
            return set(value.split())
    return set()


class _Blocks(HTMLParser):
    """Collect each top-level element, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self._depth = 0
        self._tag = ""
        self._buf: list[str] = []
        self._arabic: list[str] = []
        self._label: list[str] = []
        self._skip = 0
        # How many open ancestors are Arabic / label elements. Counters rather
        # than flags because these nest: `p.ar > span.ar-inline` is the norm.
        self._in_arabic = 0
        self._in_label = 0
        self._stack: list[tuple[str, bool, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP:
            self._skip += 1
            return
        if self._depth == 0:
            self._tag = tag
            self._buf = []
            self._arabic = []
            self._label = []

        classes = _classes(attrs)
        is_arabic = bool(classes & _ARABIC_CLASSES)
        is_label = bool(classes & _LABEL_CLASSES)
        self._stack.append((tag, is_arabic, is_label))
        # A separator between SIBLING Arabic runs. An English paragraph glosses
        # several terms, each in its own span, and without this their words are
        # concatenated into one — `ولي` + `موالات` became `وليموالات`, a word
        # that appears in no book and matches no search.
        #
        # The condition is simply "opening an Arabic element onto a non-empty
        # buffer". Testing `_in_arabic == 0` instead looks more precise and is
        # wrong: the runs nest as `p.ar > span.ar-inline`, so the counter is
        # already 1 when the sibling opens and no separator was ever added. A
        # doubled space costs nothing — the buffer is split on whitespace.
        if is_arabic and self._arabic:
            self._arabic.append(" ")
        self._in_arabic += is_arabic
        self._in_label += is_label
        self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._stack:
            _tag, was_arabic, was_label = self._stack.pop()
            self._in_arabic -= was_arabic
            self._in_label -= was_label
        self._depth -= 1
        if self._depth <= 0:
            text = " ".join("".join(self._buf).split())
            if text:
                self.blocks.append(
                    Block(
                        tag=self._tag,
                        text=text,
                        arabic=" ".join("".join(self._arabic).split()),
                        label=" ".join("".join(self._label).split()),
                    )
                )
            self._buf = []
            self._arabic = []
            self._label = []
        if self._depth < 0:  # stray close tag; treat the document as flat again
            self._depth = 0

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Void elements (img, br, hr) neither open nor close a block.
        return

    def handle_data(self, data: str) -> None:
        if self._skip or self._depth == 0:
            return
        self._buf.append(data)
        if self._in_arabic:
            self._arabic.append(data)
        if self._in_label:
            self._label.append(data)


def blocks_of(html: str) -> list[Block]:
    """Each top-level block of a rendered chapter, in document order."""
    parser = _Blocks()
    parser.feed(unescape(html or ""))
    parser.close()
    return parser.blocks


# ---------------------------------------------------------------------------
# Arabic-ness, and what the mushaf can name
# ---------------------------------------------------------------------------

_ARABIC_CHAR_RE = re.compile(r"[؀-ۿ]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# Below this share of letters, a block with some Arabic in it is English prose
# carrying a glossed term — `al-Kirmani (اَلْكِرْمَانِيّ)` — not a quotation. Such a
# block is ordinary prose whose Arabic is still searchable; it is simply not a
# candidate verse. Above it, the block IS the Arabic.
_ARABIC_BLOCK_SHARE = 0.5


def arabic_share(text: str) -> float:
    """Share of the block's letters that are Arabic script, 0.0 when there are none."""
    letters = _LETTER_RE.findall(text or "")
    if not letters:
        return 0.0
    arabic = sum(1 for ch in letters if _ARABIC_CHAR_RE.match(ch))
    return arabic / len(letters)


# ---------------------------------------------------------------------------
# The rows
# ---------------------------------------------------------------------------


@dataclass
class Passage:
    slug: str
    kind: str
    quote: str
    anchor_key: str | None = None
    heading: str | None = None
    ordinal: int = 0
    episode_number: int | None = None
    prefix: str = ""
    arabic: str | None = None
    # The caption the edition itself prints above a quotation — `Saying`, or the
    # citation it resolved at render time. Stored rather than recomputed so the
    # search card and the page agree about what a quotation is called.
    label: str | None = None
    surah: int | None = None
    ayah: int | None = None
    heading_fold: str = ""
    body_fold: str = ""
    arabic_fold: str = ""


@dataclass
class IndexReport:
    """What the run produced, for the publisher to print."""

    passages: int = 0
    verses: int = 0
    named_verses: int = 0
    mushaf: bool = True
    per_kind: dict[str, int] = field(default_factory=dict)


def passages_for(book) -> tuple[list[Passage], IndexReport]:
    """Every indexable passage of one book, plus what to report about the run."""
    rows: list[Passage] = []
    report = IndexReport(mushaf=mushaf_available())

    # The blurb, so a book can be found by what its introduction says about it.
    if getattr(book, "blurb", None):
        for block in blocks_of(book.blurb):
            rows.append(
                Passage(
                    slug=book.slug,
                    kind="blurb",
                    quote=block.text,
                    heading=book.title,
                    heading_fold=fold(book.title),
                    body_fold=fold(block.text),
                )
            )
            break  # The blurb is one paragraph on the card; index the first only.

    for chapter in getattr(book, "chapters", []):
        heading_fold = fold(f"{book.title} {chapter.title}")
        for ordinal, block in enumerate(blocks_of(chapter.html)):
            # A heading is already carried on every row of its own chapter as
            # `heading`; indexing it again as a passage would return the title as
            # a hit whose "passage" is the title.
            if block.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                continue

            # JUDGED ON THE WHOLE BLOCK, never on the isolated Arabic.
            #
            # This was the other way round and it was wrong in a way worth
            # recording. An English paragraph that glosses a term — "the first of
            # those friends is ولی" — has an isolated Arabic run that is, by
            # definition, 100% Arabic, so measuring THAT classified every such
            # paragraph as a quotation. Two consequences, both bad: the verse
            # scope filled up with English prose, and ordinary paragraphs were
            # offered to the mushaf as verse candidates, which is one unlucky
            # skeleton match away from printing a citation over prose.
            #
            # The whole block's share is the honest question — is this passage
            # Arabic, or is it English with Arabic in it — and the isolated run
            # is used only afterwards, once the answer is yes, to look the verse
            # up and to set it apart from its caption on screen.
            is_arabic = arabic_share(block.text) >= _ARABIC_BLOCK_SHARE
            candidate = block.arabic or block.text
            surah = ayah = None
            kind = "chapter"

            if is_arabic:
                reference = mushaf_reference(candidate) if report.mushaf else None
                if reference is not None:
                    kind = "verse"
                    surah, ayah = reference
                    report.named_verses += 1
                report.verses += 1

            rows.append(
                Passage(
                    slug=book.slug,
                    kind=kind,
                    # The WHOLE block text, caption included. See `Block`.
                    quote=block.text,
                    anchor_key=chapter.anchor,
                    heading=chapter.title,
                    ordinal=ordinal,
                    # Empty, always, and see the column comment in 0012_search.sql:
                    # a whole-block quote starts at offset 0, where resolveAnchor
                    # compares the prefix against the empty string.
                    prefix="",
                    arabic=candidate if is_arabic else None,
                    label=block.label or None,
                    surah=surah,
                    ayah=ayah,
                    heading_fold=heading_fold,
                    # Arabic inside an English sentence is still searchable in
                    # Arabic: the fold keeps it, so it stays in body_fold. The
                    # arabic_fold column is for blocks that ARE the Arabic, which
                    # is what the verse scope searches, and it carries the
                    # isolated run so a caption cannot match as scripture.
                    body_fold=fold(block.text),
                    arabic_fold=fold(candidate) if is_arabic else "",
                )
            )

    for episode in getattr(book, "episodes", []):
        text = " ".join(filter(None, [episode.title, getattr(episode, "blurb", None)]))
        rows.append(
            Passage(
                slug=book.slug,
                kind="episode",
                quote=text,
                heading=episode.title,
                episode_number=episode.number,
                heading_fold=fold(f"{book.title} {episode.title}"),
                body_fold=fold(text),
            )
        )

    report.passages = len(rows)
    for row in rows:
        report.per_kind[row.kind] = report.per_kind.get(row.kind, 0) + 1
    return rows, report
