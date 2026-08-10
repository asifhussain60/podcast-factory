"""_compose_scope.py — decide whether a book-compose retry needs the model
passes (fluency/augment/voice) or only the deterministic apparatus tail.

Born from a real incident (spiritual-ethos, 2026-08-08): a glossary-only fix
(21 Arabic-script entries corrected in glossary.yml) was about to be folded
into book.md via a full `--retry-phase 0book-compose`, which re-runs the
fluency and source-only-augment model passes over all 15 chapters of an
English-source book to change Arabic annotations — annotations that
`apply_book_apparatus.py` alone injects from that same glossary.yml, in
seconds, with zero model calls over the prose. The apparatus/model split that
makes this possible already shipped 2026-08-02 (see `_book_apparatus.py`'s
module docstring); this module is the missing guard that would have caught
the mistake before a multi-hour recompose started.
"""

from __future__ import annotations

from pathlib import Path

# Every file whose change could make compose_book_v2's PROSE-GENERATING stages
# (base-translate, fluency, augment, voice) produce different prose.
# Deliberately excludes the apparatus tail's own inputs (glossary.yml, render
# templates, vowel/inline-arabic modules) — those are apply_book_apparatus.py's
# job and never require a model rewrite of the prose.
_MODEL_GOVERNING_MODULES = (
    "_translation_edition.py",
    "_translation_prompts.py",
    "_translation_text.py",
    "_book_voice.py",
    "_book_voice_prompts.py",
    "_book_augment.py",
    "_narrative.py",
)


_HERE = Path(__file__).resolve().parent


def _model_governing_inputs(book_dir: Path) -> list[Path]:
    book_dir = Path(book_dir)
    inputs = [
        book_dir / "_system" / "source" / "text" / "refined-english.md",
        book_dir / "_system" / "series-config.yaml",
    ]
    inputs += [_HERE / name for name in _MODEL_GOVERNING_MODULES]
    return inputs


def needs_model_recompose(book_dir: Path) -> bool:
    """True when compose_book_v2's model passes could change book.md's prose.

    False means book/book.md is at least as fresh as every input that governs
    what the model passes WRITE — so re-running them would only spend money to
    reproduce (or, worse, silently rephrase) prose that already reflects the
    current source and rules. In that state, an apparatus-only fix (Arabic
    script, vowelling, house style, a render template) belongs in
    `apply_book_apparatus.py`, not a full `--retry-phase 0book-compose`.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return True
    book_mtime = book_md.stat().st_mtime
    for src in _model_governing_inputs(book_dir):
        if src.exists() and src.stat().st_mtime > book_mtime:
            return True
    return False


def apparatus_only_retry_advice(book_dir: Path) -> str | None:
    """A human-readable warning when a compose retry looks apparatus-only,
    else None. Advisory only — never blocks a retry; see book_driver.py."""
    if needs_model_recompose(book_dir):
        return None
    slug = Path(book_dir).name
    return (
        "0book-compose: book/book.md is newer than every model-governing input "
        "(source text, voice/augment/narrative-frame modules, series-config.yaml). "
        "This retry will re-run the fluency/augment model passes over the whole "
        "book for no textual reason. If the only thing that changed is Arabic "
        "script, vowelling, house style, or a render template, run "
        f"`python3 scripts/podcast/apply_book_apparatus.py {slug}` instead — "
        "seconds, not hours, and zero model calls over the prose."
    )
