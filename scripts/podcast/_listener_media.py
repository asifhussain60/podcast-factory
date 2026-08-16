"""What FILES a book has, and which episode each one belongs to.

Split out of `_listener_book.py` on 2026-08-11, when the Sessions collection
added chapter illustrations and the module crossed its line-count gate — along
the seam its own header already named. That file answers "what does this book
SAY": how the reading edition splits into chapters, what an episode is called,
which chapter a note is filed against. This one answers "what does this book
HAVE": recordings, transcripts, the print edition, the cover, deck pages,
illustrations — and, for a recording, which episode it belongs to.

The seam is worth stating because it is where the judgment lives. Attaching a
file to an episode is a decision that can be WRONG, and wrongly on a religious
text: a recording under the wrong episode's title is worse than a missing one.
Everything here is therefore matched on signals that are either unambiguous or
absent — a leading number, a folder name the author typed — and never on a
similarity score.

Nothing here writes anywhere. `publish_to_listener.py` turns the result into
SQL, and `upload_listener_media.py` is what actually moves bytes.

It imports NOTHING from `_listener_book` at runtime. `Book` is needed only to
say what these functions take, so it arrives under TYPE_CHECKING — otherwise the
two modules would import each other and neither would load.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_decks import (  # noqa: E402
    BOOK_DECK,
    deck_dirs,
    deck_pages,
    deck_title,
)
from _transcript import vtt_path  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover - typing only
    from _listener_book import Book

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

# The subset of the above that is an IMAGE. Named rather than filtered inline,
# because the only other place a suffix set is used is a folder sweep, and
# sweeping `book/images/` for "anything with a known content type" would file a
# stray PDF as an illustration.
IMAGE_TYPES = frozenset({".png", ".jpg", ".jpeg", ".webp"})


def narration_object_name(anchor: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    return f"{safe or 'chapter'}.mp3"


@dataclass
class ChapterNarration:
    audio: Asset
    duration_s: float | None
    source_hash: str
    voice: str
    cues: list[dict]


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
    audio: Asset | None = None
    # The WebVTT of what is said, when it has been made. A separate asset rather
    # than a column on the episode, for the same reason the audio is: the row
    # says the file exists on disk, and only `uploaded_at` says it is servable.
    transcript: Asset | None = None
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
    # Deck pages only: which deck this page belongs to, and what to call it.
    # Both None for every other kind, and `deck_title` is None for a book-wide
    # deck, which needs no name because it is the only one on the page.
    deck_id: str | None = None
    deck_title: str | None = None

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

    # The timed transcript of this same episode, when one has been made. Keyed by
    # episode NUMBER like everything else, so it is found whatever the recording
    # was called — see `_transcript.vtt_path`. Absent is an ordinary state and
    # not an error: `ensure_transcripts.py` runs before publish and makes the
    # missing ones, and a book whose transcription failed still ships its audio.
    transcript = vtt_path(book.directory, episode.number)
    if transcript.is_file():
        episode.transcript = Asset(
            key=f"{book.slug}/transcript/ep{episode.number:02d}.vtt",
            slug=book.slug,
            kind="transcript",
            content_type="text/vtt",
            path=transcript,
        )
        book.assets.append(episode.transcript)

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

    # GROUPED, BUT UNGROUPED — recordings arranged into `Episodes/` with no session
    # folders at all. This is the right shape for a book below the session
    # threshold: four episodes do not want a lone "Session 1" heading over them,
    # and `_sessions.derive_sessions` returns nothing for such a book by design.
    #
    # Without this branch those files were seen by NEITHER of the two above: the
    # session scan collects only directories, and the loose scan below globs
    # `m4a/*` without recursing. Ayyuha al-Walad, arranged exactly as its size
    # calls for, attached zero recordings AND reported nothing unmatched — the
    # worst pair, because the audio disappeared without anything saying so.
    #
    # `session=None` is what makes it flat: the catalog puts sessionless episodes
    # in a titleless group the page renders as a plain list with no heading.
    if root.is_dir():
        best = {}
        seen_audio = False
        for path in sorted(root.iterdir()):
            # `Audio/` holds the untouched masters and is skipped here for the
            # same reason it is skipped above — the masters are not what ships.
            if path.is_dir() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in (".mp3", ".m4a"):
                continue
            seen_audio = True
            match = AUDIO_NUMBER_RE.match(path.stem)
            if match is None:
                book.unmatched_audio.append(f"{EPISODES_DIR}/{path.name}")
                continue
            n = int(match.group(1))
            if n not in best or path.suffix.lower() == ".mp3":
                best[n] = path

        for n in sorted(best):
            if not _attach_audio(book, best[n], session=None):
                book.unmatched_audio.append(f"{EPISODES_DIR}/{best[n].name}")

        # Only when this folder actually held recordings. An empty `Episodes/`
        # (or one holding nothing but `Audio/`) means the author has not arranged
        # anything yet, and the loose-file report below is the honest answer.
        if seen_audio:
            return

    for name in ("m4a", "audio"):
        folder = book.directory / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() not in (".m4a", ".mp3") or path.name.startswith("."):
                continue
            book.unmatched_audio.append(path.name)


def collect_reader_narration(book: Book) -> None:
    manifest = book.directory / "book" / "narration" / "manifest.json"
    if not manifest.exists():
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    chapters = data.get("chapters")
    if not isinstance(chapters, dict):
        return

    by_anchor = {chapter.anchor: chapter for chapter in book.chapters}
    root = manifest.parent
    for anchor, entry in chapters.items():
        if not isinstance(entry, dict) or anchor not in by_anchor:
            continue
        rel = str(entry.get("audio") or "")
        path = book.directory / rel if rel else root / f"{anchor}.mp3"
        if not path.exists() or path.suffix.lower() != ".mp3":
            continue
        # A chapter read aloud by the author is his EPISODE recording — the same
        # object the episode player already streams, already uploaded. So the
        # manifest may name a key that this book has collected already, and when
        # it does that asset is referenced rather than a second one created:
        # otherwise every Sessions chapter would put a duplicate of a fifty-
        # megabyte lecture in the bucket under a second name, and the two copies
        # could then disagree. A synthesised narration names no key and gets the
        # narration key it always got.
        wanted = str(entry.get("audio_key") or "")
        existing = next((a for a in book.assets if a.key == wanted), None) if wanted else None
        asset = existing or Asset(
            key=wanted or f"{book.slug}/narration/{narration_object_name(anchor)}",
            slug=book.slug,
            kind="audio",
            content_type=CONTENT_TYPES[".mp3"],
            path=path,
        )
        by_anchor[anchor].narration = ChapterNarration(
            audio=asset,
            duration_s=entry.get("duration_s") if isinstance(entry.get("duration_s"), (int, float)) else None,
            source_hash=str(entry.get("source_hash") or ""),
            voice=str(entry.get("voice") or entry.get("voice_id") or ""),
            cues=entry.get("cues") if isinstance(entry.get("cues"), list) else [],
        )
        if existing is None:
            book.assets.append(asset)


def collect_media(book: Book) -> None:
    """Inventory everything on disk: recordings, print edition, cover, deck."""
    directory = book.directory

    collect_audio(book)
    collect_reader_narration(book)

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

    # Illustrations the author placed INSIDE the prose — `book/images/<sid>/…`.
    #
    # Only the Sessions lane writes these today: a delivered lecture's stored
    # transcript carries the diagrams and scans Asif put on screen while
    # teaching, and several passages point at one. A book route that never puts
    # a file there simply finds nothing, so this needs no per-profile branch.
    #
    # The key keeps the on-disk shape under a `/image/` segment. That segment is
    # what stops a lecture's `213/page.jpg` from ever colliding with a deck's
    # `ch01/page-01.jpg` in the primary key — the same collision migration 0010
    # had to repair for decks, avoided here rather than discovered later.
    images = directory / "book" / "images"
    if images.is_dir():
        for image in sorted(p for p in images.rglob("*") if p.suffix.lower() in IMAGE_TYPES):
            book.assets.append(
                Asset(
                    key=f"{book.slug}/image/{image.relative_to(images).as_posix()}",
                    slug=book.slug,
                    kind="session-image",
                    content_type=CONTENT_TYPES[image.suffix.lower()],
                    path=image,
                )
            )

    # The slide decks — every one of them. The vocabulary and the reasoning live
    # in `_listener_decks`; this only turns what it finds into assets.
    for deck_dir in deck_dirs(directory):
        title = None if deck_dir.name == BOOK_DECK else deck_title(directory, deck_dir.name)
        for page in deck_pages(deck_dir):
            book.assets.append(
                Asset(
                    key=f"{book.slug}/deck/{deck_dir.name}/{page.name}",
                    slug=book.slug,
                    kind="deck-page",
                    content_type="image/jpeg",
                    path=page,
                    deck_id=deck_dir.name,
                    deck_title=title,
                )
            )
