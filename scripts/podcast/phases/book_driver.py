"""phases/book_driver.py — _drive_book_branch (PDF path).

Runs the companion-book phases (0book-design → 0book-compose → 0book-render)
AFTER the finalize halt, inside publish_driver._drive_publish_through_done.
This ensures the book is always generated from podcast content that has already
passed the finalize quality review gate — any issues fixed at review are already
resolved before the book branch runs. Gated on meta.yml `series.enable_book_branch`
(opt-in). NON-BLOCKING: a book-phase failure is recorded but never aborts the
podcast ship — the book is a companion deliverable, not a gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _authoring import AuthoringError
from _authoring._book_design import author_phase_book_design
from _authoring._core import AuthoringHalt
from _book_illustrate import author_phase_book_illustrate
from _progress import read_state, update_phase

from phases.scaffold import phase_git_commit

_BOOK_PHASES = ("0book-design", "0book-compose", "0book-illustrate", "0book-slide-import", "0book-render")


from _subprocess import err as _err
from _subprocess import info as _info


def _book_branch_enabled(book_dir: Path) -> bool:
    """Delegates — see ``_pipeline_flags.book_branch_enabled`` for the shape rules.

    This body used to be a verbatim copy of the one in ``validate_book_ready``,
    and both mis-read a ``series:`` that is a title string rather than a mapping.
    """
    from _pipeline_flags import book_branch_enabled

    return book_branch_enabled(book_dir)


def _drive_book_branch(book_dir: Path) -> int:
    """Wrapper that guarantees no phase is left pinned at "running".

    The body below sets a phase to "running" and catches only AuthoringError.
    Everything else it can raise — a JSONDecodeError on book-toc.json, an OSError,
    an ImportError from one of eleven lazy imports, a Ctrl-C — propagated with the
    state file frozen at "running" and no `last_error`. Recovery then had to wait
    out the 900-second staleness window before a resume would touch the book.
    That happened for real on 2026-07-21. Whatever escapes, the phase that was
    running is now recorded as failed, with the exception on it, before it goes up.
    """
    try:
        return _drive_book_branch_body(book_dir)
    except AuthoringError:
        raise  # the body's own handlers own these and have already recorded them
    except BaseException as e:
        try:
            state = read_state(Path(book_dir))
            for phase_id, rec in (state.get("phases") or {}).items():
                if (rec or {}).get("status") == "running":
                    update_phase(
                        Path(book_dir),
                        phase=phase_id,
                        status="failed",
                        error=f"{type(e).__name__}: {e}",
                    )
                    _err(f"{phase_id}: crashed ({type(e).__name__}: {e})")
        except Exception:  # never let the recorder mask the real exception
            pass
        raise


def _drive_book_branch_body(book_dir: Path) -> int:
    """Design → compose → illustrate → slide-import → render the companion book.

    Returns 0 (non-blocking — the podcast pipeline proceeds regardless of
    book-branch outcome) with ONE exception: returns 3 when 0book-slide-import
    raises AuthoringHalt (deck PDFs not yet dropped) — the caller must stop
    BEFORE publish so the human can finish the NotebookLM slide round and
    `--resume` (the upstream 0book phases are artifact-idempotent, so re-entry
    is effectively free)."""
    book_dir = Path(book_dir).resolve()
    slug = book_dir.name
    try:
        from _translation_edition import assert_translation_contract, is_translation_edition

        translation_edition = is_translation_edition(book_dir)
        if translation_edition:
            assert_translation_contract(book_dir)
    except AuthoringError:
        raise
    except Exception:
        translation_edition = False

    if not _book_branch_enabled(book_dir):
        # Record WHY, on every phase. A bare `skipped` is indistinguishable from
        # a phase skipped by design, and nothing downstream could tell the two
        # apart: on 2026-07-31 all five book phases were stamped skipped because
        # meta.yml simply had no `series` block, the run halted reporting 95%
        # complete, and an empty book/ looked like a successful pipeline.
        reason = "series.enable_book_branch is not set in meta.yml and the book is not a translation edition"
        for ph in _BOOK_PHASES:
            update_phase(book_dir, phase=ph, status="skipped", extras={"reason": reason, "skipped_by": "config"})
        _err(f"book branch: NO READING EDITION WILL BE BUILT — {reason}")
        _err(
            "  to enable: set `series.enable_book_branch: true` in meta.yml, or declare "
            "`deliverable_mode: translation_edition` in _system/series-config.yaml"
        )
        return 0

    # 0book-design
    update_phase(book_dir, phase="0book-design", status="running")
    try:
        author_phase_book_design(book_dir, log=_info)
    except AuthoringError as e:
        update_phase(
            book_dir, phase="0book-design", status="failed", error=str(e), extras={"manual_fallback": e.manual_fallback}
        )
        _err(f"0book-design failed (non-blocking): {e}")
        return 0
    update_phase(book_dir, phase="0book-design", status="completed")
    phase_git_commit(book_dir, f"book({slug}): 0book-design — book-toc.json")

    # 0book-compose
    #
    # The single unified compose path: a faithful base -> optional
    # source-grounded augment -> optional author re-voice, selected by the two
    # knobs (book_augmentation, book_voice). This is the only compose route.
    update_phase(book_dir, phase="0book-compose", status="running")
    try:
        from _compose_scope import apparatus_only_retry_advice

        _advice = apparatus_only_retry_advice(book_dir)
        if _advice:
            _err(f"WARNING: {_advice}")

        from _book_pipeline_v2 import compose_book_v2

        compose_book_v2(book_dir, log=_info)
    except AuthoringError as e:
        update_phase(
            book_dir,
            phase="0book-compose",
            status="failed",
            error=str(e),
            extras={"manual_fallback": e.manual_fallback},
        )
        _err(f"0book-compose failed (non-blocking): {e}")
        return 0
    except ValueError as e:
        # An unrecognised knob value in series-config.yaml. It SHOULD stop the book
        # — the config does not say which book to make — but it must stop it here,
        # the way every other book failure does. Uncaught it propagates through the
        # phase wrapper, out of publish_driver and into the orchestrator, aborting
        # the run after the entire podcast has already been produced. The book
        # branch is non-blocking for the podcast; a typo does not get to change that.
        update_phase(
            book_dir,
            phase="0book-compose",
            status="failed",
            error=str(e),
            extras={"manual_fallback": "Fix the knob value in _system/series-config.yaml, then re-run."},
        )
        _err(f"0book-compose failed (non-blocking): {e}")
        return 0
    update_phase(book_dir, phase="0book-compose", status="completed")
    phase_git_commit(book_dir, f"book({slug}): 0book-compose — unified path")

    # Visual policy. Under `book_visuals: manual_only` (the default for a companion
    # edition) the reading edition is a TEXT deliverable and its figures are chosen
    # by hand in the Book Composer. Both generating phases are skipped outright, so
    # no candidate asset is produced behind the curator's back — nothing to
    # accidentally place, nothing to review away later.
    from _pipeline_flags import BOOK_VISUALS_MANUAL_ONLY, book_visuals

    try:
        _visuals = book_visuals(book_dir)
    except ValueError as e:
        # Same containment as the compose knobs above: this value decides whether
        # the illustrate and slide-import phases run at all, so a typo must fail
        # the book lane visibly rather than escape into the orchestrator.
        update_phase(book_dir, phase="0book-compose", status="failed", error=str(e))
        _err(f"0book-visual-policy failed (non-blocking): {e}")
        return 0
    _manual_visuals = _visuals == BOOK_VISUALS_MANUAL_ONLY
    if _manual_visuals:
        _info("0book-illustrate/slide-import: skipped — book_visuals=manual_only (figures curated in the Composer)")
        for _p in ("0book-illustrate", "0book-slide-import"):
            update_phase(book_dir, phase=_p, status="skipped", extras={"reason": "book_visuals=manual_only"})

    # Both generating phases run ONLY when the book allows pipeline visuals.
    if not _manual_visuals:
        # 0book-illustrate: teaching diagrams -> book-illustrated.md (non-blocking on failure)
        update_phase(book_dir, phase="0book-illustrate", status="running")
        try:
            author_phase_book_illustrate(book_dir, log=_info)
        except AuthoringError as e:
            update_phase(
                book_dir,
                phase="0book-illustrate",
                status="failed",
                error=str(e),
                extras={"manual_fallback": e.manual_fallback},
            )
            _err(f"0book-illustrate failed (non-blocking): {e}")
            # Continue to render even without illustrations — book.md still renders fine.
        else:
            update_phase(book_dir, phase="0book-illustrate", status="completed")
            phase_git_commit(book_dir, f"book({slug}): 0book-illustrate — book-illustrated.md")

        # 0book-slide-import: NotebookLM deck PDFs -> book-slides.md.
        # Halts (return 3) when framed chapters lack their dropped PDFs; plain
        # failures are non-blocking (render proceeds from book-illustrated.md).
        update_phase(book_dir, phase="0book-slide-import", status="running")
        try:
            from _slide_import import author_phase_slide_import

            result = author_phase_slide_import(book_dir, log=_info)
        except AuthoringHalt as e:
            update_phase(
                book_dir,
                phase="0book-slide-import",
                status="halted",
                error=str(e),
                extras={"manual_fallback": e.manual_fallback},
            )
            _info("")
            _info("─" * 72)
            _info("0book-slide-import halted — NotebookLM slide decks not yet dropped.")
            _info(str(e))
            _info("")
            _info("Then re-run: python3 scripts/podcast/orchestrate_book.py --resume " + book_dir.name)
            _info("─" * 72)
            return 3
        except AuthoringError as e:
            update_phase(
                book_dir,
                phase="0book-slide-import",
                status="failed",
                error=str(e),
                extras={"manual_fallback": e.manual_fallback},
            )
            _err(f"0book-slide-import failed (non-blocking — rendering without slides): {e}")
        else:
            if result.get("skipped"):
                update_phase(
                    book_dir, phase="0book-slide-import", status="skipped", extras={"reason": result["skipped"]}
                )
            elif result.get("awaiting_layout"):
                # Visuals were emitted as candidates (book/visuals/index.json), not
                # injected. HALT before render so the human curates placement in the
                # Astro Book Composer (which writes visual-layout.json); a subsequent
                # resume / the Composer's Generate button renders the PDF.
                update_phase(
                    book_dir,
                    phase="0book-slide-import",
                    status="completed",
                    extras={
                        "imported": result.get("imported", {}),
                        "exempt": result.get("exempt", []),
                        "awaiting_layout": True,
                    },
                )
                phase_git_commit(book_dir, f"book({slug}): 0book-slide-import — visual candidates")
                update_phase(
                    book_dir,
                    phase="0book-render",
                    status="halted",
                    extras={
                        "reason": "awaiting-layout",
                        "manual_fallback": "Curate visuals in the Book Composer "
                        "(writes book/visual-layout.json), then Generate PDF / --resume.",
                    },
                )
                _info("")
                _info("─" * 72)
                _info("book branch halted — awaiting-layout. Visual candidates are in book/visuals/index.json.")
                _info("Curate placement in the Astro Book Composer, then Generate PDF.")
                _info("─" * 72)
                return 3
            else:
                update_phase(
                    book_dir,
                    phase="0book-slide-import",
                    status="completed",
                    extras={"imported": result.get("imported", {}), "exempt": result.get("exempt", [])},
                )
                phase_git_commit(book_dir, f"book({slug}): 0book-slide-import — book-slides.md")

    # 0book-render (PDF + reader HTML) — task 5 module; degrade gracefully until present.
    update_phase(book_dir, phase="0book-render", status="running")
    try:
        from build_book_pdf import build_book  # lazy: render module lands in task 5
    except ImportError:
        update_phase(
            book_dir, phase="0book-render", status="pending", error="render module (build_book_pdf) not yet available"
        )
        _info("0book-render: build_book_pdf pending — book.md ready, PDF deferred")
        return 0
    try:
        build_book(book_dir, log=_info)
    except (AuthoringError, RuntimeError) as e:
        update_phase(book_dir, phase="0book-render", status="failed", error=str(e))
        _err(f"0book-render failed (non-blocking): {e}")
        return 0

    # Deterministic render-quality probes over the RENDERED PDF (blank/half-empty
    # pages, NotebookLM watermark, duplicated caption). These back the
    # book-render-challenger agent and are recorded non-blocking.
    try:
        from _book_render_checks import run_render_checks

        _rc = run_render_checks(book_dir, log=_info)
        if _rc.get("findings"):
            _info(
                f"0book-render: render-checks {_rc.get('verdict')} — "
                f"{len(_rc['findings'])} finding(s); see _system/book-render-checks.json"
            )
    except Exception as e:
        _err(f"0book-render: render-checks skipped (non-fatal): {e}")

    # Deterministic post-render gate (B1-B3): the renderer only asserts the PDF
    # file was written — it never checks that book.md covers every TOC chapter or
    # that the PDF has a sane page count. Validate the deliverable here so a
    # truncated book or an empty PDF records an HONEST `failed` status (with the
    # reason) instead of silently `completed`. Still NON-BLOCKING for the podcast:
    # we return 0 either way — a broken reading edition must not stop the audio
    # from publishing — but the failure is now visible in state + surfaced loudly.
    try:
        from validate_book_ready import validate_book

        _bv = validate_book(book_dir)
    except Exception as e:
        # A crash in the gate is NOT a pass. It used to fall through to
        # `status="completed"` alongside a genuinely validated book, so the one
        # state field anybody reads could not tell "the deliverable is sound" from
        # "the check that would have told us blew up". Recorded as its own verdict,
        # which is neither.
        _err(f"0book-render: book-validation gate CRASHED — the deliverable is unverified: {e}")
        _bv = {"verdict": "UNKNOWN", "gates": [], "error": f"{type(e).__name__}: {e}"}

    # Written OUTSIDE the try, so the UNKNOWN verdict actually reaches disk. Inside
    # it, a crash left the PREVIOUS run's report in place — and `publish_driver`
    # reads that file to tell a human whether the reading edition is sound, so the
    # ship surface went on printing "SOUND" from a report about a different build.
    try:
        (book_dir / "_system" / "book-validation-report.json").write_text(
            __import__("json").dumps(_bv, indent=2), encoding="utf-8"
        )
    except Exception as e:  # a recorder must never become the failure it records
        _err(f"0book-render: could not write book-validation-report.json: {e}")

    if _bv.get("verdict") == "UNKNOWN":
        update_phase(
            book_dir,
            phase="0book-render",
            status="failed",
            error=f"deliverable unverified — validation gate crashed: {_bv.get('error')}",
            extras={"book_validation": _bv},
        )
        _err("0book-render: reading edition UNVERIFIED (non-blocking for podcast) — validation gate crashed")
        phase_git_commit(book_dir, f"book({slug}): 0book-render — book.pdf (validation crashed)")
        return 0

    if _bv.get("verdict") == "BOOK-BROKEN":
        update_phase(
            book_dir,
            phase="0book-render",
            status="failed",
            error=f"deliverable failed validation: {_bv.get('summary')}",
            extras={"book_validation": _bv},
        )
        _err(f"0book-render: reading edition FAILED validation (non-blocking for podcast) — {_bv.get('summary')}")
        phase_git_commit(book_dir, f"book({slug}): 0book-render — book.pdf (validation failed)")
        return 0

    # Companion cards are NOT authored here any more (Asif, 2026-08-02). They used
    # to be generated for every chapter at this point, which is how a book came out
    # of the pipeline carrying ~10-15 explanations per chapter that no human had
    # read — and the chapter lane stamped them `provider: "manual"`, which the site
    # renders as "You", so a machine's card wore the reader's name.
    #
    # The ordering reason this once cited (a card's `quote` must be verbatim against
    # the prose the reader actually sees) was never an argument for AUTOMATION, only
    # for running after the edition is final. The Composer's on-demand action reads
    # the same finished `book.md`, so it satisfies that constraint identically while
    # putting a human between the proposal and the page. See propose_companion.py.
    update_phase(book_dir, phase="0book-render", status="completed", extras={"book_validation": _bv})
    phase_git_commit(book_dir, f"book({slug}): 0book-render — book.pdf")
    return 0
