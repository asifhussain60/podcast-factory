"""Real sub-phase progress, read from what a running phase already writes to disk.

Split out of `book_status_card.py` on 2026-08-12 (DR-005). `_fraction_done` there
trusts a phase's status FLAG for the common case, but a flag is a single value
written once — sometimes hours apart from the work it claims to describe — and
two phases in this repo checkpoint their REAL progress on disk while that flag
sits at a flat "running" the whole time. Reading it is what turns "halfway
through the loop" into 50% instead of 0% until the phase flips, and it is what
caught the day this file exists to prevent: `sessions-articulate` once wrote
`completed` after keeping 2 of 23 chapters, and only a real per-chapter count
could tell the card the flag was wrong.
"""

from __future__ import annotations

from pathlib import Path

_CHUNK_DIR_PHASES = frozenset({"0b", "0d"})

#: `sessions-articulate` checkpoints per chapter in its own ledger, exactly like
#: 0b/0d checkpoint per chunk — same reason for a helper: the state file's status
#: field is a single flag written once at the end of a (possibly hours-long,
#: possibly interrupted) run, so trusting it alone reports a book stuck at
#: "running" as 50% underway whether it kept 1 chapter or 20 of 23.
_SESSIONS_ARTICULATE_PHASE = "sessions-articulate"


def sessions_articulate_fraction(phase: str, book_dir: Path | None) -> float | None:
    """Real per-chapter progress for the Sessions lane's articulation step, read
    from `_system/sessions-articulation.json` — the ledger `sessions/articulate.py`
    writes after every chapter, never a fabricated number.

    Imports the lane's own `chapter_keys` and `KEPT_STATUSES` rather than
    re-deriving "which chapters count" — a second definition of that question
    here would be a second answer, and the two would drift the moment the lane's
    introduction-skip rule or its kept/reverted vocabulary changed.

    Returns None when book_dir is unknown, this is not that phase, book.md
    does not exist yet, or the ledger has nothing to count — the caller falls
    back to whatever the flag alone would have said in every one of those cases.

    Deliberately UNCAPPED (unlike ``chunk_fraction``): the caller consults this
    from both its ``completed`` branch and its ``running`` branch, and only the
    running branch wants the "never show 100% before the flag says so" cap.
    Capping in here would freeze a genuinely finished phase (kept == total,
    this returns exactly 1.0) at 95% forever.
    """
    if book_dir is None or phase != _SESSIONS_ARTICULATE_PHASE:
        return None
    book_md = Path(book_dir) / "book" / "book.md"
    if not book_md.exists():
        return None
    try:
        from _book_pass_reports import KEPT_STATUSES
        from sessions.articulate import chapter_keys, read_ledger

        total = len(chapter_keys(book_md))
        if not total:
            return None
        kept = sum(1 for v in read_ledger(Path(book_dir))["chapters"].values() if v.get("status") in KEPT_STATUSES)
    except Exception:
        return None
    return kept / total


def _chunk_dir(phase: str, book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "source" / "text" / "_chunks" / phase


def _sc_total(chunks_dir: Path) -> int:
    """The expected 0d chunk count, from that run's own source-toc.json where
    present (authoritative — it lists every source chapter this run planned to
    design), else counted from the `.in.md` inputs already written."""
    manifest = chunks_dir / "source-toc.json"
    if manifest.exists():
        try:
            import json

            data = json.loads(manifest.read_text(encoding="utf-8"))
            chapters = data.get("source_chapters")
            if isinstance(chapters, list) and chapters:
                return len(chapters)
        except Exception:
            pass
    return len(list(chunks_dir.glob("sc-*.in.md")))


def chunk_fraction(phase: str, book_dir: Path | None) -> float | None:
    """Real sub-phase progress for phases that checkpoint per source-chunk on
    disk, read from files those phases already write — never a fabricated
    number. Two conventions exist today (scripts/podcast/_chunking.py owns the
    windowing one):

      * 0d writes `sc-NNN.done` markers per source chapter, with the expected
        total in that run's own `source-toc.json`.
      * 0b writes `win-NNN.in.md` / `win-NNN.out.md` pairs — a window counts as
        done the moment its `.out.md` exists (see _chunking.py's own doc
        comment: it skips windows whose `.out.md` already exists).

    Returns None — never a guess — when book_dir is unknown, the phase has no
    chunk directory (0c and 0e do not chunk this way today), or the directory
    has nothing to count yet. The caller falls back to the flat 0.5 guess in
    that case, exactly as it did before this existed.
    """
    if book_dir is None or phase not in _CHUNK_DIR_PHASES:
        return None
    chunks_dir = _chunk_dir(phase, book_dir)
    if not chunks_dir.is_dir():
        return None
    if phase == "0d":
        total = _sc_total(chunks_dir)
        if not total:
            return None
        done = len(list(chunks_dir.glob("sc-*.done")))
        return min(0.95, done / total)
    if phase == "0b":
        total = len(list(chunks_dir.glob("win-*.in.md")))
        if not total:
            return None
        done = len(list(chunks_dir.glob("win-*.out.md")))
        return min(0.95, done / total)
    return None
