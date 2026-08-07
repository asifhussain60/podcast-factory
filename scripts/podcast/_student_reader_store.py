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

import hashlib
import json
import re
from pathlib import Path
from typing import Any

#: Only ids matching this may be created or replaced here. `_student_reader.note_id`
#: is what mints them; the prefix is what makes ownership checkable at write time.
OWNED_ID_RE = re.compile(r"^student:[0-9a-f]{16}$")

CHAPTER_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

_KEY_STRIP_RE = re.compile(r"[^a-z0-9\s-]")
_KEY_HASH_RE = re.compile(r"^#{1,6}\s+")
_KEY_WS_RE = re.compile(r"\s+")


def section_key(heading: str) -> str:
    """The key a Companion note file is named for — MIRROR of
    ``companion/keys.ts sectionKeyFromHeading``.

    This is NOT ``_book_edits.anchor_key``, and the difference is the whole
    reason this function exists: ``anchor_key`` STRIPS a heading's ordinal
    ("the persian who was dead and revived") while the note files keep it
    ("1-the-persian-who-was-dead-and-revived"). ``book_chapters`` returns the
    former, the Composer writes the latter, and the two had never met because
    until 2026-08-06 nothing in Python wrote a note file — the Composer did, in
    TypeScript, with its own key.

    Getting this wrong does not raise anywhere useful: the note is written to a
    file the reader never opens, and a chapter silently shows nothing. It is
    caught here only because the traversal guard happens to reject a key with
    spaces in it.
    """
    text = _KEY_HASH_RE.sub("", str(heading or "")).lower()
    text = _KEY_STRIP_RE.sub("", text).strip()
    return _KEY_WS_RE.sub("-", text)[:80]


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


def prune_owned(existing: list[dict[str, Any]], keep_ids: set[str]) -> tuple[list[dict[str, Any]], int]:
    """Withdraw this pass's own UNREVIEWED notes that it no longer proposes.

    The narrowest possible removal, and every clause is load-bearing. A note is
    dropped only when all three are true: this pass owns its id, its `review` is
    not "kept", and it is not among the ids just proposed. So:

      * a note Asif accepted survives, always — accepting is his half of
        accept-or-delete and a pass must never undo it (the module docstring's
        rule, unchanged);
      * a note anyone or anything else wrote is untouchable here, exactly as in
        `merge_notes`;
      * the pass may only withdraw what it said itself and nobody has read.

    Reached ONLY from `--force`, which is the flag that means "read this chapter
    again from scratch". Without it a chapter is not re-read at all, so there is
    nothing to withdraw. Returns (kept, dropped-count).
    """
    kept: list[dict[str, Any]] = []
    dropped = 0
    for note in existing:
        nid = str(note.get("id") or "")
        if OWNED_ID_RE.match(nid) and note.get("review") != "kept" and nid not in keep_ids:
            dropped += 1
            continue
        kept.append(note)
    return kept, dropped


def owned_notes(book_dir: Path, chapter_key: str, slug: str) -> list[dict[str, Any]]:
    """This pass's own notes already filed for a chapter. Never anyone else's."""
    try:
        doc = read_doc(book_dir, chapter_key, slug)
    except Exception:
        return []
    return [n for n in doc.get("notes") or [] if OWNED_ID_RE.match(str(n.get("id") or ""))]


def prose_fingerprint(prose: str) -> str:
    """What the pass last read. Whitespace-folded, so reflow is not a change."""
    folded = " ".join(str(prose or "").split())
    return hashlib.sha256(folded.encode()).hexdigest()[:16]


def already_current(book_dir: Path, chapter_key: str, slug: str, prose: str) -> bool:
    """Has this pass already read this exact chapter?

    THE determinism guarantee, and it is not a nicety. Asked twice about the same
    prose, a model does not name the same passages: measured on chapter 2 of this
    book, a second run proposed two findings that did not overlap the first two
    at all, and since each anchors to a different sentence each minted a new id —
    the file went from two notes to four, and would have gone to six. Nothing in
    the merge is wrong; the input changed.

    So the pass does not ask twice. Unchanged prose that already carries this
    pass's notes is left exactly as it is, which makes a re-run byte-identical
    rather than merely non-duplicating. Edit the chapter and the fingerprint
    moves, and it is read again — which is the behaviour that matters, since the
    reason to re-run is that the prose changed.
    """
    try:
        doc = read_doc(book_dir, chapter_key, slug)
    except Exception:
        return False
    if doc.get("studentReaderFingerprint") != prose_fingerprint(prose):
        return False
    return any(OWNED_ID_RE.match(str(n.get("id") or "")) for n in doc.get("notes") or [])


def write_chapter(
    book_dir: Path,
    chapter_key: str,
    slug: str,
    notes: list[dict[str, Any]],
    *,
    now: str,
    fingerprint: str | None = None,
) -> Path:
    path = chapter_path(book_dir, chapter_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {"slug": slug, "chapter": chapter_key, "notes": notes, "updatedAt": now}
    if fingerprint:
        doc["studentReaderFingerprint"] = fingerprint
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def file_notes(
    book_dir: Path,
    chapter_key: str,
    slug: str,
    proposed: list[dict[str, Any]],
    *,
    now: str,
    prose: str | None = None,
    prune: bool = False,
) -> tuple[int, int, int]:
    """Merge and persist. Returns (created, refreshed, withdrawn)."""
    doc = read_doc(book_dir, chapter_key, slug)
    before = {str(n.get("id")) for n in doc["notes"] if n.get("id")}
    existing = doc["notes"]
    withdrawn = 0
    if prune:
        existing, withdrawn = prune_owned(existing, {str(n.get("id")) for n in proposed})
    merged = merge_notes(existing, proposed, now=now)
    created = sum(1 for n in proposed if str(n.get("id")) not in before)
    fp = prose_fingerprint(prose) if prose is not None else doc.get("studentReaderFingerprint")
    write_chapter(book_dir, chapter_key, slug, merged, now=now, fingerprint=fp)
    return created, len(proposed) - created, withdrawn
