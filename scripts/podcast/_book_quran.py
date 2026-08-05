"""_book_quran.py — put the Arabic of a cited Qur'anic verse onto the page.

THE DEFECT THIS CLOSES. `degrees-of-excellence` cited 23 verses and carried the
Arabic of exactly one. The book's whole apparatus vowels and typesets Arabic, and
its scripture was shipping as English with a bare `(5:13)` after it. Two causes,
both mechanical:

  1. The composer's input is `_system/source/text/refined-english.md`, which holds
     no Arabic at all. The Arabic is in the OCR (`_system/source/ocr/raw-extract.md`
     marks 44 verses with ornate brackets `࿓…࿔`) and never travelled.
  2. `_book_compose._QURAN_CITE_RE` matched `Quran 41:53` but not a bare `(5:13)`.
     Of this book's citations only three matched — and Q 41:53, the single verse
     that reached the page in Arabic, was one of them. That is the whole mechanism.

WHERE THE TEXT COMES FROM — two sources, each answering the half it can.

  EXTENT is the book's. A book quotes a CLAUSE: `(2:282)` here is one sentence of
  the longest verse in the Qur'an, 12 words of 144. Inserting whole ayat would put
  Arabic on the page saying substantially more than the English beside it, in an
  edition whose contract is that the two correspond. So the extent is read off the
  source scan — what the author actually quoted.

  LETTERS AND MARKS are the mushaf's. The scan is OCR and carries real recognition
  errors (`إِنْرَاهِيمَ` for `إِبْرَاهِيمَ`), so its glyphs are never
  printed. Every word emitted is copied from `content/knowledge-base/mirror.db`
  via `quran_ayat_lookup` — the canonical vowelled Uthmani text. A model is never
  asked for scripture: for canonical Qur'an there is a right answer and it is in
  the repo.

  The two meet in `_extent`: the OCR span is aligned WORD BY WORD against the known
  ayah, and the canonical words at the matched positions are what get written. OCR
  noise therefore selects the window without ever reaching the page.

WHY THE ALIGNMENT IS FUZZY, AND WHY THAT IS SAFE. `_mushaf.mushaf_vocalisation`
refuses anything short of an exact skeleton match, which is right for its job
(vowelling a run already on the page) but resolves only 21 of this book's 44 spans
— the rest carry OCR letter errors. Here the verse is already KNOWN from its
citation, so alignment does not have to identify anything; it only has to find a
window inside one specific ayah. A per-word similarity with a monotonic
(longest-increasing-subsequence) constraint recovers the window through the noise,
and the worst case of a bad alignment is a clause one word short or long — not a
wrong verse, because the verse was never in question.

UNCITED QUOTATIONS need TWO INDEPENDENT SIGNALS. A passage with no reference has
to have its verse inferred, and a wrong inference prints the wrong scripture in a
published Islamic book — the error a reader is least able to catch. So a proposal
from the English (matched against the mirror's Pickthall/Asad columns) is acted on
only when the OCR independently contains that same verse in ornate brackets. One
signal alone is recorded for review and nothing is written.

WHAT IS DELIBERATELY NOT DONE. A cited verse whose Arabic is nowhere in the scan
gets NO Arabic and is reported as uncovered. Substituting the whole ayah there was
considered and rejected with Asif on 2026-08-01: it reintroduces exactly the
mismatch the extent rule exists to prevent, and it would do so on the verses we
know least about.

WHERE THE CODE LIVES. The resolution half — citation parsing, the mushaf lookup,
the fuzzy alignment that decides HOW MUCH of a verse the book quotes — is
``_book_quran_extent.py``, split out under the DR-005 line-count gate. What
remains here is placement: where on the page an insertion goes, the idempotency
guard, the whole-book driver and the CLI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _book_citations import find_citations  # noqa: E402
from _book_quran_extent import (  # noqa: E402
    _arabic_ratio,
    _english_proposal,
    _key,
    arabic_word_stream,
    ornate_spans,
    valid_reference,
    verse_extent,
)
from _paths import content_dir  # noqa: E402


def _block_start(lines: list[str], idx: int) -> int:
    """First line of the block line ``idx`` belongs to.

    A citation does not always sit on the line the quotation starts on. This book
    has a blockquote whose English runs on one line and whose `(Quran, 35: 45)`
    trails on the next, both inside one `>` run. Inserting immediately above the
    citation would have cut that blockquote in half and left the reference
    orphaned under an Arabic block, so the Arabic goes above the whole run.

    Only blockquotes need walking: every prose paragraph in a composed book.md is
    a single line.
    """
    if not lines[idx].lstrip().startswith(">"):
        return idx
    j = idx
    while j > 0 and lines[j - 1].lstrip().startswith(">"):
        j -= 1
    return j


def _already_has_arabic_above(lines: list[str], idx: int) -> bool:
    """Is the block above line ``idx`` already an Arabic verse block?

    The idempotency guard. Tests the PREVIOUS non-blank line for being mostly
    Arabic rather than merely containing it, because this book's English
    paragraphs routinely end in an inline honorific and a `contains` test would
    read every one of them as a verse already present.
    """
    j = idx - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0:
        return False
    prev = lines[j].lstrip("> ").strip()
    return bool(prev) and _arabic_ratio(prev) >= 0.6


def inject_text(
    text: str,
    spans: list[str],
    *,
    stream_keys: list[str] | None = None,
    uncited: list[dict] | None = None,
    log: Callable[[str], None] = print,
) -> tuple[str, dict]:
    """Insert canonical Arabic above every cited verse that the scan quotes.

    ``uncited`` carries the AGREED findings from `review_uncited` — passages with
    no reference where the English and the scan independently named the same
    verse. They are inserted on the same terms as a cited verse and recorded with
    `via: uncited-agreed`, so the one class of insertion that rests on inference
    is the one class a reviewer can list.
    """
    lines = text.split("\n")
    stats: dict = {
        "cited": 0,
        "inserted": 0,
        "already": 0,
        "uncovered": [],
        "inserted_detail": [],
        "invalid_reference": [],
    }

    # Decided first, applied second. The insertion point is not always the line
    # the citation sits on (see `_block_start`), so it can be ABOVE a line already
    # emitted — which a single append-as-you-go pass cannot reach back to.
    inserts: dict[int, str] = {}

    for idx, line in enumerate(lines):
        matches = list(find_citations(line))
        if not matches:
            continue

        # One insertion per BLOCK even when it carries two citations: the Arabic
        # goes above the quotation, and a block quoting two verses has no
        # unambiguous "above" for the second. Counted, not silently dropped.
        primary = None
        for m in matches:
            surah, ayah, last = m.surah, m.ayah, m.last
            if not valid_reference(surah, ayah) or (
                last is not None and not (valid_reference(surah, last) and last > ayah)
            ):
                stats["invalid_reference"].append({"line": idx + 1, "ref": m.text})
                continue
            stats["cited"] += 1
            if primary is None:
                primary = (surah, ayah, last)

        if primary is None:
            continue

        at = _block_start(lines, idx)
        if _already_has_arabic_above(lines, at) or at in inserts:
            stats["already"] += 1
            continue

        surah, ayah, last = primary
        ref = f"{surah}:{ayah}" + (f"-{last}" if last else "")
        arabic, detail = verse_extent(surah, ayah, spans, last, stream_keys)
        if not arabic:
            stats["uncovered"].append({"ref": ref, "line": idx + 1, **detail})
            continue

        inserts[at] = arabic
        stats["inserted"] += 1
        stats["inserted_detail"].append({"ref": ref, "line": at + 1, "via": "cited", **detail})

    # The agreed uncited passages, after the cited ones so a verse that IS cited
    # somewhere always wins the insertion point over an inference about it.
    for finding in uncited or []:
        surah_s, _, ayah_s = str(finding.get("proposed_ref", "")).partition(":")
        if not surah_s.isdigit() or not ayah_s.isdigit():
            continue
        surah, ayah = int(surah_s), int(ayah_s)
        idx = int(finding.get("line", 0)) - 1
        if not (0 <= idx < len(lines)) or not valid_reference(surah, ayah):
            continue
        at = _block_start(lines, idx)
        if _already_has_arabic_above(lines, at) or at in inserts:
            stats["already"] += 1
            continue
        arabic, detail = verse_extent(surah, ayah, spans, None, stream_keys)
        if not arabic:
            continue
        inserts[at] = arabic
        stats["inserted"] += 1
        stats["uncited_inserted"] = stats.get("uncited_inserted", 0) + 1
        stats["inserted_detail"].append(
            {
                "ref": f"{surah}:{ayah}",
                "line": at + 1,
                "via": "uncited-agreed",
                "english_similarity": finding.get("english_similarity"),
                **detail,
            }
        )

    out_lines: list[str] = []
    for idx, line in enumerate(lines):
        arabic = inserts.get(idx)
        if arabic:
            # `> arabic` then a blank line: the renderer flushes a quote block at
            # the first blank, so this yields `blockquote.quran` for the Arabic
            # followed by the quotation as the book already had it. That is the
            # exact shape this book's one pre-existing verse uses (book.md:41-43),
            # and the print and screen stylesheets both style the pair through
            # that adjacency.
            #
            # The quotation itself is NOT rewritten to match. Pure insertion keeps
            # every authored character where the author put it; restructuring a
            # paragraph is a change this pass has no mandate to make.
            if out_lines and out_lines[-1].strip():
                out_lines.append("")
            out_lines.append(f"> {arabic}")
            out_lines.append("")
        out_lines.append(line)

    return "\n".join(out_lines), stats


def review_uncited(text: str, spans: list[str]) -> list[dict]:
    """Unlabelled passages that may be scripture, with their two signals.

    IDENTIFY ONLY. Nothing here is written to the page. A proposal is marked
    `agreed` when the English match and the scan independently name the same
    verse; that is the bar for acting, and acting is a later decision than this
    function.
    """
    findings: list[dict] = []
    # Resolve the scan's spans once, so agreement can be checked without a second
    # pass per candidate.
    scan_refs = _spans_to_refs(spans)

    cited_here = {(c.surah, c.ayah) for c in find_citations(text)}

    for idx, line in enumerate(text.split("\n")):
        if next(find_citations(line), None):
            continue
        for quoted in re.findall(r'"([^"]{40,400})"', line):
            proposal = _english_proposal(quoted)
            if not proposal:
                continue
            ref, score = proposal
            if ref in cited_here:
                continue  # the same verse is cited properly elsewhere
            findings.append(
                {
                    "line": idx + 1,
                    "passage": quoted[:160],
                    "proposed_ref": f"{ref[0]}:{ref[1]}",
                    "english_similarity": round(score, 3),
                    "corroborated_by_scan": ref in scan_refs,
                    "agreed": ref in scan_refs,
                }
            )
    return findings


def _spans_to_refs(spans: Iterable[str]) -> set[tuple[int, int]]:
    """Which verses the scan's ornate spans are, by exact mushaf resolution.

    Exact-only on purpose: this set is the CORROBORATING signal, and a signal that
    tolerates ambiguity corroborates nothing. Spans too OCR-damaged to resolve
    exactly are simply absent, which withholds agreement rather than granting it.
    """
    from _mushaf import mushaf_vocalisation

    out: set[tuple[int, int]] = set()
    from source_library_mirror import open_mirror

    resolved: list[str] = []
    for span in spans:
        v = mushaf_vocalisation(span)
        if v:
            resolved.append(v)
    if not resolved:
        return out
    try:
        conn = open_mirror()
    except Exception:
        return out
    try:
        rows = conn.execute("SELECT surah, ayat, arabic FROM fts_quran").fetchall()
    except Exception:
        return out
    finally:
        conn.close()
    for surah, ayat, arabic in rows:
        skeleton = " ".join(_key(w) for w in (arabic or "").split())
        for v in resolved:
            needle = " ".join(_key(w) for w in v.split())
            if needle and needle in skeleton:
                out.add((int(surah), int(ayat)))
    return out


def inject_book(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    dry_run: bool = False,
    review: bool = True,
) -> dict:
    """Put cited verses' Arabic into `book/book.md`. Returns the run's stats."""
    md = book_dir / "book" / "book.md"
    if not md.exists():
        log("quran-arabic: no book.md - skipped")
        return {"inserted": 0}

    ocr = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    ocr_text = ocr.read_text(encoding="utf-8") if ocr.exists() else ""
    spans = ornate_spans(ocr_text)
    stream_keys = [_key(w) for w in arabic_word_stream(ocr_text)]
    if not ocr_text:
        log(
            "quran-arabic: no OCR to read an extent from — every cited verse will "
            "report as uncovered rather than being guessed at"
        )

    before = md.read_text(encoding="utf-8")
    # The review runs BEFORE the injection, because its agreed findings are inputs
    # to it — and it reads the ORIGINAL text, so its line numbers address the same
    # document `inject_text` is about to walk.
    findings = review_uncited(before, spans) if review else []
    after, stats = inject_text(
        before,
        spans,
        stream_keys=stream_keys,
        uncited=[f for f in findings if f["agreed"]],
        log=log,
    )
    stats["spans_in_scan"] = len(spans)
    stats["scan_arabic_words"] = len(stream_keys)
    stats["uncited_review"] = findings

    # Coverage answers ONE question — of the verses this book cites, how many now
    # carry their Arabic — so its numerator counts cited insertions only. Folding
    # the uncited-agreed ones in put it over 100%, which is not a rounding wart but
    # a metric measuring two different populations against one denominator.
    total = stats["cited"]
    cited_inserted = sum(1 for d in stats["inserted_detail"] if d.get("via") == "cited")
    covered = cited_inserted + stats["already"]
    stats["coverage"] = round(min(covered, total) / total, 3) if total else 1.0
    stats["cited_inserted"] = cited_inserted

    if not dry_run and after != before:
        md.write_text(after, encoding="utf-8")

    report = book_dir / "_system" / "book-quran-arabic.json"
    if not dry_run:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log(
        f"quran-arabic: {cited_inserted} of {total} cited verse(s) given Arabic, "
        f"{stats['already']} already had it, {len(stats['uncovered'])} uncovered "
        f"(coverage {stats['coverage']:.0%})"
    )
    for u in stats["uncovered"]:
        log(f"  uncovered {u['ref']} (line {u['line']}): {u['reason']}")
    proposed = len(stats.get("uncited_review", []))
    agreed = stats.get("uncited_inserted", 0)
    if proposed:
        log(
            f"  unlabelled passages: {proposed} proposed from the English, "
            f"{agreed} corroborated by the scan and given Arabic — the rest are "
            f"listed in book-quran-arabic.json and were NOT written"
        )

    # An alignment computed before this pass describes paragraphs that no longer
    # exist at the same offsets. Said out loud rather than silently repaired: the
    # alignment is expensive and rebuilding it is the caller's decision.
    alignment = book_dir / "_system" / "arabic-alignment.json"
    if stats["inserted"] and alignment.exists():
        try:
            doc = json.loads(alignment.read_text(encoding="utf-8"))
            pairs = sum(len(c.get("pairs") or []) for c in doc.get("chapters") or [])
        except Exception:
            pairs = 0
        if pairs:
            log(
                f"  NOTE: {pairs} paragraph alignment pair(s) predate these "
                f"insertions — re-run align_arabic_paragraphs.py for this book"
            )
    return stats


def _books_with_a_composed_book() -> list[Path]:
    from _paths import REPO_ROOT

    return sorted({md.parent.parent for md in (REPO_ROOT / "content").glob("*/**/book/book.md")})


def main() -> int:
    ap = argparse.ArgumentParser(description="Put the canonical Arabic of every cited Qur'anic verse into book.md.")
    ap.add_argument("--slug", help="one book; omit and pass --all to sweep every composed book")
    ap.add_argument("--all", action="store_true", help="sweep every book that has a composed book.md")
    ap.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    ap.add_argument(
        "--no-review",
        action="store_true",
        help="skip the unlabelled-quotation sweep (the slow half; it reads every quotation)",
    )
    a = ap.parse_args()
    if bool(a.slug) == bool(a.all):
        print("Pass exactly one of --slug <slug> or --all.", file=sys.stderr)
        return 2

    if a.all:
        targets = _books_with_a_composed_book()
        if not targets:
            print("No composed books found.", file=sys.stderr)
            return 1
    else:
        book_dir = content_dir(a.slug)
        if not book_dir or not book_dir.exists():
            print(f"Book not found: {a.slug}", file=sys.stderr)
            return 1
        targets = [book_dir]

    from _paths import REPO_ROOT

    for book_dir in targets:
        try:
            label = book_dir.relative_to(REPO_ROOT / "content")
        except ValueError:  # pragma: no cover - a book outside content/
            label = book_dir
        print(f"==> {label}")
        inject_book(book_dir, dry_run=a.dry_run, review=not a.no_review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
