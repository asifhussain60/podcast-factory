"""_book_completeness.py — did every planned chapter actually land in the book?

Split out of ``_translation_text.py`` (DR-005 line-cap, 2026-08-15) the same day
these two checks were added, so the split carries no history of its own to lose.

Both checks run inside ``compose_book_v2``, between the faithful base compose
and the articulation (fluency) pass — after chapters exist, before the
(expensive) pass that polishes them. ``chapter_completeness_findings`` HALTS
compose on a confirmed defect (a missing or badly under-length chapter);
``source_coverage_gap_findings`` is advisory only, logged and never blocking,
since dropping front matter from chapter coverage is correct behaviour.
"""

from __future__ import annotations

from typing import Any

from _translation_text import _MIN_ACCEPTABLE_RATIO


def chapter_completeness_findings(
    toc_chapters: list[dict[str, Any]],
    manifest_chapters: list[dict[str, Any]],
) -> list[str]:
    """Every chapter book-toc.json planned must have landed in book.md with real content.

    The base-compose loop cannot silently DROP a toc entry — it appends a manifest
    entry and a `## ` heading for every one, unconditionally (see
    ``author_translation_edition_compose``'s per-chapter loop). What it CAN do is
    keep a chapter that came back badly under-length: a compose retry that is still
    too compressed on the second attempt logs a warning and moves on rather than
    raising (``_translation_chunk._compose_one``), so a gutted chapter can reach
    the assembled book with nothing upstream having refused it. This is that check,
    reusing the SAME ratio ``_translation_long_enough`` already judges a single
    chapter by, but as a final pass over the whole assembled book rather than a
    per-chunk cache decision.
    """
    findings: list[str] = []
    by_index = {int(m["index"]): m for m in manifest_chapters if m.get("index") is not None}
    for ch in toc_chapters:
        idx = int(ch.get("bk_index") or 0)
        title = str(ch.get("title") or f"Chapter {idx}")
        entry = by_index.get(idx)
        if entry is None:
            findings.append(f"chapter {idx} ({title}): missing from the composed book — no manifest entry")
            continue
        source_words = int(entry.get("source_words") or 0)
        output_words = int(entry.get("output_words") or 0)
        if source_words < 200:
            continue
        if output_words == 0:
            findings.append(f"chapter {idx} ({title}): composed with no content (0 words)")
        elif output_words < _MIN_ACCEPTABLE_RATIO * source_words:
            findings.append(
                f"chapter {idx} ({title}): only {output_words}/{source_words} source words survived compose"
            )
    return findings


#: Below this many consecutive unclaimed source lines, a gap reads as ordinary
#: front matter (a title page, the source's own table of contents, a translator's
#: note) — which ``_authoring._book_design`` deliberately excludes from chapter
#: coverage. Above it, a gap is long enough to plausibly hide a dropped teaching
#: and is worth a human's attention.
_MIN_NOTABLE_GAP_LINES = 40


def source_coverage_gap_findings(toc: dict[str, Any], total_lines: int) -> list[str]:
    """Contiguous stretches of the numbered source no chapter (or the preface)
    claims — ADVISORY only, never a reason to halt compose.

    Dropping front matter is correct behaviour, not a defect, so a handful of
    short gaps is expected on every book. This only surfaces a gap long enough
    that it is more likely to be a chapter-design mistake (a source division the
    model's segmentation skipped over) than an intentional exclusion — a human
    judgment call the design prompt cannot fully guarantee on its own (rule 3
    tells the model every instructive line must be covered; nothing before this
    verified it).
    """
    if total_lines <= 0:
        return []
    covered = bytearray(total_lines + 1)
    ranges: list[Any] = []
    preface = toc.get("preface") or {}
    if preface.get("include"):
        ranges.extend(preface.get("source_line_ranges") or [])
    for ch in toc.get("chapters", []):
        ranges.extend(ch.get("source_line_ranges") or [])
    for r in ranges:
        if not isinstance(r, (list, tuple)) or len(r) != 2:
            continue
        start, end = int(r[0]), int(r[1])
        for i in range(max(1, start), min(total_lines, end) + 1):
            covered[i] = 1

    findings: list[str] = []
    gap_start: int | None = None
    for i in range(1, total_lines + 2):
        is_covered = i <= total_lines and covered[i]
        if not is_covered and gap_start is None:
            gap_start = i
        elif is_covered and gap_start is not None:
            gap_len = i - gap_start
            if gap_len >= _MIN_NOTABLE_GAP_LINES:
                findings.append(f"lines {gap_start}-{i - 1} ({gap_len} lines) not assigned to any chapter")
            gap_start = None
    return findings
