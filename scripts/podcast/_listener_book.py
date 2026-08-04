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

import hashlib
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
from _paths import find_content  # noqa: E402

LISTENER = Path(__file__).resolve().parents[2] / "listener"

# A heading that opens a chapter of the reading edition. `# ` is the book title
# and never a chapter; `### ` and deeper are sections inside one.
CHAPTER_HEADING_RE = re.compile(r"^##\s+(?!#)(.+?)\s*$")

# The leading episode/chapter number in an audio filename, whatever the file was
# called when it came out of NotebookLM: CH01.m4a, ep03-something.m4a, 2.m4a,
# EP-07-Air And The Instance Beyond Air.mp3.
AUDIO_NUMBER_RE = re.compile(r"^(?:ep|ch)?[\s_-]*0*(\d{1,3})\b", re.IGNORECASE)

# A session folder: `Session 2 — Spiritual Symbols: The Architecture of Creation`.
# Any of the three dashes, because which one a folder name carries depends on
# what typed it, and an em dash in a filename is not a thing to rely on.
SESSION_DIR_RE = re.compile(r"^Session\s+(\d{1,2})\s*[—–-]\s*(.+)$")

# Where a book's episode recordings live when they have been grouped. `Audio/`
# holds the untouched masters and is deliberately NOT uploaded — the mp3s in the
# session folders are what ship.
EPISODES_DIR = "Episodes"
MASTERS_DIR = "Audio"

CONTENT_TYPES = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


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

    @property
    def word_count(self) -> int:
        return len(self.markdown.split())


@dataclass
class Session:
    """A named run of episodes, exactly as the author's folder names declare it."""

    number: int
    title: str


@dataclass
class Episode:
    number: int
    title: str
    blurb: str | None
    style: str | None
    audio: "Asset | None" = None
    duration_s: int | None = None
    # None when this book's episodes were never grouped, which is most books.
    session: int | None = None


@dataclass
class Asset:
    key: str
    slug: str
    kind: str
    content_type: str
    path: Path

    @property
    def bytes(self) -> int:
        return self.path.stat().st_size

    @property
    def sha256(self) -> str:
        digest = hashlib.sha256()
        with self.path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        return digest.hexdigest()


@dataclass
class Book:
    slug: str
    bucket: str
    directory: Path
    title: str
    title_arabic: str | None
    blurb: str | None
    edition_note: str | None
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


def audio_duration(path: Path) -> int | None:
    """Seconds, via ffprobe. None when ffprobe is absent or the file is odd —
    a missing duration shows as a blank, which is better than a wrong one."""
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        ).stdout.strip()
        return int(float(out))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _attach_audio(book: Book, path: Path, *, session: int | None) -> bool:
    """Point one file at the episode its NUMBER names. False if there isn't one.

    Matching on the leading number is the one signal that is either present and
    unambiguous or absent. Anything cleverer — fuzzy title matching, ordering by
    modification time — would eventually attach the wrong recording to an
    episode, and a wrong recording on a religious text is worse than a missing
    one.
    """
    match = AUDIO_NUMBER_RE.match(path.stem)
    if match is None:
        return False

    number = int(match.group(1))
    episode = next((e for e in book.episodes if e.number == number), None)
    if episode is None:
        return False

    asset = Asset(
        key=f"{book.slug}/audio/ep{episode.number:02d}{path.suffix.lower()}",
        slug=book.slug,
        kind="audio",
        content_type=CONTENT_TYPES.get(path.suffix.lower(), "audio/mp4"),
        path=path,
    )
    episode.audio = asset
    episode.duration_s = audio_duration(path)
    episode.session = session
    book.assets.append(asset)
    return True


