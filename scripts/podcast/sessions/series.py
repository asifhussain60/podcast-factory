"""series.py — WHICH lectures the lane ingests, and the facts only a person knows.

Split out of `ingest.py` on 2026-08-11 when Surah Al-Fateha's entry pushed that
module past the DR-005 line cap. A real seam rather than an arbitrary cut, and the
distinction is worth stating because it decides where the next book's work goes:

  ingest.py     the DRIVER. One procedure, the same for every series, and nothing
                in it knows a lecture's name.
  series.py     the DATA. Five fields per series that a person had to author by
                reading the sessions, listening to the recordings, and deciding
                things no rule can decide — which file is which lecture, which
                stored title is a defect, which session is the speaker greeting a
                room rather than teaching.

The second is the expensive half, and it scales with RECORDINGS rather than with
books: five entries for Love Of The Prophet, twelve for Surah Al-Fateha, fifty-four
for Wise Reminder. Keeping it in its own file is what makes that visible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# The Drive mount holding the recordings and the session images. Anchored to the
# home directory and overridable, because an absolute path baked into pipeline
# source only works on the machine it was written on.
DRIVE_ROOT = Path(
    os.environ.get(
        "PODCAST_FACTORY_SESSIONS_ROOT",
        Path.home() / "Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com/My Drive/SESSIONS",
    )
)
AUDIO_ROOT = DRIVE_ROOT / "Quran Studies"
IMAGE_ROOT = DRIVE_ROOT / "Resources Images"

PROFILE = "islamic_session"


@dataclass(frozen=True)
class Series:
    group_id: int
    slug: str
    title: str
    # The series' name in Arabic, for the card's band — the same field every
    # book in this library fills, and the reason a Sessions card is shaped like
    # the rest of the grid rather than falling back to a Latin band with an
    # empty body beneath it.
    #
    # COINED, not recovered, and that is the honest description: these lectures
    # were delivered in English and titled in English, so there is no Arabic name
    # to find. Each one is the ordinary scholarly rendering of the English title
    # — `حُبُّ النَّبِيِّ` is precisely "love of the Prophet" — carried here as
    # data so it is reviewable beside the title it renders, never derived.
    #
    # Vowelled, per the standing rule: Asif does not read unvowelled Arabic, and
    # newly authored Arabic in this repo carries its marks.
    title_arabic: str
    audio_dir: str  # relative to AUDIO_ROOT
    audio_map: dict[str, int]  # audio filename -> session Sequence
    # Sessions whose stored transcript must be ignored in favour of the
    # recording's own transcription. Session 211 holds a 99.96% copy of session
    # 215, so publishing it verbatim would put a different lecture under its
    # title; the recording is the only witness to what was actually said.
    transcript_from_audio: frozenset[int] = field(default_factory=frozenset)
    # Chapter titles the database gets wrong, by sequence. Corrected HERE rather
    # than in book.md, because book.md is regenerated and a fix made downstream
    # of the generator is a fix that comes back. Every entry is a defect in the
    # stored name — a dropped letter, a sentence-cased title — never a retitling:
    # renaming a lecture Asif delivered is his call, not the lane's.
    title_fixes: dict[int, str] = field(default_factory=dict)
    # Sessions that are the speaker OPENING AN OCCASION rather than teaching: who
    # he is, why he runs these, greetings to the elders in the room, asking his
    # own teacher's permission to begin. Real, and rightly said aloud — but a
    # reader who opens the book meets it as chapter one and is told nothing about
    # what is in the book.
    #
    # These are not made into chapters. What stands in their place is the
    # edition's own introduction, authored by `_book_frontmatter` from this
    # book's chapter list under the same 250-word cap and the same voice every
    # other edition's introduction is written under (Asif, 2026-08-03). The
    # spoken opening is not lost: it is in the database it came from, and in this
    # repo's history.
    #
    # Declared per series rather than detected, because "this session is the
    # speaker introducing himself" is a judgement about content. A rule that
    # guessed it from the title would eventually drop a lecture called
    # "Introduction" that is the first teaching session of its series.
    preface_sessions: frozenset[int] = field(default_factory=frozenset)


SERIES: dict[str, Series] = {
    "love-of-the-prophet": Series(
        group_id=14,
        slug="love-of-the-prophet",
        title="Love Of The Prophet",
        title_arabic="حُبُّ النَّبِيِّ",
        audio_dir="Love Of The Prophet",  # the 2025/ re-delivery is deliberately excluded
        # Filenames exactly as they sit on disk, including the missing space in
        # "02cNeed" — the Drive API reports older titles for two of these, so a
        # map built from what the API says finds three of the five files.
        audio_map={
            "01 What is Love.mp3": 2,
            "02cNeed for Messengers.mp3": 3,
            "03 Islam as an experience.mp3": 4,
            "04 Character Of our prophet.mp3": 5,
            "05 Model For Success.mp3": 6,
        },
        transcript_from_audio=frozenset({2}),
        # Session 1 is Asif introducing himself and the series to the room.
        preface_sessions=frozenset({1}),
        title_fixes={
            3: "Need For Messengers",  # stored as "eed For Messengers"
            4: "Islam As An Experience",  # stored sentence-cased
            5: "Character Of The Prophet",  # stored sentence-cased
        },
    ),
    "surah-al-fateha": Series(
        group_id=11,
        slug="surah-al-fateha",
        title="Surah Al-Fateha",
        title_arabic="سُورَةُ الْفَاتِحَةِ",
        audio_dir="Surah Al-Fateha",
        # TWELVE RECORDINGS AGAINST TWENTY-THREE SESSIONS, and the eleven with no
        # recording are not a gap at the end — they are sessions 1-3 and 5-12,
        # the first month of the series. Asif began recording partway through.
        #
        # The leading numbers are the RECORDINGS' own count, not the sessions'.
        # `003` is session 14 and `007` is session 4, so anything reading the
        # filename as a sequence puts eleven of the twelve lectures under the
        # wrong title. The pairing below is by date first — eight of the twelve
        # match a session's `SessionDate` exactly — and by the title Asif typed
        # for the other four (`006 World Is The Womb Of Afterlife` against "The
        # Womb Of Afterlife"; `013 - Seeking Guidance Part 1` against "Guidance
        # To The Straight Path").
        #
        # Filenames exactly as they sit on disk, including the double space in
        # "judgment  - Linguistics".
        audio_map={
            "003 - Being vs attributes.mp3": 14,
            "004 - ISM.mp3": 15,
            "005 Complete BASMALLAH.mp3": 16,
            "006 World Is The Womb Of Afterlife.mp3": 13,
            "007 What is Worship.mp3": 4,
            "008 Perfection Of HAMD.mp3": 17,
            "009 REHMN RAHIM.mp3": 18,
            "010 King of day of judgment  - Linguistics.mp3": 19,
            "011 Motivating Factors For TAQWA.mp3": 20,
            "012 Worship and assistance.mp3": 21,
            "013 - Seeking Guidance Part 1.mp3": 22,
            "014 Resiliance.mp3": 23,
        },
        # NO SPOKEN OPENING, and that is a reading of the text rather than an
        # omission. Session 1 opens "In the flow of our conversation, we've
        # discussed the self in detail" — it is the middle of a longer course of
        # study, teaching from its first sentence, and it introduces neither the
        # speaker nor the occasion. The edition's own introduction is therefore
        # ADDED above chapter one rather than standing in place of anything,
        # which is what step 6c says to do when a series has no such session.
        preface_sessions=frozenset(),
        # None. Every stored name is a real title in reasonable case, and no two
        # transcripts are near-copies. Retitling a lecture Asif delivered is his
        # call, not the lane's, so the casing that varies between "What is
        # Worship?" and "Worship and Assistance" is left as he typed it.
        title_fixes={},
        transcript_from_audio=frozenset(),
    ),
}
