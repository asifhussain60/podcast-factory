"""_book_arabic_audit.py — per-chapter Arabic provenance audit for ``book/book.md``.

The book lane could measure Arabic in two places and neither watched the finished
edition: ``_arabic_coverage`` gates a compose *window* before chapters exist, and
``_book_voice`` counts runs per chapter and reverts a re-voice that dropped some.
Both are COUNT tests against the immediately-preceding text. Neither asks the
question a printed edition actually lives or dies by:

    is each Arabic run on this page the source's own words, or the model's recall?

A count test cannot see that. A verse can survive every gate, be counted at every
step, and still have been re-spelled, truncated, or supplied from memory. This
module answers the identity question instead, per chapter, by folding each run to
its consonantal skeleton (``_arabic_coverage.normalize_arabic``) and looking for
it in the immutable OCR of the source pages, then in the knowledge base's own
Arabic. What neither can account for is reported as ``unverified`` — never
silently accepted, and never auto-corrected: restoring a verse is a judgment call
that belongs to a human with a source in hand, not to a compose pass.

Pure and deterministic — no LLM, no network, no mutation. It reads text and
returns findings; the caller decides what to do with them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _arabic_coverage import arabic_run_spans, arabic_span_is_grounded, normalize_arabic
from _mushaf import is_quranic_sequence, mushaf_reference_label

# Resolution ladder, strongest provenance first. ``ocr`` means the run is the
# source's own words. ``knowledge-base`` means it is not in THIS book's pages but
# is a verse/saying the corpus already carries verbatim from elsewhere — weaker,
# because the edition is then quoting something its own source did not print.
RESOLUTION_MUSHAF = "canonical-mushaf"
RESOLUTION_OCR = "ocr"
RESOLUTION_KB = "knowledge-base"
RESOLUTION_HONORIFIC = "honorific-formula"
RESOLUTION_UNVERIFIED = "unverified"

# Standard Islamic honorific formulas ("peace be upon him/her/them", "may God be
# pleased with him", etc.) are the AUTHOR's own liturgical practice, not a quoted
# source — they need no grounding in the OCR or the knowledge base any more than
# an English writer's "may he rest in peace" needs a citation. Left ungrounded,
# every one of these read as "unverified" alongside a genuine mis-sourced verse,
# burying the real finding in liturgical boilerplate. Found live 2026-07-19: one
# of the-master-and-the-disciple's four "unverified" runs was exactly this — a
# false positive in the tool, not a problem with the book. Matched by normalized
# skeleton, same fold as everywhere else in this module, so spelling/diacritic
# variants of the same formula are recognized identically.
_HONORIFIC_FORMULAS = frozenset(
    normalize_arabic(f)
    for f in (
        "عليه السلام",
        "عليها السلام",
        "عليهم السلام",
        "عليهما السلام",
        "رضي الله عنه",
        "رضي الله عنها",
        "رضي الله عنهم",
        "صلى الله عليه وآله وسلم",
        "صلى الله عليه وسلم",
        "سبحانه وتعالى",
        "عز وجل",
        "جل جلاله",
    )
)

_CHAPTER_HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
# Editorial asides are additive companion prose, not source text. Their Arabic is
# audited under the same rule (it must be copied from the corpus), so they are
# left in — this constant exists to name the intent, not to exclude them.
_KB_FILES = ("quran.jsonl", "hadith.jsonl", "quote.jsonl", "doctrine.jsonl", "etymology.jsonl")


def _kb_arabic_corpus(kb_root: Path) -> str:
    """Every Arabic string the knowledge base carries, concatenated for matching."""
    parts: list[str] = []
    for name in _KB_FILES:
        path = kb_root / name
        if not path.exists():
            continue
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                body = json.loads(raw).get("body")
                if not isinstance(body, dict):
                    continue
                for key in ("arabic", "text_ar", "root"):
                    value = body.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value)
        except Exception:
            continue
    return "\n".join(parts)


def split_chapters(book_md: str) -> list[tuple[str, str]]:
    """``book.md`` as (heading, body) pairs; text before the first ``##`` is front matter."""
    matches = list(_CHAPTER_HEADING_RE.finditer(book_md))
    if not matches:
        return [("(whole book)", book_md)]
    out: list[tuple[str, str]] = []
    head = book_md[: matches[0].start()].strip()
    if head:
        out.append(("(front matter)", head))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(book_md)
        out.append((m.group(1).strip(), book_md[m.end() : end]))
    return out