def collect_audio(book: Book) -> None:
    """Find the recordings, in whichever of the two layouts this book uses.

    GROUPED — `m4a/Episodes/`, holding `Audio/` with the untouched masters and
    one folder per session named `Session 2 — Spiritual Symbols: …`. Where this
    exists it is authoritative for both the audio and the grouping: the session
    number and title are read off the folder name, never inferred from episode
    counts or runtimes. The masters in `Audio/` are deliberately skipped — the
    mp3s are what the author prepared to ship, and re-encoding or shipping both
    would either lose quality or double the bucket.

    LOOSE — files sitting directly in `m4a/`. These are WORKING FILES and are
    deliberately not shipped. That folder is where raw NotebookLM output lands,
    under whatever name it was given (`CH01.m4a` beside
    `The_Imam_as_a_Law_of_Physics.m4a`), for a podcast that may be half-made —
    which is exactly the state Degrees of Excellence is in. Arranging recordings
    into session folders is the author's act of saying they are finished, so that
    is what publishing keys on. Loose files are reported, never guessed at, and
    never uploaded.
    """
    root = book.directory / "m4a" / EPISODES_DIR
    sessions = (
        sorted(
            (
                (int(m.group(1)), m.group(2).strip(), p)
                for p in root.iterdir()
                if p.is_dir()
                for m in [SESSION_DIR_RE.match(p.name)]
                if m
            ),
            key=lambda t: t[0],
        )
        if root.is_dir()
        else []
    )

    if sessions:
        for number, title, folder in sessions:
            book.sessions.append(Session(number=number, title=title))

            # One file per episode. An episode present as both mp3 and m4a takes
            # the mp3, because that is the encode the author made for the site.
            best: dict[int, Path] = {}
            for path in sorted(folder.iterdir()):
                if path.name.startswith(".") or path.suffix.lower() not in (".mp3", ".m4a"):
                    continue
                match = AUDIO_NUMBER_RE.match(path.stem)
                if match is None:
                    book.unmatched_audio.append(f"{folder.name}/{path.name}")
                    continue
                n = int(match.group(1))
                if n not in best or path.suffix.lower() == ".mp3":
                    best[n] = path

            for n in sorted(best):
                if not _attach_audio(book, best[n], session=number):
                    book.unmatched_audio.append(f"{folder.name}/{best[n].name}")
        return

    for name in ("m4a", "audio"):
        folder = book.directory / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() not in (".m4a", ".mp3") or path.name.startswith("."):
                continue
            book.unmatched_audio.append(path.name)


def collect_media(book: Book) -> None:
    """Inventory everything on disk: recordings, print edition, cover, deck."""
    directory = book.directory

    collect_audio(book)

    # The print edition. Named for the book rather than fixed, so glob it.
    pdfs = sorted((directory / "book").glob("*.pdf"))
    if pdfs:
        book.pdf = Asset(
            key=f"{book.slug}/book.pdf",
            slug=book.slug,
            kind="pdf",
            content_type="application/pdf",
            path=pdfs[0],
        )
        book.assets.append(book.pdf)

    for candidate in (directory / "book" / "cover.png", directory / "book" / "cover.jpg"):
        if candidate.exists():
            book.cover = Asset(
                key=f"{book.slug}/cover{candidate.suffix}",
                slug=book.slug,
                kind="cover",
                content_type=CONTENT_TYPES[candidate.suffix],
                path=candidate,
            )
            book.assets.append(book.cover)
            break

    pages = sorted((directory / "slide-decks" / "_pages" / "book").glob("page-*.jpg"))
    for page in pages:
        book.assets.append(
            Asset(
                key=f"{book.slug}/deck/{page.name}",
                slug=book.slug,
                kind="deck-page",
                content_type="image/jpeg",
                path=page,
            )
        )


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


def load_book(slug: str) -> Book:
    found = find_content(slug)
    if found is None:
        raise SystemExit(f"no content found for slug '{slug}'")

    # find_content returns (status, bucket, path). The status is deliberately
    # discarded: whether a unit is readable is the Listener's own `content_unit`
    # column, decided in the admin screens, and letting the pipeline's state file
    # drive it would put the privilege bit back under a script's control.
    _status, bucket, directory = found
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

    book = Book(
        slug=slug,
        bucket=bucket,
        directory=directory,
        title=str(meta.get("title") or slug),
        title_arabic=meta.get("title_arabic"),
        blurb=blurb,
        edition_note=edition_note,
        chapters=split_chapters(book_md_path.read_text(encoding="utf-8")),
        episodes=read_episodes(directory),
    )

    book.bridge = read_bridge(directory, book.chapters)
    book.companion_notes = read_companion(directory)
    collect_media(book)
    return book


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


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
    the one module that owns it and this side only ever compares two strings.
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
        input=json.dumps({"chapters": items, "cards": cards}),
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    rendered = {c["anchor_key"]: c["html"] for c in payload["chapters"]}
    for chapter in book.chapters:
        chapter.html = rendered[chapter.anchor]
    if book.blurb is not None:
        book.blurb = rendered["\x00blurb"]

    book.companion = attach_companion(book.companion_notes, payload)
