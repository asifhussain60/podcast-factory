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

    # The Composer is the singular path for PDF-bound chapter changes, so a chapter
    # it has authored is not re-composed: every stage below consults this same set
    # and passes those chapters through. `--force` overrides it, and the warning is
    # not decoration — it is the only notice before a model rewrites human pages.
    from _book_edits import edited_chapter_keys

    _authored = edited_chapter_keys(book_dir)
    if _authored:
        if force:
            log(
                f"    book-pipeline-v2: FORCE — re-composing over {len(_authored)} "
                "Composer-authored chapter(s); the replay restores them and reports each as a conflict"
            )
        else:
            log(f"    book-pipeline-v2: {len(_authored)} Composer-authored chapter(s) will not be regenerated")

    # Both run-scoped records start empty, so each describes THIS compose rather
    # than every compose the book has ever had. `compose-skips.json` appended
    # forever until 2026-07-21, which meant a skip fixed three runs ago still read
    # as current — the opposite of what a "what went wrong this run" file is for.
    for _run_scoped in ("book-seam-dedup.json", "compose-skips.json"):
        (book_dir / "_system" / _run_scoped).unlink(missing_ok=True)

    # 1. Faithful base — the shared foundation for BOTH modes. Reuse the
    #    translation-edition compose as the base, driven by knobs (not by the
    #    deliverable_mode contract), so there is exactly one faithful composer.
    from _translation_edition import author_translation_edition_compose

    author_translation_edition_compose(book_dir, log=log, force=force, enforce_contract=False)
    # Arabic quotations surviving each stage. The upstream gates each compare against
    # their own immediate input, so a quotation lost between stages is invisible to
    # all of them — the reader only sees the total at the end and cannot tell WHERE
    # it went. Stamping the count per chapter after every stage turns "it vanished
    # somewhere" into a named stage. Pure counting; costs nothing.
    from _book_arabic_audit import stage_counts

    stages = {"base": stage_counts(book_dir)}

    # 1b. Chapter completeness — every chapter book-toc.json planned must have
    #     landed in book.md with real content, BEFORE the (expensive) articulation
    #     pass spends model time polishing a chapter that was never complete. The
    #     base-compose loop cannot silently DROP a planned chapter (see
    #     ``author_translation_edition_compose``'s docstring), but a compose retry
    #     that is still too short on its second attempt logs a warning and keeps
    #     going rather than raising — so a gutted chapter could reach book.md with
    #     nothing upstream having refused it. This is the check that closes that
    #     gap, and it HALTS: a confirmed missing or gutted chapter is not a
    #     heuristic guess the way the advisory coverage sweep above is.
    from _book_completeness import chapter_completeness_findings

    _toc_path = book_dir / "book" / "book-toc.json"
    _manifest_path = book_dir / "_system" / "translation-edition-manifest.json"
    if _toc_path.exists() and _manifest_path.exists():
        import json as _json

        _toc_chapters = _json.loads(_toc_path.read_text(encoding="utf-8")).get("chapters", [])
        _manifest_chapters = _json.loads(_manifest_path.read_text(encoding="utf-8")).get("chapters", [])
        _incomplete = chapter_completeness_findings(_toc_chapters, _manifest_chapters)
        if _incomplete:
            from _authoring._core import AuthoringError

            raise AuthoringError(
                phase="0book-compose",
                message="chapter completeness check failed: " + "; ".join(_incomplete[:4]),
                manual_fallback=(
                    "Re-run 0book-compose (base) with --force on the affected chapter(s), "
                    "or author the chapter directly in the Book Composer."
                ),
            )
        log(f"    0book-compose: chapter completeness — {len(_toc_chapters)} chapters verified against source")

    # 2. Fluency de-calque over the FAITHFUL base (Phase 5). author_companion books
    #    get their fluency from the re-voice pass below, so this only runs for the
    #    faithful voice. Gated by the same fidelity checks; reverts per-chapter.
    if voice == BOOK_VOICE_FAITHFUL:
        from _book_voice import apply_fluency_adapt

        apply_fluency_adapt(book_dir, log=log, force=force)
        # Stamped like every other stage. It was the one omission, and the worst
        # one to omit: for a faithful-voice book the fluency pass is the ONLY model
        # pass over the prose, so Arabic lost here showed up in the ledger as lost
        # "somewhere between base and final" with no stage to name.
        stages["fluency"] = stage_counts(book_dir)

    # 3. Additive source-grounded enrichment (optional, gated, non-destructive).
    if augmentation == BOOK_AUGMENTATION_SOURCE_ONLY:
        from _book_augment import author_phase_book_augment

        author_phase_book_augment(book_dir, log=log, force=force)
        stages["augment"] = stage_counts(book_dir)

    # 4. Author-companion re-voice (optional, gated, reverts on drift).
    if voice == BOOK_VOICE_AUTHOR_COMPANION:
        from _book_voice import apply_author_companion_voice

        apply_author_companion_voice(book_dir, log=log, force=force)
        stages["voice"] = stage_counts(book_dir)

    # 5. Final seam de-dup over the fully-transformed book. The de-calque / re-voice
    #    passes above reword each copy of any surviving seam double-render
    #    differently, hiding them from the verbatim trimmer inside the base compose;
    #    this similarity-based pass runs LAST so it sees the final wording.
    from _translation_edition import dedupe_seam_paragraphs, record_seam_removals

    final_md = book_dir / "book" / "book.md"
    if final_md.exists():
        # It deletes prose, so it reports what it deleted — see the docstring.
        _removed: list[dict] = []
        final_md.write_text(
            dedupe_seam_paragraphs(final_md.read_text(encoding="utf-8"), removed=_removed), encoding="utf-8"
        )
        record_seam_removals(book_dir, "final", _removed, log)

    # The deterministic tail — replay, house style, Arabic apparatus, audits,
    # bridges, honorifics, alignment. Lives in `_book_apparatus` so it can also be
    # run STANDALONE over a book already on disk, without the model passes above:
    # bringing an existing book's Arabic up to the current rules must not cost a
    # re-composition of its prose. One definition, two callers.
    from _book_apparatus import apply_book_apparatus

    return apply_book_apparatus(book_dir, log=log, force=force, stages=stages)
