#!/usr/bin/env python3
"""dedup_cross_chapter.py — retroactive cross-chapter doctrine de-duplication.

The complement to the AUTHORING-TIME prevention (R-NO-DOCTRINE-REPEAT, threaded
through Phase 0d so new chapters do "a one-line callback instead of re-teaching").
That prevention is born-correct but only helps books authored AFTER it landed; a
book authored earlier (or any book whose 0d predates a rule) carries verbatim
doctrine repeated across chapters with no built-in remedy short of a full 0d
re-author — which regenerates and loses already-polished prose.

This tool resolves the repetition in place, DETERMINISTICALLY, without an LLM
rewrite:

  * Detection reuses the chapter-set P8 logic (12-gram shingles, with inline
    bibliographic citations stripped — citing the same source in several chapters
    is scholarship, not duplication). Only what P8 would flag is touched.
  * For each contiguous run of near-duplicate sentences, the EARLIEST chapter in
    reading order keeps the passage in full (the "home"); the later chapter's
    repeat is replaced with a single-line callback to the home chapter — the same
    idiom R-NO-DOCTRINE-REPEAT prescribes at authoring time.
  * Frame sections (openers / landings / closings) are excluded, exactly as the
    P8 detector excludes them.
  * Short, integral quotations never form a long enough run to trip the
    span threshold, so a half-verse quoted in passing is left alone; only
    substantial verbatim blocks collapse.

Dry-run first (the vacuum/clean-commit pattern): prints the proposed plan and
writes nothing. `--apply` performs the edits. Idempotent: the callbacks are
short enough to carry no 12-gram, so a second run finds nothing.

Usage:
    python3 scripts/podcast/dedup_cross_chapter.py <book-dir>            # dry-run plan
    python3 scripts/podcast/dedup_cross_chapter.py <book-dir> --apply    # write edits
    python3 scripts/podcast/dedup_cross_chapter.py <book-dir> --json     # plan as JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_chapter_set import (
    _CITATION_SPAN_RES,
    _DUP_EXCLUDE_SUBSTRINGS,
    SHINGLE_DUP_THRESHOLD,
    SHINGLE_N,
    chapter_num,
    chapter_slug,
    list_chapter_files,
)

# A later sentence counts as a near-duplicate of an earlier one when this share
# of its shingles is also in the earlier sentence. High enough that incidental
# phrase overlap does not trip it; low enough to catch lightly-reworded repeats.
NEAR_DUP_RATIO = 0.55
# A run of near-duplicate sentences is only collapsed when, together, it shares at
# least this many distinct shingles with the home — identical to the P8 floor, so
# the fixer resolves exactly what the detector flags and nothing smaller.
MIN_RUN_SHINGLES = SHINGLE_DUP_THRESHOLD
# A repeat is only safe to AUTO-collapse to a callback when it is (nearly) a
# standalone paragraph. Below this share of its paragraph it is woven into unique
# prose — a blunt cut would strip the duplicated sentence but leave its lead-in
# and restatement neighbours dangling. Those are FLAGGED for an authoring rewrite,
# never auto-edited.
STANDALONE_COVERAGE = 0.85

# Frame headings (openers / landings / closings) — mirror of _concept_shingles in
# check_chapter_set: their bodies are excluded from both detection and edits.
_FRAME_HEADING_RE = re.compile(
    r"^##\s+(where\s+this\s+episode|what\s+this\s+episode\s+lands|closing)",
    re.IGNORECASE,
)


@dataclass
class Sentence:
    text: str
    start: int  # absolute char offset in the chapter file
    end: int  # absolute char offset (exclusive)
    shingles: set[tuple[str, ...]] = field(default_factory=set)


def _blank_citations(s: str) -> str:
    """Replace inline bibliographic citation spans with equal-length blanks.

    Equal-length (not collapsed-to-one-space) so downstream char offsets into the
    ORIGINAL text stay valid. Run over the WHOLE chapter — not per sentence — so a
    citation that straddles a sentence boundary (e.g. a parenthetical carrying a
    'vol. 8, p. 245' that the splitter would cut) is still fully neutralised. A
    bare citation tail must never read as repeated teaching."""

    def repl(m: re.Match) -> str:
        return " " * (m.end() - m.start())

    for cre in _CITATION_SPAN_RES:
        s = cre.sub(repl, s)
    return s


def _shingles(text: str) -> set[tuple[str, ...]]:
    """12-gram shingles of a (already citation-blanked) sentence, lowercased — the
    same normalization the P8 detector uses, including the formulaic-phrase
    exclusions."""
    tokens = re.findall(r"[a-z']+", text.lower())
    out: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - SHINGLE_N + 1):
        gram = tuple(tokens[i : i + SHINGLE_N])
        joined = " ".join(gram)
        if any(x in joined for x in _DUP_EXCLUDE_SUBSTRINGS):
            continue
        out.add(gram)
    return out


_SENT_SPLIT_RE = re.compile(r'(?<=[.?!])\s+(?=[A-Z"“(*])')


def concept_sentences(text: str) -> list[Sentence]:
    """Sentences inside CONCEPT sections only (frames + headings excluded), each
    carrying its absolute char offsets in `text`. Chapters store one paragraph per
    physical line, so sentence offsets are computed within each concept line."""
    blanked = _blank_citations(text)  # whole-text, equal-length: offsets stay valid
    sentences: list[Sentence] = []
    keep = True
    pos = 0
    for line in text.split("\n"):
        line_len = len(line)
        if line.startswith("## "):
            keep = not _FRAME_HEADING_RE.match(line)
        elif line.startswith("#"):
            pass  # H1 / other headings: never concept prose
        elif keep and line.strip():
            # split this paragraph-line into sentences, tracking offsets
            for m in _split_with_offsets(line):
                seg, off = m
                if not seg.strip():
                    continue
                start = pos + off
                sentences.append(Sentence(seg, start, start + len(seg)))
        pos += line_len + 1  # +1 for the '\n' removed by split
    for s in sentences:
        s.shingles = _shingles(blanked[s.start : s.end])  # shingles from the blanked slice
    return sentences


def _split_with_offsets(line: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    last = 0
    for m in _SENT_SPLIT_RE.finditer(line):
        end = m.start()
        out.append((line[last:end], last))
        last = m.end()
    out.append((line[last:], last))
    return out


def chapter_title(text: str) -> str:
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


@dataclass
class Collapse:
    chapter_slug: str
    home_slug: str
    home_title: str
    start: int
    end: int
    original: str
    callback: str
    shared: int
    scripture_hint: bool = False  # original carries a *…* quotation (verse/dua) — review before collapsing
    embedded: bool = False  # repeat is woven INTO a larger unique paragraph — needs an authoring
    # rewrite, NOT a blunt cut (a cut leaves dangling lead-ins / restatements)


def _callback(home_title: str) -> str:
    # Short by construction: < 12 tokens, so it carries no 12-gram and a second
    # pass finds nothing (idempotent). Mirrors the R-NO-DOCTRINE-REPEAT idiom.
    return f'This teaching is developed in full earlier, in "{home_title}."'


def plan(book_dir: Path) -> list[Collapse]:
    files = list_chapter_files(book_dir)
    # reading order = chapter number, then filename
    files = sorted(files, key=lambda p: (chapter_num(p) if chapter_num(p) is not None else 1e9, p.name))
    texts = {p: p.read_text(encoding="utf-8") for p in files}
    slugs = {p: chapter_slug(p) for p in files}
    titles = {p: chapter_title(texts[p]) for p in files}
    sents = {p: concept_sentences(texts[p]) for p in files}

    # union of all shingles in each EARLIER chapter, for home lookup
    collapses: list[Collapse] = []
    for idx, p in enumerate(files):
        earlier = files[:idx]
        if not earlier:
            continue
        # map shingle -> earliest chapter that contains it
        home_of: dict[tuple[str, ...], Path] = {}
        for ep in earlier:
            for s in sents[ep]:
                for g in s.shingles:
                    home_of.setdefault(g, ep)

        # walk this chapter's sentences; group consecutive near-dup runs
        run: list[Sentence] = []
        run_home: dict[Path, int] = {}
        run_shared: set[tuple[str, ...]] = set()

        def flush():
            nonlocal run, run_home, run_shared
            if run and run_shared and len(run_shared) >= MIN_RUN_SHINGLES:
                home = max(run_home, key=lambda hp: run_home[hp])
                start = run[0].start
                end = run[-1].end
                original = texts[p][start:end]
                # paragraph (single physical line) the run sits in
                para_start = texts[p].rfind("\n", 0, start) + 1
                para_end = texts[p].find("\n", end)
                if para_end == -1:
                    para_end = len(texts[p])
                para_len = max(1, len(texts[p][para_start:para_end].strip()))
                coverage = len(original.strip()) / para_len
                collapses.append(
                    Collapse(
                        chapter_slug=slugs[p],
                        home_slug=slugs[home],
                        home_title=titles[home] or slugs[home],
                        start=start,
                        end=end,
                        original=original,
                        callback=_callback(titles[home] or slugs[home]),
                        shared=len(run_shared),
                        scripture_hint=("*" in original),
                        embedded=(coverage < STANDALONE_COVERAGE),
                    )
                )
            run, run_home, run_shared = [], {}, set()

        for s in sents[p]:
            shared = {g for g in s.shingles if g in home_of}
            ratio = (len(shared) / len(s.shingles)) if s.shingles else 0.0
            if s.shingles and len(shared) >= 2 and ratio >= NEAR_DUP_RATIO:
                run.append(s)
                run_shared |= shared
                for g in shared:
                    run_home[home_of[g]] = run_home.get(home_of[g], 0) + 1
            else:
                flush()
        flush()
    return collapses


def apply_collapses(book_dir: Path, collapses: list[Collapse]) -> dict[str, int]:
    # Only standalone repeats are ever auto-edited. Embedded repeats are returned
    # to the operator/authoring step; a blunt cut would break the paragraph.
    by_chapter: dict[str, list[Collapse]] = {}
    for c in collapses:
        if c.embedded:
            continue
        by_chapter.setdefault(c.chapter_slug, []).append(c)
    files = {chapter_slug(p): p for p in list_chapter_files(book_dir)}
    counts: dict[str, int] = {}
    for slug, cs in by_chapter.items():
        p = files[slug]
        text = p.read_text(encoding="utf-8")
        for c in sorted(cs, key=lambda x: x.start, reverse=True):
            text = text[: c.start] + c.callback + text[c.end :]
        p.write_text(text, encoding="utf-8")
        counts[slug] = len(cs)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("book_dir", type=Path)
    ap.add_argument("--apply", action="store_true", help="write edits (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="emit plan as JSON")
    ap.add_argument(
        "--skip",
        default="",
        help="comma-separated 1-based indices to leave untouched (operator veto after reviewing the dry-run)",
    )
    args = ap.parse_args()

    if not args.book_dir.is_dir():
        print(f"not a directory: {args.book_dir}", file=sys.stderr)
        return 2

    skip = {int(x) for x in args.skip.split(",") if x.strip().isdigit()}
    all_collapses = plan(args.book_dir)
    collapses = [c for i, c in enumerate(all_collapses, 1) if i not in skip]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "chapter": c.chapter_slug,
                        "home": c.home_slug,
                        "shared_shingles": c.shared,
                        "chars": c.end - c.start,
                        "original": c.original,
                        "callback": c.callback,
                    }
                    for c in collapses
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if not all_collapses:
        print(f"dedup_cross_chapter: {args.book_dir.name} — no cross-chapter doctrine repeats to collapse.")
        return 0

    auto = [c for i, c in enumerate(all_collapses, 1) if i not in skip and not c.embedded]
    flagged = [c for c in all_collapses if c.embedded]
    print(
        f"dedup_cross_chapter: {args.book_dir.name} — {len(all_collapses)} repeated passage(s): "
        f"{len(auto)} auto-collapsible, {len(flagged)} need an authoring rewrite "
        f"(skipped: {sorted(skip) or 'none'}):\n"
    )
    for i, c in enumerate(all_collapses, 1):
        if i in skip:
            kind = "SKIP"
        elif c.embedded:
            kind = "REWRITE"  # woven into unique prose — hand to authoring, never blunt-cut
        else:
            kind = "AUTO"
        tag = " [scripture/quote]" if c.scripture_hint else ""
        print(f"  #{i} [{kind}] [{c.shared} shingles]{tag} in '{c.chapter_slug}' -> home '{c.home_slug}'")
        print(f"      passage ({c.end - c.start} chars): {c.original[:120].strip()}...\n")

    if args.apply:
        counts = apply_collapses(args.book_dir, [c for i, c in enumerate(all_collapses, 1) if i not in skip])
        if counts:
            print("Auto-collapsed (standalone repeats):")
            for slug, n in sorted(counts.items()):
                print(f"  {slug}: {n} passage(s)")
        else:
            print("No standalone repeats to auto-collapse.")
        if flagged:
            print(
                f"\n{len(flagged)} embedded repeat(s) left untouched — they need an authoring "
                f"rewrite (fold the repeat into a one-line callback, preserving the unique prose)."
            )
    else:
        print("(dry-run — re-run with --apply to write standalone collapses; REWRITE items are never auto-edited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
