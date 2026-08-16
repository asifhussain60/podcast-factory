"""What every pipeline step is CALLED, and how long it takes relative to the rest.

Split out of `book_status_card.py` on 2026-08-11, when the Sessions lane's own
steps pushed that module past its line-count gate. The seam is a real one: this
file is a dictionary and the card is an argument. Nothing here computes
anything, and nothing in the card names a step.

TWO LANES, ONE TABLE, and that is deliberate. The podcast orchestrator runs
twenty-nine phases; the Sessions lane runs five and shares almost none of them.
They are listed together because "how far along is this book" is ONE question,
and a book that answered it from a second table would be a second answer to it.
A lane whose steps were absent weighed 1 apiece and reported a finished book as
0% of a sequence it never runs — which is exactly what a Sessions book did until
its five entries were added.

The weights are deliberately coarse. The point is that the long phases dominate
the number the way they dominate the wait, not that any figure is precise.

The names are the only place the pipeline's internal ids are translated. The card
is read by a human, so it must never show one: a step called "0ci" tells a reader
nothing. The ids stay in the JSON, where machines read them.
"""

from __future__ import annotations

# Relative wall-clock weight per phase. A phase absent here weighs 1. These are
# deliberately coarse — the point is that the long phases dominate the number the
# way they dominate the wait, not that any single figure is precise.
_PHASE_WEIGHTS: dict[str, int] = {
    "pre-flight": 1,
    "branch": 1,
    "scaffold": 1,
    "0a": 6,
    "0b": 8,
    "0c": 4,
    "0ci": 4,
    "0d": 8,
    "0e": 8,
    "0literary": 4,
    "06a": 1,
    "0f": 1,
    "0g": 1,
    "per-chapter": 40,
    "per-chapter-optimize": 8,
    "per-chapter-slides": 12,
    "audio-script": 8,
    "audio-render": 8,
    "finalize": 2,
    "audio-ingest": 4,
    "0book-design": 3,
    "0book-compose": 20,
    "0book-illustrate": 6,
    "0book-slide-import": 4,
    "0book-render": 3,
    "publish": 1,
    "trainer": 2,
    "merge": 1,
    "done": 1,
    # The Sessions lane, which is a different and much shorter sequence — no
    # OCR, no chapter design, no NotebookLM. Its ids live in the same tables
    # rather than in a second card, because "how far along is this book" is one
    # question and a book that answered it from a different file would be a
    # second answer to it. A lane whose steps were absent here weighed 1 apiece
    # and reported a finished book as 0% of twenty-nine steps it never runs.
    "sessions-ingest": 2,
    "sessions-transcribe": 10,
    "sessions-articulate": 30,
    "sessions-read-along": 15,
    "sessions-preface": 2,
    "sessions-apparatus": 4,
}

# Plain-English name per phase. The card is read by a human, so it must never
# show the pipeline's internal ids — a step called "0ci" tells the reader nothing.
# The ids stay in the JSON, where machines read them.
_PHASE_NAMES: dict[str, str] = {
    "pre-flight": "Pre-flight checks",
    "branch": "Branch created",
    "scaffold": "Folders prepared",
    "0a": "Scanning and translating",
    "0b": "English refinement",
    "0c": "Arabic pronunciation",
    "0ci": "Source gap analysis",
    "0d": "Chapter design",
    "0e": "Enrichment",
    "0literary": "Literary pass",
    "06a": "Source review",
    "0f": "Series plan review",
    "0g": "Series registered",
    "per-chapter": "Writing each chapter",
    "per-chapter-optimize": "Chapter polish",
    "per-chapter-slides": "Slide decks",
    "audio-script": "Dialogue scripts",
    "audio-render": "Audio render",
    "finalize": "Quality review",
    "audio-ingest": "Audio ingest",
    "0book-design": "Book structure",
    "0book-compose": "Writing the book",
    "0book-illustrate": "Diagrams",
    "0book-slide-import": "Slide import",
    "0book-render": "Rendering the PDF",
    "publish": "Publishing",
    "trainer": "Learning pass",
    "merge": "Merging to develop",
    "done": "Done",
    "sessions-ingest": "Reading the session archive",
    "sessions-transcribe": "Transcribing the recordings",
    "sessions-articulate": "Refining the language",
    "sessions-read-along": "Timing the read-along",
    "sessions-preface": "Writing the introduction",
    "sessions-apparatus": "Arabic and citations",
}
