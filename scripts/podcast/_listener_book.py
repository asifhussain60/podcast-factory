"""Read one book off disk, the way the Listener needs it.

Everything here answers "what is in `content/<Bucket>/<slug>/`" — the reading
edition split into chapters, the episodes, and an inventory of the media files.
Nothing here writes anywhere; `publish_to_listener.py` is what turns the result
into SQL.

Split out of that script when it crossed the module line-count gate, along the
seam that was already there: reading is the part with all the judgment calls in
it (how a chapter is keyed, which audio belongs to which episode, what counts as
a blurb) and writing is mechanical.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from _book_edits import anchor_key  # noqa: E402
from _listener_companion import (  # noqa: E402
    CompanionCard,
    attach_companion,
    cards_to_render,
    read_companion,
)

# Re-exported deliberately: `Asset`, `Episode` and the collectors were part of
# this module's surface before the split, and four callers plus two test files
# name them here. A facade keeps the split an internal matter.
from _listener_media import (  # noqa: E402,F401
    AUDIO_NUMBER_RE,
    CONTENT_TYPES,
    EPISODES_DIR,
    IMAGE_TYPES,
    MASTERS_DIR,
    SESSION_DIR_RE,
    Asset,
    ChapterNarration,
    Episode,
    Session,
    audio_duration,
    collect_audio,
    collect_media,
)
from _listener_source_ref import SourceReference, read_source_references  # noqa: E402
from _paths import find_content  # noqa: E402

LISTENER = Path(__file__).resolve().parents[2] / "listener"

#: What a card credits when the book records no author (Asif, 2026-09-01). The
#: string is shared with the migration's column default so the two cannot
#: disagree about what an unattributed work is called.
ANONYMOUS = "Anonymous"

# A heading that opens a chapter of the reading edition. `# ` is the book title
# and never a chapter; `### ` and deeper are sections inside one.
CHAPTER_HEADING_RE = re.compile(r"^##\s+(?!#)(.+?)\s*$")


# ---------------------------------------------------------------------------
# What we found on disk
# ---------------------------------------------------------------------------


@dataclass
class Chapter:
    anchor: str
    idx: int
    title: str
    markdown: str
    html: str = ""
    narration: ChapterNarration | None = None

    @property
    def word_count(self) -> int:
        return len(self.markdown.split())


#: The study tracks a book may declare. The reader colours its shelf from this and
#: anything outside it is dropped rather than guessed. Named (rather than left as
#: the inline literal it was until 2026-08-30) so the intake form can offer exactly
#: these values instead of restating the list and drifting from it.
STUDY_TRACKS: frozenset[str] = frozenset({"theology", "history", "shariah", "esoteric", "reality", "philosophy"})


@dataclass
class Book:
    slug: str
    bucket: str
    directory: Path
    title: str
    title_arabic: str | None
    title_language: str | None
    study_track: str | None
    blurb: str | None
    edition_note: str | None
    #: Never empty. `ANONYMOUS` where a book records no author — the card is
    #: designed like a jacket and a jacket always prints a credit, so "always" is
    #: guaranteed here rather than remembered by a template.
    #:
    #: Defaulted rather than required so the loader stays the only place that has
    #: to know how a missing author is spelled. Twenty-five tests construct a
    #: `Book` directly to exercise media collection and the publish SQL, and none
    #: of them is about attribution; making them all name an author would be
    #: fixture noise that says nothing.
    author: str = ANONYMOUS
    #: The name a card can print on ONE line. Falls back to `author`, which is
    #: right for the short ones and is why this is not required of every book.
    author_short: str = ANONYMOUS
    chapters: list[Chapter] = field(default_factory=list)
    episodes: list[Episode] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    bridge: list[tuple[int, str]] = field(default_factory=list)
    # The notes exactly as filed, by section key — the raw read. `render` turns
    # them into `companion` once the renderer has told us which chapter each
    # section key belongs to. Same two-phase shape as a chapter's markdown/html.
    companion_notes: dict[str, list[dict]] = field(default_factory=dict)
    companion: list[CompanionCard] = field(default_factory=list)
    # The reading edition's source-crosswalk, reduced to what a reader may see:
    # page range and headings only. Empty on the 19-of-27 books with no
    # `book/source-crosswalk.json` — see `_listener_source_ref`.
    source_references: list[SourceReference] = field(default_factory=list)
    unmatched_audio: list[str] = field(default_factory=list)
    cover: Asset | None = None
    pdf: Asset | None = None


# ---------------------------------------------------------------------------
# Reading a book
# ---------------------------------------------------------------------------


def split_chapters(book_md: str) -> list[Chapter]:
    """Split the reading edition into chapters at its `##` headings.

    Keyed by `anchor_key`, the same normalisation the Book Composer uses to find
    a chapter it saved an edit against, so a chapter keeps its identity across a
    re-compose that renumbers it. The number in `## 3. Title` is part of the
    display title and NOT part of the key, for exactly that reason.
    """
    chapters: list[Chapter] = []
    current: list[str] = []
    title: str | None = None

    def close() -> None:
        if title is None:
            return
        chapters.append(
            Chapter(
                anchor=anchor_key(title),
                idx=len(chapters) + 1,
                title=title,
                markdown="\n".join(current).strip(),
            )
        )

    for line in book_md.replace("\r\n", "\n").split("\n"):
        match = CHAPTER_HEADING_RE.match(line)
        if match:
            close()
            title = match.group(1).strip()
            current = []
        elif title is not None:
            current.append(line)

    close()
    return chapters


def read_episodes(book_dir: Path) -> list[Episode]:
    """Episodes come from the chapter contracts, which are the authored record.

    The `episodes/EP*.txt` files are the NotebookLM framings — what gets pasted
    into the Customize box — and their filenames carry a slug rather than the
    episode's real title. The contracts carry `episode_number`, `title`,
    `episode_format` and a written blurb, so they are the better source. A book
    with no contracts simply has no episodes here.
    """
    contracts = sorted((book_dir / "chapter-contracts").glob("*.yml"))
    if not contracts:
        return _audiobook_episodes(book_dir)

    episodes: dict[int, Episode] = {}

    for path in contracts:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue

        number = data.get("episode_number")
        if not isinstance(number, int):
            continue

        notes = data.get("show_notes") or {}
        episodes[number] = Episode(
            number=number,
            title=str(data.get("title") or f"Episode {number}"),
            blurb=(notes.get("blurb") if isinstance(notes, dict) else None),
            style=data.get("episode_format"),
        )

    return [episodes[n] for n in sorted(episodes)]


#: The audiobook lane's own record of its recordings, written by the ingest that
#: split the source file. Same role the chapter contracts play for the podcast
#: lane: the authored list of what exists, with the numbering already decided.
AUDIOBOOK_CHAPTERS = "audiobook-chapters.json"


def _audiobook_episodes(book_dir: Path) -> list[Episode]:
    """Episodes for a book whose audio came off a recording, not out of NotebookLM.

    `read_episodes` derives episodes from `chapter-contracts/*.yml`, which is the
    PODCAST lane's authored record. An audiobook has none — its ingest writes
    `_system/audiobook-chapters.json` instead — so White Nights dry-ran as nine
    chapters and ZERO episodes on 2026-09-01, with eight bridge entries pointing
    at episodes that did not exist. The book would have published as text with no
    audio at all, and the failure was silent: nothing errored, the count simply
    read 0.

    The titles in that file are the source's own filenames
    (`02_WhiteNights_Introduction`), which are provenance rather than something to
    show a reader. The bridge already names the chapter each episode belongs to,
    and that name IS the reader-facing title, so it is used where it exists and
    the raw stem is the fallback — never a guess, just the less good of two real
    answers.

    No blurb and no style: an audiobook chapter has neither, and inventing them
    would put authored-looking prose under a title nobody wrote.
    """
    path = book_dir / "_system" / AUDIOBOOK_CHAPTERS
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    bridge_titles: dict[int, str] = {}
    bridge_path = book_dir / "_system" / "listener-episode-chapters.json"
    if bridge_path.exists():
        try:
            raw = json.loads(bridge_path.read_text(encoding="utf-8"))
            for key, titles in (raw or {}).items():
                if isinstance(titles, list) and titles and str(key).isdigit():
                    bridge_titles[int(key)] = str(titles[0])
        except (OSError, ValueError):
            pass

    episodes: dict[int, Episode] = {}
    for entry in data.get("chapters") or []:
        number = entry.get("episode")
        if not isinstance(number, int):
            continue
        episodes[number] = Episode(
            number=number,
            title=bridge_titles.get(number) or str(entry.get("title") or f"Episode {number}"),
            blurb=None,
            style=None,
        )
    return [episodes[n] for n in sorted(episodes)]


def read_bridge(book_dir: Path, chapters: list[Chapter]) -> list[tuple[int, str]]:
    """The episode-to-chapter map, ONLY where a human wrote one down.

    `_system/listener-episode-chapters.json` is `{"1": ["chapter title", …], …}`
    keyed by episode number. Nothing derives this: a chapter contract's
    `source_chapter_ref` points into the SOURCE book's chapter numbering, which
    is a third segmentation again, so inferring the link would be a guess
    presented as a fact. A title that matches no chapter is reported by the
    caller rather than dropped silently.
    """
    path = book_dir / "_system" / "listener-episode-chapters.json"
    if not path.exists():
        return []

    known = {c.anchor: c for c in chapters}
    pairs: list[tuple[int, str]] = []
    data = json.loads(path.read_text(encoding="utf-8"))

    for number, titles in data.items():
        for title in titles:
            key = anchor_key(str(title))
            if key in known:
                pairs.append((int(number), key))
            else:
                print(f"  ! episode {number} names a chapter that does not exist: {title}")

    return pairs


def credit(meta: dict) -> tuple[str, str]:
    """A book's author and the one-line form a card prints, from its `meta.yml`.

    Its own function so the rule can be tested without a book on disk — the
    loader around it resolves a slug through the content tree, which a unit test
    would have to build a whole bucket to satisfy.

    NEITHER IS EVER DERIVED. A missing author becomes `ANONYMOUS`, which is an
    honest statement about a work of unknown authorship and is true of several of
    these; it is not a placeholder to be improved later. And a missing alias
    becomes the full name rather than an abbreviation of it: shortening
    "Jaʿfar ibn Manṣūr al-Yaman" by rule means guessing which part is the
    surname, and Arabic names do not have one. The alias is a judgement somebody
    made and recorded, or it is the full name unchanged.
    """
    author = str(meta.get("author") or "").strip() or ANONYMOUS
    return author, (str(meta.get("author_short") or "").strip() or author)


def load_book(slug: str, *, normalise_audio: bool = False) -> Book:
    """Read one book off disk.

    `normalise_audio` brings the recordings to the spoken-word profile and drops
    the masters BEFORE anything is read — see `downsize_audio.normalise`. It lives
    here, as part of loading, because the two must not be separable: the byte
    counts and hashes this function reads are what a publish records, so reading
    first and normalising after would stamp the database with the sizes of files
    that no longer exist. Defaults to off, so every read-only caller is unaffected;
    `publish_to_listener` is what turns it on.
    """
    found = find_content(slug)
    if found is None:
        raise SystemExit(f"no content found for slug '{slug}'")

    # find_content returns (status, bucket, path). The status is deliberately
    # discarded: whether a unit is readable is the Listener's own `content_unit`
    # column, decided in the admin screens, and letting the pipeline's state file
    # drive it would put the privilege bit back under a script's control.
    _status, bucket, directory = found

    if normalise_audio:
        from downsize_audio import normalise  # local: only the publish path needs it

        done = normalise(directory, apply=True, log=lambda _m: None)
        if done["encoded"] or done["masters"]:
            print(f"  audio normalised: {done['encoded']} re-encoded, {done['masters']} master(s) dropped")

    meta = yaml.safe_load((directory / "meta.yml").read_text(encoding="utf-8")) or {}

    book_md_path = directory / "book" / "book.md"
    if not book_md_path.exists():
        raise SystemExit(
            f"'{slug}' has no reading edition at book/book.md — nothing to publish. "
            "Run the book branch of the pipeline first."
        )

    intro = directory / "_system" / "edition-introduction.md"
    blurb = None
    if intro.exists():
        paragraphs = [p.strip() for p in intro.read_text(encoding="utf-8").split("\n\n")]
        blurb = next((p for p in paragraphs if p), None)

    series = directory / "_system" / "series-config.yaml"
    edition_note = None
    if series.exists():
        config = yaml.safe_load(series.read_text(encoding="utf-8")) or {}
        edition_note = config.get("deliverable_mode")

    original_language = meta.get("original_title_language")
    original_title = (
        meta.get("title_urdu")
        or meta.get("title_arabic")
        or (meta.get("original_title") if original_language in {"ar", "ur", "zh"} else None)
    )
    title_language = (
        "ur"
        if meta.get("title_urdu")
        else "ar"
        if meta.get("title_arabic")
        else original_language
        if original_title
        else None
    )

    # An author of unknown authorship is a real answer, and a truer one than a
    # blank. Several of these works are anonymous by their own tradition.
    author, author_short = credit(meta)

    study_track = meta.get("study_track")
    if study_track not in STUDY_TRACKS and study_track is not None:
        study_track = None

    book = Book(
        slug=slug,
        bucket=bucket,
        directory=directory,
        title=str(meta.get("title") or slug),
        author=author,
        author_short=author_short,
        title_arabic=original_title,
        title_language=title_language,
        study_track=study_track,
        blurb=blurb,
        edition_note=edition_note,
        chapters=split_chapters(book_md_path.read_text(encoding="utf-8")),
        episodes=read_episodes(directory),
    )

    book.bridge = read_bridge(directory, book.chapters)
    book.companion_notes = read_companion(directory)
    book.source_references = read_source_references(directory, book.chapters)
    collect_media(book)
    return book


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_BOOK_IMAGE_SRC = re.compile(r'(<img\b[^>]*?\bsrc=")images/([^"]+)(")', re.I)


def _media_image_srcs(html: str, slug: str) -> str:
    """Point an illustration at the gated media route instead of at the folder.

    `book.md` writes `images/<sid>/<guid>.jpg`, relative to `book/`, and that is
    RIGHT — it is what makes the same file render in the print edition, where the
    PDF is built in that directory. The site has no such directory, so the same
    source has to resolve two ways and this is the second one.

    Done here, on the rendered HTML, rather than by teaching the renderer about
    the site: `renderMarkdown` is shared with the printed book precisely so the
    two cannot disagree about what a paragraph looks like, and a site-only URL
    rule inside it would be the first thing they disagreed about.

    `/media/<key>` runs `requireUnitAccess` on the slug, so an illustration is
    reachable by exactly the people who may read the chapter around it — no new
    authorisation path, and none possible.
    """
    return _BOOK_IMAGE_SRC.sub(rf"\1/media/{slug}/image/\2\3", html)


def render(book: Book) -> None:
    """Fill in every chapter's HTML, the blurb's, and the Companion cards'.

    ONE call to the renderer, carrying everything that needs it. The blurb goes
    through it because it is markdown on disk carrying italics, inline Arabic and
    scholarly transliteration, so shipping the raw text put `*Kitab al-Alim
    wa-l-Ghulam*` on the page with its asterisks showing and its diacritics
    unfolded. The Companion cards go through it for the same reason, through the
    card's own renderer.

    The same call answers a second question: which chapter each companion file
    belongs to. Every chapter's HEADING goes over with it and comes back with the
    `section_key` the notes are filed under, so the ordinal-keeping rule stays in
    the one module that owns it and this side only ever compares two strings. The
    FOLDER goes over for the same reason: the bridge reads its quotation maps.
    """
    items = [{"anchor_key": c.anchor, "heading": c.title, "markdown": c.markdown} for c in book.chapters]
    if book.blurb is not None:
        items.append({"anchor_key": "\x00blurb", "markdown": book.blurb})

    cards = cards_to_render(book.companion_notes)

    if not items:
        return

    result = subprocess.run(
        ["node", "scripts/render-chapters.mjs"],
        cwd=LISTENER,
        input=json.dumps({"chapters": items, "cards": cards, "book_dir": str(book.directory)}),
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    rendered = {c["anchor_key"]: c["html"] for c in payload["chapters"]}
    for chapter in book.chapters:
        chapter.html = _media_image_srcs(rendered[chapter.anchor], book.slug)
    if book.blurb is not None:
        book.blurb = rendered["\x00blurb"]

    book.companion = attach_companion(book.companion_notes, payload)
