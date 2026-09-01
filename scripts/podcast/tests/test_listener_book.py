#!/usr/bin/env python3
"""What the Listener actually ships, decided from what is on disk.

`_listener_book.collect_audio` and `collect_media` hold the judgment calls the
module's own docstring names — which recording belongs to which episode, which
files ship at all — and they had NO tests. They are also the side that WINS: the
folder names they read are what reach D1, while the derived sessions that could
have contradicted them are the well-tested half. The untested side deciding the
outcome is how a book went live under a lone "Session 4".

Everything here builds a book directory in a tmp_path and reads it back. No
network, no Azure, no database.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _listener_book import Book  # noqa: E402
from _listener_decks import deck_title  # noqa: E402
from _listener_media import (  # noqa: E402
    AUDIO_NUMBER_RE,
    SESSION_DIR_RE,
    collect_audio,
    collect_media,
)


def make_book(tmp_path: Path, *, episodes: int = 4) -> Book:
    """A book with `episodes` episodes and nothing on disk but the folder."""
    book = Book(
        slug="test-book",
        bucket="Islamic",
        directory=tmp_path,
        title="Test Book",
        title_arabic=None,
        title_language=None,
        study_track=None,
        blurb=None,
        edition_note=None,
    )
    from _listener_media import Episode

    for n in range(1, episodes + 1):
        book.episodes.append(Episode(number=n, title=f"Episode {n}", blurb=None, style=None))
    return book


def touch(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------------------
# The session folder name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dash", ["—", "–", "-"])
def test_session_dir_accepts_all_three_dashes(dash):
    """Which dash a folder carries depends on what typed it, and an em dash in a
    filename is not a thing to rely on."""
    m = SESSION_DIR_RE.match(f"Session 2 {dash} Spiritual Symbols")
    assert m is not None
    assert m.group(1) == "2"
    assert m.group(2) == "Spiritual Symbols"


def test_session_dir_ignores_a_folder_that_is_not_one():
    assert SESSION_DIR_RE.match("Audio") is None
    assert SESSION_DIR_RE.match("Session Two — Words") is None


# ---------------------------------------------------------------------------
# Which recording belongs to which episode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("EP-01-Three Thanks", 1),
        ("EP01 - Three Thanks", 1),
        ("ep03-something", 3),
        ("CH01", 1),
        ("07", 7),
        ("2", 2),
    ],
)
def test_audio_number_is_read_from_the_front(stem, expected):
    m = AUDIO_NUMBER_RE.match(stem)
    assert m is not None and int(m.group(1)) == expected


@pytest.mark.parametrize("stem", ["ch19c-the-conspiracy", "ep_003_something"])
def test_a_number_run_into_other_word_characters_is_not_read(stem):
    """Documenting a real edge, not asking for it to change.

    The pattern ends in `\b`, so a digit run followed by a letter or an
    underscore does not match: `ch19c` is the canonical CHAPTER stem used by the
    transcription lane, not a filename this ever sees, and the shapes that do
    reach it all separate the number with a dash or a space. Widening the pattern
    to swallow `ch19c` would make it read `19` out of names it has no business
    interpreting, which is the failure mode this whole matcher exists to avoid.
    """
    assert AUDIO_NUMBER_RE.match(stem) is None


def test_a_file_with_no_leading_number_is_never_guessed_at():
    """Matching on the leading number is the one signal that is either present and
    unambiguous or absent. A wrong recording on a religious text is worse than a
    missing one."""
    assert AUDIO_NUMBER_RE.match("The_Imam_as_a_Shadow_of_God") is None


# ---------------------------------------------------------------------------
# Grouped
# ---------------------------------------------------------------------------


def test_grouped_book_reads_its_sessions_off_the_folder_names(tmp_path):
    book = make_book(tmp_path, episodes=3)
    folder = tmp_path / "m4a" / "Episodes" / "Session 1 — The True Sources"
    for n in (1, 2, 3):
        touch(folder / f"EP-0{n}-Title.mp3")

    collect_audio(book)

    assert [(s.number, s.title) for s in book.sessions] == [(1, "The True Sources")]
    assert all(e.audio is not None and e.session == 1 for e in book.episodes)
    assert book.unmatched_audio == []


def test_masters_in_audio_are_never_shipped(tmp_path):
    """`Audio/` holds the untouched masters. Shipping them too would double the
    bucket for no gain."""
    book = make_book(tmp_path, episodes=1)
    touch(tmp_path / "m4a" / "Episodes" / "Audio" / "EP01 - Title.m4a")
    touch(tmp_path / "m4a" / "Episodes" / "Session 1 — Run" / "EP-01-Title.mp3")

    collect_audio(book)

    assert book.episodes[0].audio is not None
    assert book.episodes[0].audio.path.suffix == ".mp3"


def test_the_mp3_wins_when_a_book_ships_both(tmp_path):
    """The mp3 is the encode the author prepared for the site."""
    book = make_book(tmp_path, episodes=1)
    folder = tmp_path / "m4a" / "Episodes" / "Session 1 — Run"
    touch(folder / "EP-01-Title.m4a")
    touch(folder / "EP-01-Title.mp3")

    collect_audio(book)

    assert book.episodes[0].audio.path.suffix == ".mp3"


# ---------------------------------------------------------------------------
# Flat — the case that silently shipped nothing
# ---------------------------------------------------------------------------


def test_a_flat_book_ships_its_recordings(tmp_path):
    """Arranged into `Episodes/` with NO session folders, which is the right shape
    for a book under the session threshold.

    This is the regression: the session scan collects only directories and the
    loose scan does not recurse, so these files were seen by neither. Four
    recordings attached to nothing AND `unmatched_audio` empty — the audio
    disappeared with nothing saying so.
    """
    book = make_book(tmp_path, episodes=4)
    for n in range(1, 5):
        touch(tmp_path / "m4a" / "Episodes" / f"EP-0{n}-Title.m4a")

    collect_audio(book)

    assert [e.audio is not None for e in book.episodes] == [True] * 4
    assert book.unmatched_audio == []
    assert book.sessions == [], "a flat book declares no sessions"
    assert all(e.session is None for e in book.episodes)


def test_a_flat_book_still_skips_the_masters_folder(tmp_path):
    book = make_book(tmp_path, episodes=1)
    touch(tmp_path / "m4a" / "Episodes" / "Audio" / "EP01 - Title.m4a")
    touch(tmp_path / "m4a" / "Episodes" / "EP-01-Title.m4a")

    collect_audio(book)

    assert book.episodes[0].audio.path.parent.name == "Episodes"


def test_an_unnumbered_file_in_episodes_is_reported_not_dropped(tmp_path):
    book = make_book(tmp_path, episodes=1)
    touch(tmp_path / "m4a" / "Episodes" / "EP-01-Title.m4a")
    touch(tmp_path / "m4a" / "Episodes" / "Some Stray Recording.m4a")

    collect_audio(book)

    assert book.unmatched_audio == ["Episodes/Some Stray Recording.m4a"]


def test_an_empty_episodes_folder_falls_through_to_the_loose_report(tmp_path):
    """`Episodes/` holding nothing means the author has not arranged anything yet,
    and the loose files are the honest answer."""
    book = make_book(tmp_path, episodes=1)
    (tmp_path / "m4a" / "Episodes").mkdir(parents=True)
    touch(tmp_path / "m4a" / "Raw_NotebookLM_Export.m4a")

    collect_audio(book)

    assert book.episodes[0].audio is None
    assert book.unmatched_audio == ["Raw_NotebookLM_Export.m4a"]


# ---------------------------------------------------------------------------
# Loose — working files, never shipped
# ---------------------------------------------------------------------------


def test_loose_files_are_reported_and_never_shipped(tmp_path):
    """`m4a/` is where raw NotebookLM output lands for a podcast that may be
    half-made. Arranging them is the author's act of saying it is finished."""
    book = make_book(tmp_path, episodes=2)
    touch(tmp_path / "m4a" / "CH01.m4a")
    touch(tmp_path / "m4a" / "The_Imam_as_a_Law_of_Physics.m4a")

    collect_audio(book)

    assert all(e.audio is None for e in book.episodes)
    assert sorted(book.unmatched_audio) == ["CH01.m4a", "The_Imam_as_a_Law_of_Physics.m4a"]


