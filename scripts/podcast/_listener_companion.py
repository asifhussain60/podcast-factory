"""The Ismaili Scholar Companion, read off disk and paired with its chapters.

Its own module for the reason `_listener_book.py` is its own module: that file
crossed the line-count gate, and the seam that was already there is this one. The
Companion is a whole concern — a second body of writing about the book, filed
under a key of its own — and nothing else in the read path needs to know it
exists.

Deliberately ignorant of `Book`. This module takes a directory and gives back
plain dictionaries, and takes plain dictionaries and gives back cards, so
`_listener_book` can import it without it importing back.

TWO KEYS, ONE CHAPTER
---------------------
The notes are filed under `sectionKeyFromHeading` — `## 3. The Boy at the Door`
becomes `3-the-boy-at-the-door…`, ORDINAL INCLUDED — and everything the Listener
stores is keyed by `anchor_key`, which strips that ordinal so a chapter survives
a re-compose that renumbers it. Both rules are right for their own job and they
are not interchangeable. Nothing here re-implements either: `attach_companion`
is handed the section key the RENDERER computed (see
`listener/scripts/render-chapters.mjs`) and only ever compares two strings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CompanionCard:
    """One Companion card, tied to a chapter of the reading edition."""

    anchor: str
    note_id: str
    idx: int
    title: str | None
    quote: str | None
    etymology: list[str]
    body_html: str = ""


def read_companion(book_dir: Path) -> dict[str, list[dict]]:
    """The cards as filed, keyed by the section key on the tin.

    One file per chapter at `_system/companion-notes/<section-key>.json`, written
    by the Book Composer's Scholar panel. Nothing is matched to a chapter here —
    that key is the renderer's rule, so the pairing waits until it can be asked.

    A file holding no usable note is dropped rather than carried: every book has
    a file per chapter whether or not anything was ever written in it, and an
    empty one is not a chapter whose notes went missing.
    """
    directory = book_dir / "_system" / "companion-notes"
    if not directory.is_dir():
        return {}

    filed: dict[str, list[dict]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"  ! {path.name} is not readable as JSON, skipped: {error}")
            continue

        notes = [
            note for note in (doc.get("notes") or []) if isinstance(note, dict) and str(note.get("body") or "").strip()
        ]
        if notes:
            filed[path.stem] = notes

    return filed


def cards_to_render(filed: dict[str, list[dict]]) -> list[dict]:
    """The note bodies as the renderer bridge wants them.

    A COMPOSITE id, because a note id only has to be unique within its own file,
    and this list is the whole book's.
    """
    return [
        {"id": f"{key}\x00{index}", "markdown": str(note.get("body") or "")}
        for key, notes in filed.items()
        for index, note in enumerate(notes)
    ]


def attach_companion(filed: dict[str, list[dict]], payload: dict) -> list[CompanionCard]:
    """Pair each filed note with its chapter, and report the ones that have none.

    A notes file whose section key matches no chapter of the edition is REPORTED
    and dropped, exactly as `read_bridge` reports an episode naming a chapter that
    does not exist. It is the ordinary consequence of renaming a chapter after
    writing notes against it, and the honest answer is to say so — filing them
    against the nearest-looking chapter would put an explanation on a passage it
    was not written for.
    """
    by_section = {
        chapter["section_key"]: chapter["anchor_key"] for chapter in payload["chapters"] if chapter.get("section_key")
    }
    bodies = {card["id"]: card["html"] for card in payload.get("cards", [])}

    cards: list[CompanionCard] = []
    for key, notes in filed.items():
        anchor = by_section.get(key)
        if anchor is None:
            print(
                f"  ! companion notes filed under '{key}' match no chapter of the edition ({len(notes)} not published)"
            )
            continue

        for index, note in enumerate(notes):
            etymology = [str(row).strip() for row in (note.get("etymology") or []) if str(row).strip()]
            cards.append(
                CompanionCard(
                    anchor=anchor,
                    note_id=str(note.get("id") or f"{key}-{index + 1}"),
                    idx=index + 1,
                    title=text_or_none(note.get("anchor")),
                    quote=text_or_none(note.get("quote")),
                    etymology=etymology,
                    body_html=bodies.get(f"{key}\x00{index}", ""),
                )
            )

    return cards


def text_or_none(value: object) -> str | None:
    """A trimmed string, or nothing at all — never an empty one to render."""
    text = str(value or "").strip()
    return text or None
