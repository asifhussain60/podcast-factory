"""Narrative frames — WHO narrates a book, and WHETHER the narration addresses anyone.

Split out of `_rules.py` on 2026-08-11 (DR-005). The registry and its three
resolvers are one coherent subject and they were the largest single topic left in
a 1,200-line rules module; adding a fifth frame pushed that file past its ratchet
ceiling, which is the size gate doing its job rather than an obstacle to route
around.

Everything here is RE-EXPORTED from `_rules`, so every existing
`from _rules import NARRATIVE_FRAMES` keeps working and no caller had to change.
`_rules` remains the front door for rule data; this is where this rule lives.
"""

from __future__ import annotations

from _content_types import CONTENT_TYPE_REGISTRY

# WHO NARRATES and WHETHER THE NARRATION ADDRESSES ANYONE are two questions, and
# `addresses_reader` is the second one (added 2026-08-11). Until then the lecture-voice
# and navigation guards keyed off `person`, which answered both at once — every
# first-person book was assumed to be a letter, so the guards fell silent and the
# prompt dropped its "a book addresses nobody" block. That is right for *Ayyuhal
# Walad*, where the address to the disciple IS the form. It is wrong for a lecture
# transcribed into a book: the speaker is genuinely "I", and every "you" and
# "notice this" is the room he was standing in, not the form of the work.
NARRATIVE_FRAMES: dict[str, dict[str, object]] = {
    "transmitted_report": {
        "label": "anonymous transmitted report",
        "person": "third",
        "narrator_is_character": False,
        "addresses_reader": False,
        "description": (
            "An unnamed transmitter reports what passed between other people "
            "('it has reached us that…'). Characters speak in first person only "
            "inside direct discourse. The default for classical Islamic prose."
        ),
    },
    "external_narrator": {
        "label": "external third-person narrator",
        "person": "third",
        "narrator_is_character": False,
        "addresses_reader": False,
        "description": "A narrator outside the story who never appears in it.",
    },
    "first_person_author": {
        "label": "first-person author addressing the reader",
        "person": "first",
        "narrator_is_character": False,
        "addresses_reader": True,
        "description": (
            "The author speaks as 'I' to the reader about the subject — a letter, "
            "a memoir, an epistle. Legitimate ONLY when the source does this."
        ),
    },
    "first_person_expository": {
        "label": "first-person author expounding, addressing nobody",
        "person": "first",
        "narrator_is_character": False,
        "addresses_reader": False,
        "description": (
            "The author speaks as 'I' about the subject and never turns to an "
            "audience. The frame for a delivered lecture becoming a book: the "
            "speaker's own voice is kept, the room he spoke it in is not. Contrast "
            "`first_person_author`, where the address to a reader is the form."
        ),
    },
    "participant_narrator": {
        "label": "first-person narrator who is also a character",
        "person": "first",
        "narrator_is_character": True,
        # True to preserve the behaviour this frame has always had, not because a
        # novel's narrator addresses a reader. No book declares it today; a fiction
        # book that adopts it and wants the guard should use the expository frame
        # or this value should be revisited with that book in hand.
        "addresses_reader": True,
        "description": (
            "A character narrates the events he took part in. Requires a single "
            "named participant for the WHOLE book, declared in narrator_subject."
        ),
    },
}

# Fallback when a book does not declare `narrative_frame`. Conservative on
# purpose: a translated classical text is third-person until proven otherwise,
# because inventing a narrator is unrecoverable while failing to invent one is not.
# DERIVED from CONTENT_TYPE_REGISTRY — a frame is a property of the content type,
# declared once beside its bucket. Profiles leaving it None fall through below.
PROFILE_DEFAULT_NARRATIVE_FRAME: dict[str, str] = {
    p: ct.narrative_frame for p, ct in CONTENT_TYPE_REGISTRY.items() if ct.narrative_frame
}
DEFAULT_NARRATIVE_FRAME: str = "external_narrator"


def narrative_frame_for(profile: str | None, declared: str | None = None) -> str:
    """Resolve a book's narrative frame: declared value wins, else profile default.

    An unknown declared frame falls back rather than raising — a typo in one
    book's config must not halt the pipeline, and the challenger reports it.
    """
    if declared and declared in NARRATIVE_FRAMES:
        return declared
    return PROFILE_DEFAULT_NARRATIVE_FRAME.get(profile or "", DEFAULT_NARRATIVE_FRAME)


def narrative_person_for(frame: str) -> str:
    """'first' or 'third' for a resolved frame name."""
    spec = NARRATIVE_FRAMES.get(frame) or NARRATIVE_FRAMES[DEFAULT_NARRATIVE_FRAME]
    return str(spec["person"])


def addresses_reader_for(frame: str) -> bool:
    """Whether this frame's form legitimately turns and speaks to a reader.

    The single predicate behind R-NO-LECTURE-VOICE and R-NO-NAVIGATION-APPARATUS:
    both the prompt that asks for the removal and the guards that police it read
    this, so they cannot disagree about which books are exempt. False means the
    narration expounds and never addresses — whatever person it expounds in.
    """
    spec = NARRATIVE_FRAMES.get(frame) or NARRATIVE_FRAMES[DEFAULT_NARRATIVE_FRAME]
    return bool(spec["addresses_reader"])
