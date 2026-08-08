"""_book_reports.py — the compose apparatus's REPORT-ONLY tail.

Three steps that read the finished `book/book.md` and write a report beside it. None
of them alters the page, which is why they are the safe seam to lift out of
`_book_apparatus` (2026-08-08, when the DR-005 line cap forced a split and this was
the one group whose extraction could not change a printed book):

  arabic-audit    is every surviving Arabic run the source's own words
  duplication     which passages the edition narrates twice, several paragraphs apart
  visual-policy   did image markup reach a text-only edition

All three are classified ADVISORY in `_compose_skips`, so gate B8 reports them and
never blocks — a book does not lose its ship because its own audit failed. Their
relative order and their position in the sequence are preserved exactly: the caller
invokes this where `arabic-audit` used to sit.
"""

from __future__ import annotations

import json
from pathlib import Path

from _apparatus_steps import record_ok as _ok
from _book_arabic_audit import stage_counts
from _compose_skips import record_skip as _record_skip


def run_report_steps(book_dir: Path, *, log, stages: dict) -> None:
    """Run the three report-only steps over the finished book. Never raises.

    ``stages`` carries the per-stage Arabic counts the model passes stamped; this
    adds the FINAL count before the audit reads it, so the audit can name the stage a
    quotation went missing in.
    """
    # 6. Arabic provenance audit over the FINAL edition. The gates upstream count
    #    Arabic runs; this one asks whether each surviving run is the source's own
    #    words. Report-only and last, so it judges exactly what will be printed.
    from _book_arabic_audit import run_arabic_audit

    stages["final"] = stage_counts(book_dir)
    try:
        run_arabic_audit(book_dir, log=log, stages=stages)
        _ok(book_dir, "arabic-audit")
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
        _ok(book_dir, "duplication")
    except Exception as e:  # never fail a good compose over its own audit
        _record_skip(book_dir, "duplication", e, log)

    # 7. Visual policy. Skipping the generating phases states the intent; this
    #    measures the artifact, because image markup can also reach book.md from a
    #    model mid-prose, which no phase toggle would catch.
    from _book_visual_policy import check_text_only

    try:
        check_text_only(book_dir, log=log)
        _ok(book_dir, "visual-policy")
    except Exception as e:
        _record_skip(book_dir, "visual-policy", e, log)
