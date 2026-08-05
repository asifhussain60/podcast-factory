#!/usr/bin/env python3
"""align_arabic_paragraphs.py — say which Arabic paragraph each English one came from.

The Arabic source is numbered `(١)`..`(٥٥٨)` and the refined English carries the
SAME numbering, so `book-toc.json`'s per-chapter line ranges already name each
chapter's Arabic paragraphs exactly. What is missing is the last hop: compose
stripped the numbers from `book.md` and articulation reshaped the paragraphs. This
computes that hop once and stores it, so the Composer can put the right Arabic above
the right English paragraph without guessing at read time.

DETERMINISTIC FIRST, the same shape `fill_glossary_arabic` uses. An
anchor-constrained DP (`_align_paragraphs`) does the work for free; a model is
asked only about the residue it cannot settle, and then only as a narrow multiple
choice — "this paragraph lies between ¶88 and ¶91, which is it?" — never to align a
chapter.

TWO CONFIDENCE STATES, and neither is "unknown":
  * `verified`  — anchored on a shared Arabic quotation, or carrying enough of its
                  own vocabulary. Names one source paragraph.
  * `bracketed` — carried by the path between two confident neighbours. Names that
                  span, and the reveal says so.

    python3 scripts/podcast/align_arabic_paragraphs.py <slug>          # dry run
    python3 scripts/podcast/align_arabic_paragraphs.py <slug> --apply
    python3 scripts/podcast/align_arabic_paragraphs.py --all --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _align_paragraphs import SELF_SUPPORT, align, bracket, is_monotonic  # noqa: E402
from _arabic_coverage import arabic_run_spans, normalize_arabic  # noqa: E402
from _arabic_paragraphs import load_blocks  # noqa: E402
from _para_blocks import blocks_fingerprint, para_fingerprint, prose_blocks  # noqa: E402
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _vowelled_source import write_atomic  # noqa: E402
from _vowelling import MIN_RUN_CHARS  # noqa: E402

REPORT_NAME = "arabic-alignment.json"
SCHEMA = "podcast.arabic-alignment/v1"

# Scan furniture in the refined English, dropped before paragraphs are split out.
_PAGE_LINE_RE = re.compile(r"^\s*<!--\s*page\s+\d+\s*-->\s*$")

# Below this there is no numbering to align against — a handful of stray markers is
# an artefact, not an edition's apparatus.
_MIN_NUMBERED_PARAGRAPHS = 20

# A bracket of one is already an answer and is marked verified above, so the repair
# pass starts at two. Two is where the bulk of the residue actually is — chapter 3
# alone carries 45 brackets at a median width of 2 — and a binary choice is the
# cheapest, most reliable question that can be put to a model.
REPAIR_MIN_WIDTH = 2
# And never over an absurd span — that is a sign the DP lost the thread, not a
# question a model should paper over.
REPAIR_MAX_WIDTH = 12

# The questions are independent, so they go out together. Sequentially this book's
# 71 repairs took ten and a half minutes; as a step that runs on every compose of a
# changed chapter that is a stall, not a step. Same width `vowel_glossary` and the
# vowelling sweep already use against the same endpoint.
REPAIR_WORKERS = 8

SYSTEM = """You match one paragraph of an English translation to the paragraph of \
its source that it was translated from.

You are given a numbered list of candidate SOURCE paragraphs and one TRANSLATED \
paragraph. The translation is faithful but articulated: it may split one source \
paragraph into several, so several translated paragraphs can share one source.

Answer with the single candidate number and nothing else - no words, no \
punctuation, no explanation. If none of them is a plausible source for the \
translated paragraph, answer 0."""


def _chapter_bodies(book_md: Path) -> dict[str, str]:
    """Composed chapter bodies from book.md, keyed by the Composer's chapter key."""
    from _book_edits import anchor_key

    text = book_md.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    parts = re.split(r"(?m)^(##\s+.+)$", text)
    for i in range(1, len(parts), 2):
        heading, body = parts[i], parts[i + 1]
        out[anchor_key(heading)] = body
    return out