def audit_book_arabic(book_md: str, arabic_src: str, kb_arabic: str = "") -> dict[str, Any]:
    """Per-chapter provenance of every Arabic run in a composed edition.

    Returns ``{"chapters": [...], "totals": {...}}``. Each chapter lists its runs
    with a ``resolution`` from the ladder above; ``unverified`` runs carry their
    text so a human can check them against a source without re-deriving anything.
    """
    chapters: list[dict[str, Any]] = []
    totals = {
        RESOLUTION_MUSHAF: 0,
        RESOLUTION_OCR: 0,
        RESOLUTION_KB: 0,
        RESOLUTION_HONORIFIC: 0,
        RESOLUTION_UNVERIFIED: 0,
    }
    for title, body in split_chapters(book_md):
        runs: list[dict[str, str]] = []
        for span in arabic_run_spans(body):
            # Canonical FIRST: a Quranic verse is verified against the mushaf, never
            # against the OCR (the scan can carry an OCR error; the mushaf cannot).
            # The corpus is content/knowledge-base/mirror.db, tracked in git.
            #
            # `_sequence`, because a display quotation is very often SEVERAL ayat
            # run together with their numbers between them, and the single-verse
            # check can never match across two of them. See its docstring for why
            # the promotion is unanimous.
            if is_quranic_sequence(span):
                resolution = RESOLUTION_MUSHAF
            elif arabic_span_is_grounded(span, arabic_src):
                resolution = RESOLUTION_OCR
            elif kb_arabic and arabic_span_is_grounded(span, kb_arabic):
                resolution = RESOLUTION_KB
            elif normalize_arabic(span) in _HONORIFIC_FORMULAS:
                resolution = RESOLUTION_HONORIFIC
            else:
                resolution = RESOLUTION_UNVERIFIED
            totals[resolution] += 1
            run: dict[str, str] = {
                "text": span,
                "resolution": resolution,
                "skeleton": normalize_arabic(span)[:40],
            }
            # WHICH ayah, not merely whether. The reading edition prints a Qur'an
            # card headed by its chapter and verse and has no card without one
            # (Asif, 2026-08-09), so the matcher's answer is recorded here instead
            # of being recomputed at render time in a second language. Every one of
            # the 497 mushaf-resolved runs across the seven books answers, so this
            # is not a best-effort field — an empty one means the ladder and the
            # reference lookup have drifted apart and is worth investigating.
            if resolution == RESOLUTION_MUSHAF:
                label = mushaf_reference_label(span)
                if label:
                    run["reference"] = label
            runs.append(run)
        chapters.append(
            {
                "chapter": title,
                "arabic_runs": len(runs),
                "unverified": sum(1 for r in runs if r["resolution"] == RESOLUTION_UNVERIFIED),
                "runs": runs,
            }
        )
    # EVERY resolution tier, mushaf included. Omitting the canonical-Quran tier
    # made the headline number a lie: the-master-and-the-disciple reported 31
    # Arabic runs against 54 actually present, so the audit read as if a third of
    # the book's Arabic had gone missing.
    totals["arabic_runs"] = sum(
        totals[k]
        for k in (
            RESOLUTION_MUSHAF,
            RESOLUTION_OCR,
            RESOLUTION_KB,
            RESOLUTION_HONORIFIC,
            RESOLUTION_UNVERIFIED,
        )
    )
    return {"schema": "book.arabic-audit/v1", "chapters": chapters, "totals": totals}


