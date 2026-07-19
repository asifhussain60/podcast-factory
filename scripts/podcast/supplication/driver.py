#!/usr/bin/env python3
"""driver.py — the supplication lane's entry point.

    python3 scripts/podcast/supplication/driver.py intake  <slug> --lang ar --pdf <file> [--title ...]
    python3 scripts/podcast/supplication/driver.py run     <slug>          # advance to the next halt
    python3 scripts/podcast/supplication/driver.py review  <slug>          # show the units for review
    python3 scripts/podcast/supplication/driver.py approve <slug>          # clear the review halt
    python3 scripts/podcast/supplication/driver.py verify  <slug>          # run the integrity gate alone
    python3 scripts/podcast/supplication/driver.py render  <slug>          # re-render the PDF alone
    python3 scripts/podcast/supplication/driver.py status  <slug>

`run` walks the step ledger and STOPS at the review halt. Translation spend only
happens after `approve`, so nobody pays to translate boundaries a person has not
looked at.

This driver is standalone. It does not import, call, or advance
orchestrate_book.py, and it never writes orchestrator-state.json.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _paths  # noqa: E402

from supplication import gates, intake, llm, ocr, render, state  # noqa: E402
from supplication.schema import (  # noqa: E402
    SourceRecord,
    SupplicationError,
    UnitsDoc,
    derive_source,
    refrain_units,
    validate_source_language,
)


def _book_dir(slug: str) -> Path:
    d = intake.content_root(slug)
    if not d.is_dir():
        raise SupplicationError(f"no supplication at {d} — run `intake {slug}` first.")
    return d


def units_path(book_dir: Path) -> Path:
    return book_dir / "units.json"


# ── commands ────────────────────────────────────────────────────────────────


def cmd_intake(args) -> int:
    meta = {k: v for k, v in (("type", args.type), ("attributed_to", args.attributed_to)) if v}
    book_dir = intake.run(
        args.slug,
        source_language=validate_source_language(args.lang),
        title_en=args.title or "",
        meta=meta,
        create_branch=not args.no_branch,
    )
    st = state.mark_done(book_dir, "intake")
    if args.pdf:
        src = Path(args.pdf).expanduser().resolve()
        dest = book_dir / "_system" / "source" / src.name
        dest.write_bytes(src.read_bytes())
        st = state.load(book_dir)
        st["source_pdf"] = str(dest.relative_to(book_dir))
        state.save(book_dir, st)
        print(f"  source PDF → {dest}")
    print(f"intake: {book_dir}  (branch {intake.branch_for(args.slug)})")
    print(f"next: {state.next_step(st)}")
    return 0


def cmd_run(args) -> int:
    book_dir = _book_dir(args.slug)
    while True:
        st = state.load(book_dir)
        step = state.next_step(st)
        if step is None:
            print("all steps complete.")
            return 0
        if step in state.HALT_STEPS:
            _do_review(book_dir, st)
            return 0
        print(f"\n── {step} ─────────────────────────────")
        try:
            state.mark_running(book_dir, step)
            _STEPS[step](book_dir, st)
            state.mark_done(book_dir, step)
        except SupplicationError as exc:
            state.mark_failed(book_dir, step, str(exc))
            print(f"\n{step}: FAILED\n{exc}", file=sys.stderr)
            return 1


def _step_ocr(book_dir: Path, st: dict) -> None:
    rel = st.get("source_pdf")
    if not rel:
        raise SupplicationError("no source PDF recorded — re-run intake with --pdf.")
    rec = ocr.run(
        book_dir,
        slug=st["slug"],
        source_language=st["source_language"],
        pdf_path=book_dir / rel,
    )
    print(f"  {len(rec.lines)} OCR lines across {rec.ocr.get('pages')} pages (digest {rec.digest[:12]}…)")


def _step_segment(book_dir: Path, st: dict) -> None:
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = llm.segment(rec, log=lambda m: print(m))
    # Gate the boundaries BEFORE the halt, so the human reviews a document that
    # is already known to cover the source exactly once and in order.
    gates.assert_ok(doc, rec, require_english=False)
    doc.write(units_path(book_dir))
    print(f"  {len(doc.units)} units → {units_path(book_dir)}")


def _step_translate(book_dir: Path, st: dict) -> None:
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    # Re-gate: the human may have edited boundaries during the halt.
    gates.assert_ok(doc, rec, require_english=False)
    doc = llm.translate(doc, rec, log=lambda m: print(m))
    doc.write(units_path(book_dir))


def _step_verify(book_dir: Path, st: dict) -> None:
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    rep = gates.assert_ok(doc, rec, require_english=True)
    print(rep.summary())


def _step_render(book_dir: Path, st: dict) -> None:
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    gates.assert_ok(doc, rec, require_english=True)
    out = render.run(book_dir, doc, rec)
    print(f"  wrote {out}")
    # FINAL STEP, as on every other PDF route. A supplication carries no glossary,
    # so the term-based lenses have nothing to track and the report comes back
    # empty — that is the honest result, not a gap. The sentence-length and
    # page-density lenses still apply, and wiring it here means a future
    # supplication that DOES carry a vocabulary is reviewed without a code change.
    _final_comprehension_review(book_dir, pdf=out)


def _final_comprehension_review(book_dir: Path, *, pdf: Path) -> None:
    """Reader-facing review over the finished PDF. Never raises, never blocks."""
    try:
        from _book_comprehension import run_comprehension_checks

        run_comprehension_checks(book_dir, log=lambda *a: print("   ", *a), pdf=pdf)
    except Exception as e:
        print(f"    comprehension: skipped (non-fatal): {e}")


def _step_deliver(book_dir: Path, st: dict) -> None:
    out = render.output_path(book_dir, st["slug"])
    if not out.is_file():
        raise SupplicationError(f"nothing to deliver — {out} does not exist.")
    print(f"  deliverable ready: {out}")
    print("  (PDF only — this lane produces no episodes, audio, slides, or video.)")


_STEPS = {
    "ocr": _step_ocr,
    "segment": _step_segment,
    "translate": _step_translate,
    "verify": _step_verify,
    "render": _step_render,
    "deliver": _step_deliver,
}


def _do_review(book_dir: Path, st: dict) -> None:
    state.mark_halted(
        book_dir,
        "review",
        "Merge/split units in units.json, then run `driver.py approve <slug>`.",
    )
    print("\n══ REVIEW HALT ══════════════════════════════════")
    print(f"Units are segmented but NOT translated. Review {units_path(book_dir)} before spending on translation.")
    print("  merge  → concatenate two units' line_ids into one")
    print("  split  → divide a unit's line_ids at any line boundary")
    print("  NOTE: the OCR line is the atom — you cannot split inside a line.")
    print(f"\n  driver.py review  {st['slug']}    # print the units")
    print(f"  driver.py approve {st['slug']}    # clear this halt and continue")


def cmd_review(args) -> int:
    book_dir = _book_dir(args.slug)
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    index = rec.by_id()
    # Derived, not stored — shows the human exactly which rows the PDF will tint.
    refrains = refrain_units(doc, rec)
    for u in doc.units:
        mark = " [refrain]" if u.n in refrains else ""
        print(f"\n{u.n}{mark}  ({', '.join(u.line_ids)})")
        print(f"  {derive_source(u.line_ids, index)}")
        if u.english:
            print(f"  EN: {u.english}")
    print(f"\n{len(doc.units)} units, {len(rec.lines)} OCR lines, {len(refrains)} refrain rows.")
    return 0


def cmd_approve(args) -> int:
    book_dir = _book_dir(args.slug)
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    # A human may have hand-edited units.json; re-prove integrity before letting
    # the run continue into paid translation.
    gates.assert_ok(doc, rec, require_english=False)
    # Renumber so unit numbers stay 1..N after merges and splits.
    for i, u in enumerate(doc.units, start=1):
        u.n = i
    doc.write(units_path(book_dir))
    state.clear_halt(book_dir)
    print(f"review approved — {len(doc.units)} units. Run `driver.py run {args.slug}` to continue.")
    return 0


def cmd_verify(args) -> int:
    book_dir = _book_dir(args.slug)
    rec = SourceRecord.read(ocr.record_path(book_dir))
    doc = UnitsDoc.read(units_path(book_dir))
    rep = gates.verify(doc, rec, require_english=args.require_english)
    print(rep.summary())
    return 0 if rep.passed else 1


def cmd_render(args) -> int:
    book_dir = _book_dir(args.slug)
    _step_render(book_dir, state.load(book_dir))
    return 0


def cmd_status(args) -> int:
    book_dir = _book_dir(args.slug)
    st = state.load(book_dir)
    print(f"slug            {st['slug']}")
    print(f"bucket          Supplications ({_paths.relative_to_repo(book_dir)})")
    print(f"branch          {intake.branch_for(st['slug'])}")
    print(f"source_language {st['source_language']}")
    print(f"step            {st['step']} ({st['step_status']})")
    print(f"completed       {', '.join(st.get('completed_steps') or []) or '—'}")
    if st.get("last_error"):
        print(f"last_error      {st['last_error']}")
    print(f"next            {state.next_step(st) or '—'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="supplication", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake", help="create the folder, branch, and config")
    p.add_argument("slug")
    p.add_argument("--lang", required=True, choices=["ar", "ur"], help="source script — never inferred")
    p.add_argument("--pdf", help="source PDF to copy in")
    p.add_argument("--title")
    p.add_argument("--type", help="e.g. Du'a / Ziyarat / Munajat")
    p.add_argument("--attributed-to")
    p.add_argument("--no-branch", action="store_true")
    p.set_defaults(fn=cmd_intake)

    for name, fn, helptext in (
        ("run", cmd_run, "advance to the next halt or completion"),
        ("review", cmd_review, "print the segmented units"),
        ("approve", cmd_approve, "clear the review halt"),
        ("render", cmd_render, "re-render the PDF"),
        ("status", cmd_status, "show the step ledger"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug")
        p.set_defaults(fn=fn)

    p = sub.add_parser("verify", help="run the integrity gate")
    p.add_argument("slug")
    p.add_argument("--no-english", dest="require_english", action="store_false", help="skip the translation check")
    p.set_defaults(fn=cmd_verify, require_english=True)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except SupplicationError as exc:
        print(f"\nsupplication: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
