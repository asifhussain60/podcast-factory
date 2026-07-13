"""Book Pipeline v2 — the single unified book-compose path.

Replaces the two divergent routes (faithful ``_translation_edition`` vs.
author-companion ``_book_compose``) with ONE path whose behaviour is set by two
orthogonal knobs (see ``_pipeline_flags``):

    faithful base  (always, from _system/source/text/refined-english.md)
      -> 0book-augment   [book_augmentation == source_only]  additive, gated
      -> 0book-voice     [book_voice == author_companion]    re-voice, gated
      -> book/book.md

Only reached when ``book_pipeline_v2_enabled(book_dir)`` is True. With the flag
OFF, ``phases/book_driver`` runs the untouched legacy dispatch, so today's output
is reproduced byte-for-byte.

The knob-default map (in ``_pipeline_flags``) makes flag ON + default config
reproduce the current *routing*: ``deliverable_mode: translation_edition`` ->
``{none, faithful}`` (base only, faithful voice); legacy companion ->
``{source_only, author_companion}`` (base + additive enrichment + author voice).
"""
from __future__ import annotations

from pathlib import Path

from _pipeline_flags import (
    BOOK_AUGMENTATION_SOURCE_ONLY,
    BOOK_VOICE_AUTHOR_COMPANION,
    BOOK_VOICE_FAITHFUL,
    book_augmentation,
    book_voice,
)


def compose_book_v2(book_dir: Path, *, log=print, force: bool = False) -> Path:
    """Run the unified base -> augment -> voice compose. Returns book/book.md.

    Each stage writes ``book/book.md`` in place; later stages read the previous
    stage's output, so the knobs compose cleanly and independently.
    """
    book_dir = Path(book_dir).resolve()
    augmentation = book_augmentation(book_dir)
    voice = book_voice(book_dir)
    log(f"    book-pipeline-v2: augmentation={augmentation} · voice={voice}")

    # 1. Faithful base — the shared foundation for BOTH modes. Reuse the
    #    translation-edition compose as the base, driven by knobs (not by the
    #    deliverable_mode contract), so there is exactly one faithful composer.
    from _translation_edition import author_translation_edition_compose  # noqa: PLC0415

    book_md = author_translation_edition_compose(
        book_dir, log=log, force=force, enforce_contract=False
    )

    # 2. Fluency de-calque over the FAITHFUL base (Phase 5). author_companion books
    #    get their fluency from the re-voice pass below, so this only runs for the
    #    faithful voice. Gated by the same fidelity checks; reverts per-chapter.
    if voice == BOOK_VOICE_FAITHFUL:
        from _book_voice import apply_fluency_adapt  # noqa: PLC0415

        book_md = apply_fluency_adapt(book_dir, log=log, force=force)

    # 3. Additive source-grounded enrichment (optional, gated, non-destructive).
    if augmentation == BOOK_AUGMENTATION_SOURCE_ONLY:
        from _book_augment import author_phase_book_augment  # noqa: PLC0415

        book_md = author_phase_book_augment(book_dir, log=log, force=force)

    # 4. Author-companion re-voice (optional, gated, reverts on drift).
    if voice == BOOK_VOICE_AUTHOR_COMPANION:
        from _book_voice import apply_author_companion_voice  # noqa: PLC0415

        book_md = apply_author_companion_voice(book_dir, log=log, force=force)

    return book_md