def _source_paragraphs(refined: list[str], ranges: list[list[int]]) -> tuple[list[str], list[int | None]]:
    """A chapter's source paragraphs and the ¶ number each one opens with.

    Some blocks are continuations — a paragraph split across a page break carries no
    marker of its own — so the number is carried forward from the last one that had
    it, which is what makes every block addressable.
    """
    lines: list[str] = []
    for start, end in ranges:
        lines += refined[start - 1 : end]
    # Drop page markers BEFORE splitting, exactly as `_arabic_paragraphs` does on
    # the other side. A marker sits on its own line with no blank line after it, so
    # a paragraph whose number follows one opened its block with `<!-- page 12 -->`
    # instead of `(63)` and the number was never picked up — five of chapter 3's
    # fifty-seven, and with them the quotation anchors that would have pinned the
    # path there. The two sides now treat page furniture the same way.
    lines = [ln for ln in lines if not _PAGE_LINE_RE.match(ln)]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", "\n".join(lines)) if b.strip()]
    numbers: list[int | None] = []
    current: int | None = None
    for block in blocks:
        m = re.match(r"^\((\d+)\)", block)
        if m:
            current = int(m.group(1))
        numbers.append(current)
    return blocks, numbers


def _anchors(
    composed: list[str],
    numbers: list[int | None],
    arabic: dict,
    glossary_skeletons: set[str],
) -> dict[int, int]:
    """Composed paragraphs pinned to a source paragraph by a shared Arabic quotation.

    Glossary terms are excluded: the inline-Arabic overlay places those at first
    mention in the ENGLISH, so they belong to no source paragraph and pinning to one
    would drag the path somewhere wrong. Measured on this book, 24 of the 77 Arabic
    runs in the edition are overlay terms and 53 are genuine quotations.
    """
    by_number = {n: normalize_arabic(p.text) for n, p in arabic.items()}
    index_of: dict[int, int] = {}
    for j, n in enumerate(numbers):
        if n is not None and n not in index_of:
            index_of[n] = j

    found: dict[int, int] = {}
    for i, block in enumerate(composed):
        for run in arabic_run_spans(block, MIN_RUN_CHARS):
            skeleton = normalize_arabic(run)
            if not skeleton or skeleton in glossary_skeletons:
                continue
            needle = skeleton[:20]
            hits = [n for n, hay in by_number.items() if needle in hay]
            # Only an UNAMBIGUOUS quotation anchors. A formula that recurs in five
            # paragraphs tells us nothing about which one this is.
            if len(hits) == 1 and hits[0] in index_of:
                found[i] = index_of[hits[0]]
                break
    return found


def _glossary_skeletons(book_dir: Path) -> set[str]:
    path = book_dir / "_system" / "glossary.yml"
    if not path.exists():
        return set()
    out = set()
    for m in re.finditer(r"arabic_script:\s*(.+)", path.read_text(encoding="utf-8")):
        sk = normalize_arabic(m.group(1).strip())
        if sk:
            out.add(sk)
    return out


def _repair(
    composed_block: str,
    candidates: list[tuple[int, str]],
    *,
    call: Callable[[str, str], str] | None = None,
) -> int | None:
    """Ask which candidate source paragraph a composed paragraph came from.

    Returns the chosen source ¶ number, or None when the model declines or answers
    outside the offered set — a refusal is recorded, never coerced into a guess.
    """
    if not candidates:
        return None
    ask = call or (lambda system, user: _gemini(system, user))
    listing = "\n\n".join(f"[{i + 1}] {text[:600]}" for i, (_, text) in enumerate(candidates))
    user = f"CANDIDATE SOURCE PARAGRAPHS:\n\n{listing}\n\nTRANSLATED PARAGRAPH:\n\n{composed_block[:900]}"
    try:
        answer = ask(SYSTEM, user)
    except Exception:
        return None
    m = re.search(r"\d+", answer or "")
    if not m:
        return None
    choice = int(m.group(0))
    if not (1 <= choice <= len(candidates)):
        return None
    return candidates[choice - 1][0]


def _gemini(system: str, user: str) -> str:
    from vowel_book import _gemini as gemini_call

    return gemini_call(system, user)


