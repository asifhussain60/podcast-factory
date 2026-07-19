"""Book Pipeline v2 — the single unified book-compose path.

The one book-compose route, whose behaviour is set by two orthogonal knobs
(see ``_pipeline_flags``):

    faithful base  (always, from _system/source/text/refined-english.md)
      -> 0book-augment   [book_augmentation == source_only]  additive, gated
      -> 0book-voice     [book_voice == author_companion]    re-voice, gated
      -> book/book.md

The knob-default map (in ``_pipeline_flags``) selects each deliverable's
behaviour: ``deliverable_mode: translation_edition`` -> ``{none, faithful}``
(base only, faithful voice); companion book -> ``{source_only,
author_companion}`` (base + additive enrichment + author voice).
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
    from _translation_edition import author_translation_edition_compose

    book_md = author_translation_edition_compose(book_dir, log=log, force=force, enforce_contract=False)
    # Arabic quotations surviving each stage. The upstream gates each compare against
    # their own immediate input, so a quotation lost between stages is invisible to
    # all of them — the reader only sees the total at the end and cannot tell WHERE
    # it went. Stamping the count per chapter after every stage turns "it vanished
    # somewhere" into a named stage. Pure counting; costs nothing.
    from _book_arabic_audit import stage_counts

    stages = {"base": stage_counts(book_dir)}

    # 2. Fluency de-calque over the FAITHFUL base (Phase 5). author_companion books
    #    get their fluency from the re-voice pass below, so this only runs for the
    #    faithful voice. Gated by the same fidelity checks; reverts per-chapter.
    if voice == BOOK_VOICE_FAITHFUL:
        from _book_voice import apply_fluency_adapt

        book_md = apply_fluency_adapt(book_dir, log=log, force=force)

    # 3. Additive source-grounded enrichment (optional, gated, non-destructive).
    if augmentation == BOOK_AUGMENTATION_SOURCE_ONLY:
        from _book_augment import author_phase_book_augment

        book_md = author_phase_book_augment(book_dir, log=log, force=force)
        stages["augment"] = stage_counts(book_dir)

    # 4. Author-companion re-voice (optional, gated, reverts on drift).
    if voice == BOOK_VOICE_AUTHOR_COMPANION:
        from _book_voice import apply_author_companion_voice

        book_md = apply_author_companion_voice(book_dir, log=log, force=force)
        stages["voice"] = stage_counts(book_dir)

    # 5. Final seam de-dup over the fully-transformed book. The de-calque / re-voice
    #    passes above reword each copy of any surviving seam double-render
    #    differently, hiding them from the verbatim trimmer inside the base compose;
    #    this similarity-based pass runs LAST so it sees the final wording.
    from _translation_edition import dedupe_seam_paragraphs

    final_md = book_dir / "book" / "book.md"
    if final_md.exists():
        final_md.write_text(dedupe_seam_paragraphs(final_md.read_text(encoding="utf-8")), encoding="utf-8")
        book_md = final_md

    # 6. Arabic provenance audit over the FINAL edition. The gates upstream count
    #    Arabic runs; this one asks whether each surviving run is the source's own
    #    words. Report-only and last, so it judges exactly what will be printed.
    from _book_arabic_audit import run_arabic_audit

    stages["final"] = stage_counts(book_dir)
    try:
        run_arabic_audit(book_dir, log=log, stages=stages)
    except Exception as e:  # never fail a good compose over its own audit
        log(f"    arabic-audit: skipped (non-fatal): {e}")

    # 7. Visual policy. Skipping the generating phases states the intent; this
    #    measures the artifact, because image markup can also reach book.md from a
    #    model mid-prose, which no phase toggle would catch.
    from _book_visual_policy import check_text_only

    try:
        check_text_only(book_dir, log=log)
    except Exception as e:
        log(f"    visual-policy: skipped (non-fatal): {e}")

    # 8. Comprehension bridges — LAST, so a fix from a prior review round survives
    #    this compose. Idempotent (strips its own previous output first), so a
    #    convergence loop that re-enters compose many times never accumulates
    #    duplicate bridges. Read-only over the sidecar: only the reviewer writes it.
    from _book_bridges import apply_bridges

    try:
        apply_bridges(book_dir, log=log)
    except Exception as e:
        log(f"    bridges: skipped (non-fatal): {e}")

    return book_md