# ---------------------------------------------------------------------------
# Decks
# ---------------------------------------------------------------------------


def test_every_deck_is_collected_not_only_a_book_wide_one(tmp_path):
    """The pipeline's default is per-chapter and always was. Looking only in
    `_pages/book/` found nothing at all for a book with chapter decks."""
    book = make_book(tmp_path, episodes=0)
    for ch, pages in (("ch01", 2), ("ch02", 3)):
        for p in range(1, pages + 1):
            touch(tmp_path / "slide-decks" / "_pages" / ch / f"page-0{p}.jpg")

    collect_media(book)

    decks = {a.deck_id for a in book.assets if a.kind == "deck-page"}
    assert decks == {"ch01", "ch02"}


def test_deck_pages_from_different_decks_get_different_keys(tmp_path):
    """`media_asset.key` is the PRIMARY KEY. Under the old flat key every deck's
    `page-01.jpg` collided and all but one deck's pages vanished on insert."""
    book = make_book(tmp_path, episodes=0)
    for ch in ("ch01", "ch02"):
        touch(tmp_path / "slide-decks" / "_pages" / ch / "page-01.jpg")

    collect_media(book)

    keys = [a.key for a in book.assets if a.kind == "deck-page"]
    assert len(keys) == len(set(keys)) == 2