def stage_counts(book_dir: Path) -> dict[str, int]:
    """Arabic quotations per chapter in ``book.md`` right now — one compose stage's mark.

    Each upstream gate compares against its own immediate input, so a quotation
    lost BETWEEN stages is invisible to every one of them. Marking the count after
    each stage is what makes a loss attributable instead of merely total.
    """
    book_md = Path(book_dir) / "book" / "book.md"
    if not book_md.exists():
        return {}
    return {title: len(arabic_run_spans(body)) for title, body in split_chapters(book_md.read_text(encoding="utf-8"))}


def stage_losses(stages: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """Where Arabic quotations disappeared: (chapter, stage, before -> after)."""
    names = list(stages)
    losses: list[dict[str, Any]] = []
    for earlier, later in zip(names, names[1:]):
        before, after = stages[earlier], stages[later]
        for chapter, count in before.items():
            now = after.get(chapter, 0)
            if now < count:
                losses.append({"chapter": chapter, "stage": later, "before": count, "after": now})
    return losses


def provenance_drift(book_dir: Path) -> list[tuple[str, str]]:
    """(chapter, run) where the stored record disagrees with the page about scripture.

    The record is written by a COMPOSE and read at RENDER time, and between those
    two moments the book can be edited — by the Composer, by ``compose_fix.py``, by
    anything. Nothing has ever checked that it still describes the text it is
    filed beside, and on 2026-08-09 every one of the seven books had drifted: runs
    the record still listed had been edited out days earlier.

    Only the SCRIPTURE question is reported, because that is the only part of the
    answer anything acts on — the Arabic face, the Arabic ink, the card a
    quotation is drawn in and the face of its English rendering all key off
    `canonical-mushaf` and nothing keys off the difference between `ocr` and
    `knowledge-base`. A run the page no longer carries is silence rather than a
    finding: it costs nothing at render time, where the set is matched by exact
    text.

    A SCRIPTURE RUN THAT CANNOT NAME ITSELF IS ALSO DRIFT (2026-08-09). The
    edition prints a Qur'an card headed by its chapter and verse and has no card
    without one, so a stored run filed as scripture with no `reference` describes
    the page less completely than the page now requires — which is exactly what
    this function exists to notice. Reporting it here is what makes the field
    self-healing through the door that already exists (`--refresh-provenance`)
    rather than needing a migration nobody would remember to run.

    Pure: reads two files and returns findings. Refreshing the record is
    ``run_arabic_audit``, which the caller invokes if it wants the repair.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    report = book_dir / "_system" / "book-arabic-audit.json"
    if not book_md.exists() or not report.exists():
        return []
    try:
        stored = json.loads(report.read_text(encoding="utf-8"))
    except Exception:  # an unreadable record is a different problem from a stale one
        return []
    scripture = {
        (r.get("text") or "").strip()
        for ch in stored.get("chapters", [])
        for r in ch.get("runs", [])
        if r.get("resolution") == RESOLUTION_MUSHAF and r.get("reference")
    }
    fresh = audit_book_arabic(book_md.read_text(encoding="utf-8"), arabic_src="")
    return [
        (ch.get("chapter", ""), (r.get("text") or "").strip())
        for ch in fresh.get("chapters", [])
        for r in ch.get("runs", [])
        if r.get("resolution") == RESOLUTION_MUSHAF and (r.get("text") or "").strip() not in scripture
    ]


def run_arabic_audit(book_dir: Path, *, log=print, stages: dict[str, dict[str, int]] | None = None) -> dict[str, Any]:
    """Audit ``book/book.md`` in place and write ``_system/book-arabic-audit.json``.

    Non-fatal by contract: a provenance problem is surfaced for human judgment,
    never used to fail a compose that otherwise produced a good edition.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {}
    ocr = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    arabic_src = ocr.read_text(encoding="utf-8") if ocr.exists() else ""
    kb_root = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"
    report = audit_book_arabic(book_md.read_text(encoding="utf-8"), arabic_src, _kb_arabic_corpus(kb_root))
    if not arabic_src:
        report["note"] = "no OCR ground truth for this book — every run falls back to the knowledge base"
    # The `vowelling_review` list that used to be assembled here is gone
    # (2026-07-29). It flagged non-Quranic runs vowelled beyond the scan, which
    # after the reversal describes every non-Quranic run in the book by design —
    # `vowel_book.py` marks them all. What replaces it as the human-facing record
    # is that pass's own `_system/book-vowelling.json`, which lists the runs the
    # marks-only gate REFUSED and why.
    # Qur'anic COVERAGE — a different question from provenance, and one this audit
    # could not previously ask. Its totals grade the Arabic that IS on the page;
    # they say nothing about scripture the book cites and does not print. That gap
    # is why `degrees-of-excellence` read as a clean `unverified: 0` while 21 of
    # its 23 cited verses carried no Arabic at all.
    #
    # Copied from the sidecar rather than recomputed: `_book_quran` owns the
    # citation parser and the has-it-already test, and a second implementation
    # here is a second thing to drift. Absent sidecar (a book that never ran the
    # pass) reports null, which reads as "not measured" rather than as a pass.
    coverage_file = book_dir / "_system" / "book-quran-arabic.json"
    quran: dict[str, Any] = {"measured": False}
    if coverage_file.exists():
        try:
            doc = json.loads(coverage_file.read_text(encoding="utf-8"))
            quran = {
                "measured": True,
                "cited": doc.get("cited", 0),
                "with_arabic": doc.get("cited_inserted", 0) + doc.get("already", 0),
                "coverage": doc.get("coverage"),
                "uncovered": doc.get("uncovered", []),
                "uncited_inserted": doc.get("uncited_inserted", 0),
            }
        except Exception:  # a malformed sidecar must not fail the audit
            quran = {"measured": False}
    report["quran_coverage"] = quran

    out = book_dir / "_system" / "book-arabic-audit.json"
    if stages:
        report["stages"] = stages
        report["stage_losses"] = stage_losses(stages)
    elif out.exists():
        # Only a COMPOSE can measure per-stage Arabic loss — it is the only caller
        # that sees the text between passes. Re-auditing a finished book on the
        # standalone CLI has no stages to offer, and writing the report without
        # them threw away the compose's own record: every book lost `stages` and
        # `stage_losses` the first time the documented one-line command was run
        # (found 2026-08-09, before the refresh those keys were about to be
        # deleted from all seven books). Carried forward instead, exactly as
        # `quran_coverage` above is read from its sidecar rather than recomputed.
        try:
            prior = json.loads(out.read_text(encoding="utf-8"))
            for key in ("stages", "stage_losses"):
                if key in prior:
                    report[key] = prior[key]
        except Exception:  # a malformed prior report must not fail the audit
            pass
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    t = report["totals"]
    log(
        f"    arabic-audit: {t['arabic_runs']} Arabic runs · {t[RESOLUTION_MUSHAF]} canonical Quran · "
        f"{t[RESOLUTION_OCR]} from source · {t[RESOLUTION_KB]} from knowledge base · "
        f"{t[RESOLUTION_HONORIFIC]} honorific formulas · {t[RESOLUTION_UNVERIFIED]} unverified"
    )
    if quran.get("measured"):
        log(f"      quran coverage: {quran['with_arabic']}/{quran['cited']} cited verse(s) carry their Arabic")
        for u in quran.get("uncovered", []):
            log(f"      ! {u.get('ref')} cited with no Arabic — {u.get('reason')}")
    for ch in report["chapters"]:
        if ch["unverified"]:
            log(f"      ! {ch['chapter']}: {ch['unverified']} unverified of {ch['arabic_runs']}")
    for loss in report.get("stage_losses", []):
        log(
            f"      ! {loss['chapter']}: {loss['before']} -> {loss['after']} Arabic quotations "
            f"lost at the {loss['stage']} stage"
        )
    return report


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import sys

    if len(sys.argv) != 2:
        print("usage: _book_arabic_audit.py <BOOK_DIR>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(0 if run_arabic_audit(Path(sys.argv[1])) else 1)
