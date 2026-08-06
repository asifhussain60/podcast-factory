"""_student_reader_store.py — file the lane's notes WITHOUT touching anyone else's.

This is the Python writer that docs/rca/2026-07-28-automation-deleted-companion-notes.md
is about. The predecessor regenerated every chapter and dropped each chapter's
prior generated notes on the way past, so a curated set was destroyed by a pass
that believed it was adding to it. The lesson taken then was to remove the writer
entirely; Asif has now asked for notes filed directly (2026-08-06), so the writer
comes back — under a rule that makes the old failure unreachable rather than
unlikely.

THE RULE: this module may only create or replace a note whose id it could have
minted itself — one carrying the `student:` prefix. Every other note in the file
is copied through untouched, and a note is never removed. It is not a flag and
not a code path; `merge_notes` cannot express the destructive operation, because
the only notes it writes are the ones handed to it plus the ones already there.

A note the pass no longer proposes is therefore LEFT IN PLACE rather than swept.
That is deliberate: Asif may have accepted it (`review: "kept"`), and a pass that
withdrew its own earlier findings would delete his acceptances. Deleting is his
half of accept-or-delete, and it stays his.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

#: Only ids matching this may be created or replaced here. `_student_reader.note_id`
#: is what mints them; the prefix is what makes ownership checkable at write time.
OWNED_ID_RE = re.compile(r"^student:[0-9a-f]{16}$")

CHAPTER_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def chapter_path(book_dir: Path, chapter_key: str) -> Path:
    if not CHAPTER_KEY_RE.match(chapter_key):
        raise ValueError(f"invalid chapter key: {chapter_key!r}")
    return Path(book_dir) / "_system" / "companion-notes" / f"{chapter_key}.json"


def read_doc(book_dir: Path, chapter_key: str, slug: str) -> dict[str, Any]:
    path = chapter_path(book_dir, chapter_key)
    if not path.exists():
        return {"slug": slug, "chapter": chapter_key, "notes": [], "updatedAt": None}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # An unreadable file is NOT an empty one. Returning {} here would let the
        # merge below write a fresh document over notes that are merely corrupt
        # to us — the exact shape of the 2026-07-28 loss.
        raise
    doc.setdefault("notes", [])
    return doc


def merge_notes(existing: list[dict[str, Any]], proposed: list[dict[str, Any]], *, now: str) -> list[dict[str, Any]]:
    """Existing notes, with this pass's own notes created or refreshed in place.

    Order is preserved for everything already on disk — a note the reader has
    scrolled to should not move because a pass ran. New notes append in the order
    proposed, which `select` has already put in reading order.

    Refreshing an owned note updates its body and keeps its `review`: if Asif
    accepted a finding, a re-run must not quietly set it back to "proposed" and
    ask him to accept it again.
    """
    by_id = {str(n.get("id")): i for i, n in enumerate(existing) if n.get("id")}
    out = [dict(n) for n in existing]

    for note in proposed:
        nid = str(note.get("id") or "")
        if not OWNED_ID_RE.match(nid):
            raise ValueError(f"refusing to write a note this pass does not own: {nid!r}")
        payload = dict(note)
        idx = by_id.get(nid)
        if idx is None:
            payload.setdefault("createdAt", now)
            payload["updatedAt"] = now
            out.append(payload)
        else:
            prior = out[idx]
            payload["createdAt"] = prior.get("createdAt", now)
            payload["updatedAt"] = now
            # His judgement survives a re-run; only the machine's own default is
            # overwritten by the machine.
            if prior.get("review") == "kept":
                payload["review"] = "kept"
            out[idx] = payload
    return out


def write_chapter(book_dir: Path, chapter_key: str, slug: str, notes: list[dict[str, Any]], *, now: str) -> Path:
    path = chapter_path(book_dir, chapter_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"slug": slug, "chapter": chapter_key, "notes": notes, "updatedAt": now}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def file_notes(
    book_dir: Path, chapter_key: str, slug: str, proposed: list[dict[str, Any]], *, now: str
) -> tuple[int, int]:
    """Merge and persist. Returns (created, refreshed)."""
    doc = read_doc(book_dir, chapter_key, slug)
    before = {str(n.get("id")) for n in doc["notes"] if n.get("id")}
    merged = merge_notes(doc["notes"], proposed, now=now)
    created = sum(1 for n in proposed if str(n.get("id")) not in before)
    write_chapter(book_dir, chapter_key, slug, merged, now=now)
    return created, len(proposed) - created