def align_book(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    apply: bool = False,
    force: bool = False,
    call: Callable[[str, str], str] | None = None,
) -> dict:
    """Align every chapter of a book. Returns the report that would be written."""
    toc_path = book_dir / "book" / "book-toc.json"
    book_md = book_dir / "book" / "book.md"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not (toc_path.exists() and book_md.exists() and refined_path.exists()):
        log("    no translation-edition source — nothing to align")
        return {}
    arabic = load_blocks(book_dir)
    if not arabic:
        log("    no Arabic source — nothing to align")
        return {}

    # THE CONTRACT THIS WHOLE STEP RESTS ON: the critical edition numbers its
    # paragraphs and the refined English carries the SAME numbering, so a chapter's
    # line range names its Arabic paragraphs exactly. That is a property of the
    # EDITION, not of the pipeline — measured across the library, one book has
    # 557/558, one has 54/54, and three have effectively none. Without it there is
    # nothing to align to, and saying so plainly is the whole point: the pass would
    # otherwise report "0/0 verified" and read like a success.
    refined_text = refined_path.read_text(encoding="utf-8")
    english_markers = len(re.findall(r"(?m)^\s*(?:<!--\s*page\s+\d+\s*-->\s*)?\((\d+)\)", refined_text))
    if english_markers < _MIN_NUMBERED_PARAGRAPHS or len(arabic) < _MIN_NUMBERED_PARAGRAPHS:
        log(
            f"    source is not paragraph-numbered on both sides "
            f"(Arabic {len(arabic)}, English {english_markers}) — cannot align; skipped"
        )
        return {}

    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    refined = refined_path.read_text(encoding="utf-8").splitlines()
    bodies = _chapter_bodies(book_md)
    glossary = _glossary_skeletons(book_dir)
    previous = _load_report(book_dir)
    prior_by_key = {c["chapter_key"]: c for c in previous.get("chapters", [])}

    from _book_edits import anchor_key

    chapters: list[dict] = []
    spend = {"in_chars": 0, "out_chars": 0, "calls": 0}

    for entry in toc.get("chapters", []):
        key = anchor_key(f"## {entry.get('title', '')}")
        body = bodies.get(key)
        if body is None:  # numbered heading: the key carries the ordinal
            for k, v in bodies.items():
                if k.endswith(anchor_key(f"## {entry.get('title', '')}")):
                    key, body = k, v
                    break
        if body is None:
            log(f"    chapter not found in book.md: {entry.get('title')!r} — skipped")
            continue

        composed = prose_blocks(body)
        fp = blocks_fingerprint(body)
        prior = prior_by_key.get(key)
        if prior and prior.get("blocks_fingerprint") == fp and not force:
            chapters.append(prior)
            log(f"    {entry.get('title', '')[:38]:<38} unchanged — kept")
            continue

        src_blocks, numbers = _source_paragraphs(refined, entry.get("source_line_ranges") or [])
        if not src_blocks or not composed:
            continue

        anchors = _anchors(composed, numbers, arabic, glossary)
        alignments = align(src_blocks, composed, anchors)
        if not alignments or not is_monotonic(alignments):
            log(f"    {entry.get('title', '')[:38]:<38} REFUSED — alignment not monotonic")
            continue

        def number_at(source_index: int) -> int | None:
            for k in range(source_index, -1, -1):
                if numbers[k] is not None:
                    return numbers[k]
            return None

        # ── Classify first, ask second ────────────────────────────────────────
        # Every paragraph is settled deterministically here; only the residue is
        # collected as a question. Asking inside the loop made the repair pass
        # SEQUENTIAL, which on this book was 71 calls and over ten minutes — for a
        # step that runs on every compose of a changed chapter, that is the
        # difference between a pipeline step and a pipeline stall.
        settled: list[dict | None] = []
        questions: dict[int, list[int]] = {}
        for a in alignments:
            n = number_at(a.source_index)
            if n is None:
                settled.append(None)
                continue
            fpx = para_fingerprint(composed[a.index])
            if a.anchored or a.score >= SELF_SUPPORT:
                settled.append({"fp": fpx, "source_paras": [n], "confidence": "verified", "anchored": a.anchored})
                continue
            lo_i, hi_i = bracket(alignments, a.index)
            lo, hi = number_at(lo_i), number_at(hi_i)
            if lo is None or hi is None:
                settled.append(None)
                continue
            span = list(range(min(lo, hi), max(lo, hi) + 1))
            if len(span) == 1:
                # The bracket collapsed to a point: both confident neighbours name
                # the SAME source paragraph, so monotonicity leaves this one no
                # other place to be. A determined answer — calling it "bracketed"
                # would under-report what is actually known.
                settled.append(
                    {"fp": fpx, "source_paras": span, "confidence": "verified", "anchored": False, "pinned": True}
                )
                continue
            settled.append({"fp": fpx, "source_paras": span, "confidence": "bracketed", "anchored": False})
            if apply and REPAIR_MIN_WIDTH <= len(span) <= REPAIR_MAX_WIDTH:
                questions[a.index] = span

        # ── Ask the residue, all at once ──────────────────────────────────────
        if questions:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def ask_one(idx: int) -> tuple[int, int | None, int]:
                span = questions[idx]
                cands = [(x, arabic_english(refined, numbers, src_blocks, x)) for x in span]
                cands = [(x, t) for x, t in cands if t]
                chars = sum(len(t) for _, t in cands) + len(composed[idx])
                return idx, _repair(composed[idx], cands, call=call), chars

            with ThreadPoolExecutor(max_workers=REPAIR_WORKERS) as pool:
                for future in as_completed([pool.submit(ask_one, i) for i in questions]):
                    idx, chosen, chars = future.result()
                    spend["calls"] += 1
                    spend["in_chars"] += chars
                    if chosen is None:
                        continue  # a refusal keeps its bracket, never a guess
                    spend["out_chars"] += 4
                    pos = next(k for k, a in enumerate(alignments) if a.index == idx)
                    settled[pos] = {
                        "fp": para_fingerprint(composed[idx]),
                        "source_paras": [chosen],
                        "confidence": "verified",
                        "anchored": False,
                        "repaired": True,
                    }

        pairs = [p for p in settled if p is not None]

        verified = sum(1 for p in pairs if p["confidence"] == "verified")
        chapters.append(
            {
                "chapter_key": key,
                "title": entry.get("title", ""),
                "blocks_fingerprint": fp,
                "source_para_range": [min(n for n in numbers if n), max(n for n in numbers if n)]
                if any(numbers)
                else [],
                "pairs": pairs,
            }
        )
        pct = verified * 100 // max(len(pairs), 1)
        log(f"    {entry.get('title', '')[:38]:<38} {verified:>3}/{len(pairs):<3} verified ({pct}%)")

    report = {"schema": SCHEMA, "chapters": chapters}
    if apply:
        write_atomic(book_dir / "_system" / REPORT_NAME, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if spend["calls"]:
            _record_spend(book_dir, spend)
    return report


def arabic_english(refined: list[str], numbers: list[int | None], blocks: list[str], number: int) -> str:
    """The ENGLISH text of a source paragraph — what the repair question shows.

    The model is asked in English on both sides deliberately: it is a matching
    question, and giving it Arabic on one side and English on the other would make
    it a translation judgement instead.
    """
    for j, n in enumerate(numbers):
        if n == number:
            return re.sub(r"^\(\d+\)\s*", "", blocks[j]).strip()
    return ""


def _record_spend(book_dir: Path, spend: dict) -> None:
    try:
        from _cost_ledger import append_gemini_cost

        append_gemini_cost(
            book_dir=book_dir,
            phase="0book-compose",
            step="arabic-alignment",
            model="gemini-2.5-pro",
            in_chars=spend["in_chars"],
            out_chars=spend["out_chars"],
        )
    except Exception as e:  # pragma: no cover
        print(f"    WARN: cost-ledger append failed: {e}", file=sys.stderr)
    try:
        from _authoring._core import record_model_provenance

        record_model_provenance(book_dir, phase="0book-compose", step="arabic-alignment", model="gemini-2.5-pro")
    except Exception:  # pragma: no cover
        pass


def _load_report(book_dir: Path) -> dict:
    path = book_dir / "_system" / REPORT_NAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _books_with_an_arabic_source() -> list[Path]:
    return sorted(
        {p.parent.parent.parent.parent for p in (REPO_ROOT / "content").glob("*/**/_system/source/ocr/raw-extract.md")}
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Map each composed English paragraph to the source paragraph it came from.",
        epilog="Dry run by default — the repair pass spends. Pass --apply to write.",
    )
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true", help="every book carrying an Arabic source")
    ap.add_argument("--apply", action="store_true", help="write the sidecar (otherwise report only)")
    ap.add_argument("--force", action="store_true", help="re-align chapters whose fingerprint is unchanged")
    a = ap.parse_args()
    if bool(a.slug) == bool(a.all):
        print("Pass exactly one of <slug> or --all.", file=sys.stderr)
        return 2

    if a.all:
        targets = _books_with_an_arabic_source()
    else:
        book_dir = content_dir(a.slug)
        if not book_dir or not book_dir.exists():
            print(f"Book not found: {a.slug}", file=sys.stderr)
            return 1
        targets = [book_dir]

    if not a.apply:
        print("DRY RUN — nothing is written and no model is called. Pass --apply.\n")
    for book_dir in targets:
        try:
            label = book_dir.relative_to(REPO_ROOT / "content")
        except ValueError:  # pragma: no cover
            label = book_dir
        print(f"==> {label}")
        align_book(book_dir, apply=a.apply, force=a.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
