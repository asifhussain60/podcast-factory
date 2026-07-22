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

import json
from pathlib import Path

from _pipeline_flags import (
    BOOK_AUGMENTATION_SOURCE_ONLY,
    BOOK_VOICE_AUTHOR_COMPANION,
    BOOK_VOICE_FAITHFUL,
    book_augmentation,
    book_voice,
)


# Every "non-fatal" step below is genuinely optional — a finished translation is
# worth more than an overlay — but a skip must never be INVISIBLE. Nine steps
# used to swallow their exception into a log line that scrolls away: a compose
# could return "completed" having dropped the transliteration fold, the inline
# Arabic, the spelling pass, the human's Composer edits and the introduction,
# with nothing in state and nothing in any report. Each skip is now also written
# to `_system/compose-skips.json`, which the ship gate and a human can both read.
def _record_skip(book_dir: Path, step: str, exc: BaseException, log) -> None:
    log(f"    {step}: skipped (non-fatal): {exc}")
    try:
        path = Path(book_dir) / "_system" / "compose-skips.json"
        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("skips", [])
            except Exception:
                existing = []
        existing.append({"step": step, "error": f"{type(exc).__name__}: {exc}"})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema": "book.compose-skips/v1", "skips": existing}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:  # a recorder must never become the failure it records
        pass


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
        # Stamped like every other stage. It was the one omission, and the worst
        # one to omit: for a faithful-voice book the fluency pass is the ONLY model
        # pass over the prose, so Arabic lost here showed up in the ledger as lost
        # "somewhere between base and final" with no stage to name.
        stages["fluency"] = stage_counts(book_dir)

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
    from _translation_edition import dedupe_seam_paragraphs, record_seam_removals

    final_md = book_dir / "book" / "book.md"
    if final_md.exists():
        # It deletes prose, so it reports what it deleted — see the docstring.
        _removed: list[dict] = []
        final_md.write_text(
            dedupe_seam_paragraphs(final_md.read_text(encoding="utf-8"), removed=_removed), encoding="utf-8"
        )
        book_md = final_md
        record_seam_removals(book_dir, "final", _removed, log)

    # 5a-replay. Replay durable Book Composer edits, and stamp the per-chapter
    #     fingerprints the Composer quotes back on its next save.
    #
    #     Since 2026-07-21 the model stages above SKIP any chapter carrying a
    #     Composer edit, so this is normally a confirming pass rather than a rescue.
    #     It stays because it is what makes the guarantee unconditional: under
    #     `--force`, and for any stage that grows a new path to book.md, the
    #     author's chapter is restored here and the overwrite is reported.
    #
    #     It runs BEFORE the deterministic house-style passes below, not after.
    #     After was wrong and cost the authored chapters their inline Arabic: the
    #     script pass ran, annotated the human's terms, and then the replay wrote
    #     the raw saved body back over the annotations, so exactly the chapters
    #     someone cared enough to author printed with no Arabic beside their terms
    #     — and gate B3 counts Arabic runs book-wide, so nothing noticed. Replaying
    #     first means transliteration, script, spelling and honorifics all see the
    #     final text, the author's chapters included, instead of a version of it.
    #     Idempotent and anchored by heading — see _book_edits.py.
    #
    #     The replay must also keep the pass reports honest (RCA-001): fluency
    #     and voice wrote "adapted" BEFORE this step, so a replayed edit landing
    #     on an adapted chapter — under `--force`, or from a save that arrived
    #     mid-run — makes that claim stale in the same compose that wrote it,
    #     and in July 2026 exactly that report waved 8 discarded chapters
    #     through every gate. The reconcile re-stamps those chapters
    #     'adapted-then-overwritten', and the discard is announced here, loudly,
    #     because it means model spend bought prose the book does not carry.
    from _book_edits import apply_composer_edits
    from _book_pass_reports import reconcile_reports_after_replay

    _replay_report = None
    try:
        _replay_report = apply_composer_edits(book_dir, log=log, force=force)
        book_md = book_dir / "book" / "book.md"
    except Exception as e:  # a bad sidecar must never destroy a good compose
        _record_skip(book_dir, "composer-edits", e, log)

    # The reconcile gets its OWN guard, deliberately not shared with the replay's.
    # Sharing one try block meant a reconcile failure was recorded as a
    # "composer-edits" skip — telling the operator their edits were dropped when
    # the replay had in fact applied them — while ALSO suppressing the discard
    # warning and leaving the stale "adapted" in place: the one failure mode this
    # step exists to end, hidden behind a false skip record.
    if _replay_report is not None:
        try:
            _discarded = reconcile_reports_after_replay(book_dir, _replay_report, log=log)
            if _discarded:
                log(
                    f"    WARNING: composer-edit replay DISCARDED adapted prose in {_discarded} chapter(s) — "
                    "the pass reports now read 'adapted-then-overwritten'; that model spend bought text "
                    "the book does not carry"
                )
        except Exception as e:  # a truth-teller must never fail the compose it describes
            _record_skip(book_dir, "report-reconcile", e, log)

    # 5a-translit. Fold scholarly transliteration to the plain house form, AFTER
    #     the model passes. The base composer already does this at the end of its
    #     own run (_translation_edition), but the fluency and augment passes come
    #     later and write whatever spelling they please — a rebuild on 2026-07-21
    #     came out of them carrying Shu'ayb, Ka'b, ta'wil, du'at and Ma'mur again,
    #     apostrophes and all. That is not only the wrong house style: the
    #     inline-Arabic pass below matches glossary terms against this text, so an
    #     un-folded "Bayt al-Ma'mur" silently matches nothing and the term loses
    #     its script. Folding here is what makes the two steps below reliable.
    from _translit import simplify_transliteration

    try:
        _md = book_dir / "book" / "book.md"
        if _md.exists():
            _before = _md.read_text(encoding="utf-8")
            _after = simplify_transliteration(_before)
            if _after != _before:
                _md.write_text(_after, encoding="utf-8")
                log("    translit: folded to plain transliteration")
    except Exception as e:  # never worth a finished translation
        _record_skip(book_dir, "translit", e, log)

    # 5a-policy. Classify the glossary's annotation policy — ONCE per book. Which
    #     terms deserve an inline annotation is a judgment call, so a model makes
    #     it, and it is durable: proposals land in glossary.yml where a human can
    #     override any line, and entries already carrying a class are never
    #     touched again, so this is a no-op (and zero cost) on every compose
    #     after the first. Per the learning-loop rule, suggestions are pre-applied
    #     and visible (_system/annotation-policy-report.json), never silent.
    from _annotation_policy import propose_annotation_policy

    try:
        propose_annotation_policy(book_dir, log=log)
    except Exception as e:  # a policy miss must never cost a finished book
        _record_skip(book_dir, "annotation-policy", e, log)

    # 5a-arabic. Put the Arabic script back beside inline terms. AFTER every
    #     LLM text pass, so no model can romanize the script away again, and AFTER
    #     the Composer replay, so it annotates the author's chapters too — before
    #     the replay it annotated them and the replay wrote the raw saved body back
    #     over its work. BEFORE the audits, so the Arabic audit judges exactly what
    #     prints. Deterministic and glossary-driven — no model, no cost, nothing
    #     recalled. See _book_inline_arabic.py.
    from _book_inline_arabic import apply_inline_arabic

    try:
        apply_inline_arabic(book_dir, log=lambda m: log(f"    {m}"))
        book_md = book_dir / "book" / "book.md"
    except Exception as e:  # an overlay is never worth a finished translation
        _record_skip(book_dir, "inline-arabic", e, log)

    # 5a-spelling. One spelling standard for the whole edition. The drafting and
    #     re-voicing models have no consistent preference, so without this a
    #     single book ships "honour" in one chapter and "honor" in the next.
    #     Deterministic, whole-word, and skips fenced blocks; source records under
    #     _system/source/ are never in scope here — this only touches book.md,
    #     which is prose the pipeline itself authored. See _american_spelling.py.
    from _american_spelling import to_american

    try:
        _md = book_dir / "book" / "book.md"
        if _md.exists():
            _before = _md.read_text(encoding="utf-8")
            _after = to_american(_before)
            if _after != _before:
                _md.write_text(_after, encoding="utf-8")
                log("    spelling: normalized to American forms")
    except Exception as e:  # a spelling pass is never worth a finished book
        _record_skip(book_dir, "spelling", e, log)

    # 5c. The edition's introduction. AFTER the Composer replay, so a human who
    #     rewrote the preface keeps their words and the introduction sits above
    #     them; BEFORE the audits, so what they judge is what will print. The
    #     source's own opening is untouched — it stays where the source put it,
    #     under a subheading, with the orientation in front of it.
    from _book_frontmatter import apply_introduction

    try:
        apply_introduction(book_dir, log=log, force=force)
    except Exception as e:  # apparatus is never worth a finished translation
        _record_skip(book_dir, "front-matter", e, log)

    # 6. Arabic provenance audit over the FINAL edition. The gates upstream count
    #    Arabic runs; this one asks whether each surviving run is the source's own
    #    words. Report-only and last, so it judges exactly what will be printed.
    from _book_arabic_audit import run_arabic_audit

    stages["final"] = stage_counts(book_dir)
    try:
        run_arabic_audit(book_dir, log=log, stages=stages)
    except Exception as e:  # never fail a good compose over its own audit
        _record_skip(book_dir, "arabic-audit", e, log)

    # 6b. Duplicated-passage sweep. The seam de-dup at step 5 drops a twin that
    #     sits NEXT to its original; this finds the one that does not — a window
    #     that ran past its own passage, so the whole scene prints twice several
    #     paragraphs apart, in different words. Report-only by design: on
    #     2026-07-20 each copy of such a pair turned out faithful where the other
    #     was wrong, with two source sentences missing from both, so deleting
    #     either automatically would have destroyed source text.
    from _translation_edition import duplicate_passage_findings

    try:
        dup_path = book_dir / "_system" / "book-duplication-check.json"
        dups = duplicate_passage_findings((book_dir / "book" / "book.md").read_text(encoding="utf-8"))
        dup_path.parent.mkdir(parents=True, exist_ok=True)
        dup_path.write_text(
            json.dumps(
                {"schema": "book.duplication-check/v1", "findings": dups},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if dups:
            log(f"    duplication: {len(dups)} passage(s) narrated twice — compare BOTH copies against the source")
            for d in dups[:3]:
                log(
                    f"      {d['chapter'][:48]}: paragraphs {d['first_copy_paragraphs']} vs {d['second_copy_paragraphs']}"
                )
    except Exception as e:  # never fail a good compose over its own audit
        _record_skip(book_dir, "duplication", e, log)

    # 7. Visual policy. Skipping the generating phases states the intent; this
    #    measures the artifact, because image markup can also reach book.md from a
    #    model mid-prose, which no phase toggle would catch.
    from _book_visual_policy import check_text_only

    try:
        check_text_only(book_dir, log=log)
    except Exception as e:
        _record_skip(book_dir, "visual-policy", e, log)

    # 8. Comprehension bridges — LAST, so a fix from a prior review round survives
    #    this compose. Idempotent (strips its own previous output first), so a
    #    convergence loop that re-enters compose many times never accumulates
    #    duplicate bridges. Read-only over the sidecar: only the reviewer writes it.
    from _book_bridges import apply_bridges

    try:
        apply_bridges(book_dir, log=log)
    except Exception as e:
        _record_skip(book_dir, "bridges", e, log)

    # 9. Honorifics — introduce each in full, then abbreviate. Genuinely LAST,
    #    after the introduction and the bridges, because "first use" is a property
    #    of the whole book AS THE READER MEETS IT and both of those are prose a
    #    reader reads. Run before them, an abbreviation in the introduction sat
    #    ahead of its own expansion — the exact confusion this pass exists to end.
    #    The Arabic audit above therefore counts the abbreviated form; that is the
    #    same limitation bridges already have, and both are report-only.
    #    Deterministic, book-scoped and idempotent; see _honorifics.py.
    from _honorifics import expand_first_honorific_use

    try:
        _md = book_dir / "book" / "book.md"
        if _md.exists():
            _before = _md.read_text(encoding="utf-8")
            _after, _n = expand_first_honorific_use(_before)
            if _n:
                _md.write_text(_after, encoding="utf-8")
                log(f"    honorifics: {_n} first-use honorific(s) spelled out in full")
    except Exception as e:  # a convention is never worth a finished book
        _record_skip(book_dir, "honorifics", e, log)

    return book_md
