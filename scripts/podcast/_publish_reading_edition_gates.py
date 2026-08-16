"""publish_to_library.py's G1/G5 gates, for a reading-edition-only book.

A reading-edition-only book (pipeline_mode="reading_edition_only" in
orchestrator-state.json) deliberately never produces a NotebookLM podcast: no
chapters/*.txt or episodes/*.txt upload bundle, no episode audio at all. Its
only deliverable is the reading edition (book/book.md -> book/book.pdf) plus
its Azure-TTS read-aloud narration (book/narration/manifest.json). G1
(structure), G2 (pairs), G3 (sequential numbering) and G4 (build-clean) are
ALL specifically about the podcast upload bundle, so forcing a podcast-less
book through them isn't a stricter check — it's a check of files that were
never going to exist. G2-G4 simply don't apply and are reported n/a by the
caller; this module supplies the two that need a real reading-edition-only
equivalent: G1 (does this book actually have finished content to publish) and
G5 (has the reading edition's own pipeline actually finished).

Split out of publish_to_library.py the same way _publish_sessions_gates.py
was — a self-contained question a caller can import rather than grow the gate
list in place. This is the one-step-further sibling of the Sessions lane:
Sessions books still ship real episode audio (m4a/Episodes/), just produced a
different way; a reading-edition-only book ships no episode audio at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def is_reading_edition_only(workspace: Path) -> bool:
    """True if this book's own state file declares the reading-edition-only lane."""
    state_path = workspace / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        return False
    try:
        return json.loads(state_path.read_text()).get("pipeline_mode") == "reading_edition_only"
    except (OSError, ValueError):
        return False


def gate_g1_reading_edition_structure(workspace: Path, *, fail, ok) -> tuple[bool, int]:
    """This lane's own proof of finished content: a composed book/book.md, a
    rendered PDF under book/ (0book-render renames book.pdf to the edition
    title, so any *.pdf counts), and a read-aloud narration manifest with at
    least one chapter. Returns (passed, chapter_count) — chapter_count
    substitutes for G1's normal episode count in the caller's catalog/log
    lines.
    """
    book_md = workspace / "book" / "book.md"
    book_dir = workspace / "book"
    manifest_path = book_dir / "narration" / "manifest.json"

    if not book_md.is_file() or not book_md.read_text(encoding="utf-8").strip():
        fail("G1", f"missing or empty book/book.md under {workspace}")
        return False, 0

    pdfs = sorted(book_dir.glob("*.pdf")) if book_dir.is_dir() else []
    if not pdfs:
        fail("G1", f"no rendered book/*.pdf under {workspace} — run 0book-render (build_book_pdf.py)")
        return False, 0

    if not manifest_path.is_file():
        fail("G1", f"no book/narration/manifest.json under {workspace} — no read-aloud narration")
        return False, 0
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as e:
        fail("G1", f"book/narration/manifest.json unreadable: {e}")
        return False, 0
    chapters = manifest.get("chapters") or []
    if not chapters:
        fail("G1", "book/narration/manifest.json has zero chapters")
        return False, 0

    ok("G1", f"reading-edition-only: book.md + {pdfs[0].name} + {len(chapters)} narrated chapter(s)")
    return True, len(chapters)


def gate_g5_reading_edition_state(workspace: Path, force: bool, *, fail, ok) -> bool:
    """This lane's own state checkpoint: the reading edition's own B1-B8 gate
    suite (validate_book_ready.validate_book) must report BOOK-SOUND — the
    lane's equivalent of the orchestrator's phase=done checkpoint, since this
    book never ran the orchestrator's per-chapter podcast convergence loop at
    all.
    """
    if force:
        ok("G5", "--force: state checkpoint skipped")
        return True

    import validate_book_ready as _vbr

    verdict = _vbr.validate_book(workspace)
    if verdict.get("verdict") == "BOOK-SOUND":
        ok("G5", f"validate_book_ready: {verdict.get('summary')}")
        return True
    fail(
        "G5",
        f"validate_book_ready verdict={verdict.get('verdict')!r} — {verdict.get('summary')}. "
        "Fix the reading edition, or use --force to bypass.",
    )
    return False