def test_a_deck_is_named_from_its_source_heading(tmp_path):
    (tmp_path / "slide-decks").mkdir(parents=True)
    (tmp_path / "slide-decks" / "ch01-deck-knowledge.txt").write_text(
        "# Knowledge Without Action\n\nSlide one.\n", encoding="utf-8"
    )
    assert deck_title(tmp_path, "ch01") == "Knowledge Without Action"


def test_a_deck_with_no_source_has_no_name_rather_than_a_guessed_one(tmp_path):
    """Deck folders are numbered against the PODCAST chapter set, which for
    several books is a different segmentation from the reading edition. Naming a
    deck from the reading chapter of the same ordinal would file it under a
    confidently wrong title."""
    (tmp_path / "slide-decks").mkdir(parents=True)
    assert deck_title(tmp_path, "ch01") is None


# ---------------------------------------------------------------------------
# An audiobook has no chapter contracts, and used to publish with no episodes.
# ---------------------------------------------------------------------------


def _audiobook(tmp_path):
    (tmp_path / "_system").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_system" / "audiobook-chapters.json").write_text(
        json.dumps(
            {
                "schema": "podcast.audiobook-chapters/v1",
                "chapters": [
                    {"episode": 1, "file": "m4a/Episodes/ep01.m4a", "title": "01_Work_OpeningCredits"},
                    {"episode": 2, "file": "m4a/Episodes/ep02.m4a", "title": "02_Work_FirstNight"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_an_audiobook_gets_episodes_from_its_own_record(tmp_path):
    """White Nights dry-ran as nine chapters and ZERO episodes on 2026-09-01:
    `read_episodes` derives from `chapter-contracts/*.yml`, which is the PODCAST
    lane's authored record, and an audiobook has none. It would have published as
    text with no audio, and silently — nothing errored, the count read 0."""
    from _listener_book import read_episodes

    episodes = read_episodes(_audiobook(tmp_path))
    assert [e.number for e in episodes] == [1, 2]
    assert [e.blurb for e in episodes] == [None, None]
    assert [e.style for e in episodes] == [None, None]


def test_the_readers_title_comes_from_the_bridge_not_the_source_filename(tmp_path):
    """`02_Work_FirstNight` is provenance. The bridge already names the chapter
    each episode belongs to, and that name is what a reader should see."""
    from _listener_book import read_episodes

    book = _audiobook(tmp_path)
    (book / "_system" / "listener-episode-chapters.json").write_text(
        json.dumps({"1": ["Opening Credits"], "2": ["First Night"]}), encoding="utf-8"
    )
    assert [e.title for e in read_episodes(book)] == ["Opening Credits", "First Night"]


def test_without_a_bridge_the_filename_stem_is_used_rather_than_a_guess(tmp_path):
    from _listener_book import read_episodes

    assert [e.title for e in read_episodes(_audiobook(tmp_path))] == [
        "01_Work_OpeningCredits",
        "02_Work_FirstNight",
    ]


def test_a_book_with_contracts_is_untouched_by_the_fallback(tmp_path):
    """The fallback fires only where there are no contracts, so the podcast lane
    keeps deriving episodes exactly as it did."""
    from _listener_book import read_episodes

    book = _audiobook(tmp_path)
    (book / "chapter-contracts").mkdir()
    (book / "chapter-contracts" / "ch01.yml").write_text(
        "episode_number: 7\ntitle: From the contract\n", encoding="utf-8"
    )
    episodes = read_episodes(book)
    assert [(e.number, e.title) for e in episodes] == [(7, "From the contract")]


def test_a_book_with_neither_has_no_episodes_and_does_not_raise(tmp_path):
    from _listener_book import read_episodes

    (tmp_path / "_system").mkdir(parents=True)
    assert read_episodes(tmp_path) == []


# ---------------------------------------------------------------------------
# Every card prints a credit, and it prints one that fits.
# ---------------------------------------------------------------------------


def test_a_book_with_no_author_is_credited_anonymous_not_left_blank():
    """The card is a jacket and a jacket always prints a credit, so the absence
    of a name is answered here rather than by a rule in the template."""
    from _listener_book import ANONYMOUS, credit

    assert credit({}) == (ANONYMOUS, ANONYMOUS)
    assert credit({"author": "   "}) == (ANONYMOUS, ANONYMOUS)


def test_the_alias_is_what_a_card_prints_and_the_full_name_survives():
    from _listener_book import credit

    assert credit({"author": "Hamid al-Din Ahmad ibn Abdullah al-Kirmani", "author_short": "Al-Kirmani"}) == (
        "Hamid al-Din Ahmad ibn Abdullah al-Kirmani",
        "Al-Kirmani",
    )


def test_without_an_alias_the_full_name_is_used_rather_than_being_shortened():
    """Never derived. Shortening an Arabic name by rule means guessing which part
    is the surname, and Arabic names do not have one."""
    from _listener_book import credit

    assert credit({"author": "Asif Hussain"}) == ("Asif Hussain", "Asif Hussain")
