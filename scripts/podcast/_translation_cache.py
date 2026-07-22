"""_translation_cache.py — when a composed chapter chunk may be reused.

Extracted from ``_translation_edition`` so the freshness rule has one home and a
test of its own. It is the single highest-leverage correctness lever in the
compose chain: get it wrong in the permissive direction and the pipeline reports
"composed" while re-emitting prose written before the rule you just fixed.

That is exactly what happened. The original rule compared a chunk's mtime against
``refined-english.md`` alone. On the-master-and-the-disciple the source was from
June, the chunks from 19 July, and ``narrative_frame`` was locked on the 20th — so
every chunk looked fresh, every chapter hit cache on every run, and the shipping
prose had never been through the narrative-frame gate at all. A prompt fix, a rule
change or a new frame invalidated nothing.

The rule now: a chunk is reusable only if it is newer than EVERY input that
governs its wording — the source text, the book's own config, and the modules
that build the prompt and define the gates.
"""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent

# The modules whose content decides what a chapter says. A change to any of them
# means the cached prose was written under different instructions.
_GOVERNING_MODULES = (
    "_translation_prompts.py",
    "_narrative.py",
    "_translation_text.py",
)


def governing_inputs(book_dir: Path, refined_path: Path) -> list[Path]:
    """Every file whose mtime should invalidate a cached chunk."""
    return [
        refined_path,
        Path(book_dir) / "_system" / "series-config.yaml",
        *(_HERE / name for name in _GOVERNING_MODULES),
    ]


def cache_floor(book_dir: Path, refined_path: Path) -> float:
    """The mtime a chunk must beat to be reusable. Missing inputs are ignored —
    absence cannot make a cache staler than it is."""
    newest = 0.0
    for src in governing_inputs(book_dir, refined_path):
        try:
            newest = max(newest, src.stat().st_mtime)
        except OSError:
            continue
    return newest


def make_is_fresh(book_dir: Path, refined_path: Path):
    """Return `is_fresh(chunk_path) -> bool`, with the floor computed once."""
    floor = cache_floor(book_dir, refined_path)

    def is_fresh(path: Path) -> bool:
        try:
            return path.stat().st_mtime >= floor
        except OSError:
            return False

    return is_fresh
