#!/usr/bin/env python3
"""chapter_density_audit.py — Concept-density auditor for podcast-factory chapters.

USAGE
-----
  # Audit all books across every bucket:
  python3 scripts/podcast/chapter_density_audit.py

  # Audit a single book slug:
  python3 scripts/podcast/chapter_density_audit.py --slug the-master-and-the-disciple

  # Output JSON for downstream tooling:
  python3 scripts/podcast/chapter_density_audit.py --json

  # Show only chapters that exceed the density threshold:
  python3 scripts/podcast/chapter_density_audit.py --violations-only

  # Emit a remediation plan (suggested splits):
  python3 scripts/podcast/chapter_density_audit.py --remediate

WHAT IT MEASURES
----------------
A "concept" is one ## H2 section in a rendered chapter .txt file, minus
bookkeeping frames ("Where this episode opens/picks up", "What this episode
lands") which carry no new content.

Target density (configurable via --max-concepts, default 3):
  - PASS   : concept_count <= max_concepts
  - WARN   : concept_count == max_concepts + 1
  - FAIL   : concept_count  > max_concepts + 1

Additional signals:
  - words_per_concept  : average word count per concept section
  - density_score      : 0–10 composite (lower = less dense = better)
    computed as min(10, concept_count * words_per_concept / TARGET_WORDS)
    where TARGET_WORDS = max_concepts * 1800

EXIT CODES
----------
  0  all chapters pass
  1  at least one FAIL chapter
  2  fatal (no chapters found, bad args)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import iter_content, slug_of
from _validator_constants import EPISODE_MAX_CONCEPTS

# ── repo root -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"

# ── density constants ---------------------------------------------------------
# Single source of truth lives in _validator_constants.EPISODE_MAX_CONCEPTS
# (shared with the Phase 0d post-write gate and the preflight smoke gate).
DEFAULT_MAX_CONCEPTS = EPISODE_MAX_CONCEPTS  # target: ≤3 concept sections per episode
TARGET_WORDS_PER_CONCEPT = 1800  # ~18 minutes of podcast audio at 150 wpm
WARN_THRESHOLD_DELTA = 1  # WARN if exactly max+1

# H2 headings that are purely structural frames, not concepts.
# Enrichment rewrites frame headings with variant nouns ("Where the dialogue
# opens", "Where this teaching opens", "What this episode lands for the
# listener") — match the frame SHAPE, not one fixed noun (2026-06-10).
# "stands" added 2026-06-11: enrichment emits "Where the argument stands" as
# the opening frame on late dialectical chapters (observed on
# the-master-and-the-disciple ch18b/ch19c — counted as a 4th concept without it).
_FRAME_PATTERNS = re.compile(
    r"^##\s+(where\s+(this|the)\s+\w+\s+(opens|picks\s+up|begins|stands)\b.*"
    r"|what\s+(this|the)\s+[\w'-]+(\s+[\w'-]+)*?\s+(lands?|leaves?|lays\s+down)\b.*"
    r"|closing\s*(turn|reflection)?"
    r"|the\s+frame)"
    r"\s*$",
    re.IGNORECASE,
)


# ── data model ----------------------------------------------------------------
@dataclass
class ConceptSection:
    title: str
    word_count: int
    is_frame: bool


@dataclass
class ChapterDensity:
    book_slug: str
    bucket: str
    chapter_file: str  # bare filename, no path
    chapter_path: Path = field(repr=False)
    sections: list[ConceptSection] = field(default_factory=list)
    total_words: int = 0
    max_concepts: int = DEFAULT_MAX_CONCEPTS

    # computed
    @property
    def concept_sections(self) -> list[ConceptSection]:
        return [s for s in self.sections if not s.is_frame]

    @property
    def frame_sections(self) -> list[ConceptSection]:
        return [s for s in self.sections if s.is_frame]

    @property
    def concept_count(self) -> int:
        return len(self.concept_sections)

    @property
    def words_per_concept(self) -> float:
        """Average words per concept, computed over the WHOLE file.

        Includes preamble and frame-section words in the numerator by
        design — the figure approximates per-concept listening load for
        the full episode, not just the concept bodies.
        """
        return self.total_words / self.concept_count if self.concept_count else 0.0

    @property
    def density_score(self) -> float:
        """0–10 composite: higher = more dense. 10 = very dense."""
        if self.concept_count == 0:
            return 0.0
        target = self.max_concepts * TARGET_WORDS_PER_CONCEPT
        raw = (self.concept_count * self.words_per_concept) / target
        return round(min(10.0, raw * 10), 1)

    @property
    def status(self) -> str:
        if self.concept_count <= self.max_concepts:
            return "PASS"
        elif self.concept_count == self.max_concepts + WARN_THRESHOLD_DELTA:
            return "WARN"
        else:
            return "FAIL"

    @property
    def suggested_splits(self) -> list[list[str]]:
        """Return concept titles grouped into target-sized chunks."""
        titles = [s.title for s in self.concept_sections]
        if self.concept_count <= self.max_concepts:
            return [titles]
        n_parts = math.ceil(self.concept_count / self.max_concepts)
        chunk_size = math.ceil(self.concept_count / n_parts)
        return [titles[i : i + chunk_size] for i in range(0, len(titles), chunk_size)]

    def to_dict(self) -> dict:
        return {
            "book_slug": self.book_slug,
            "bucket": self.bucket,
            "chapter_file": self.chapter_file,
            "total_words": self.total_words,
            "concept_count": self.concept_count,
            "words_per_concept": round(self.words_per_concept),
            "density_score": self.density_score,
            "status": self.status,
            "concepts": [s.title for s in self.concept_sections],
            "frames": [s.title for s in self.frame_sections],
            "suggested_splits": self.suggested_splits,
        }


# ── parsing -------------------------------------------------------------------


def _parse_chapter(path: Path) -> list[ConceptSection]:
    """Split chapter text into sections by ## headings."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections: list[ConceptSection] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def _flush():
        if current_title is not None:
            body = "\n".join(current_lines)
            word_count = len(body.split())
            is_frame = bool(_FRAME_PATTERNS.match(f"## {current_title}"))
            sections.append(
                ConceptSection(
                    title=current_title,
                    word_count=word_count,
                    is_frame=is_frame,
                )
            )

    for line in lines:
        if line.startswith("## "):
            _flush()
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    _flush()
    return sections


def _total_words(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def audit_chapter(
    path: Path,
    book_slug: str,
    bucket: str,
    max_concepts: int = DEFAULT_MAX_CONCEPTS,
) -> ChapterDensity:
    sections = _parse_chapter(path)
    total_words = _total_words(path)
    return ChapterDensity(
        book_slug=book_slug,
        bucket=bucket,
        chapter_file=path.name,
        chapter_path=path,
        sections=sections,
        total_words=total_words,
        max_concepts=max_concepts,
    )


def audit_book(
    book_dir: Path,
    max_concepts: int = DEFAULT_MAX_CONCEPTS,
) -> list[ChapterDensity]:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        return []
    txts = sorted(chapters_dir.glob("*.txt"))
    if not txts:
        return []
    # Bucket = first path segment under content/ (parent.name is wrong for
    # nested work-parent volumes); slug via the canonical resolver so
    # container volumes get their composite slug.
    try:
        bucket = book_dir.resolve().relative_to(CONTENT_ROOT.resolve()).parts[0]
    except ValueError:
        bucket = book_dir.parent.name
    slug = slug_of(book_dir)
    return [audit_chapter(p, slug, bucket, max_concepts) for p in txts]


def audit_all(
    max_concepts: int = DEFAULT_MAX_CONCEPTS,
    slug_filter: str | None = None,
) -> list[ChapterDensity]:
    """Audit every book via the canonical content resolver.

    iter_content() handles the type-first buckets, nested work-parent
    volumes (e.g. asaas-al-taveel/vol-0N), and the legacy layout — never
    re-implement bucket scanning here.
    """
    results: list[ChapterDensity] = []
    seen: set[Path] = set()
    for _status, _bucket, book_dir in iter_content():
        if book_dir.resolve() in seen:
            continue
        seen.add(book_dir.resolve())
        slug = slug_of(book_dir) if callable(slug_of) else book_dir.name
        if slug_filter and slug_filter not in (slug, book_dir.name):
            continue
        results.extend(audit_book(book_dir, max_concepts))
    return results


# ── reporting -----------------------------------------------------------------

_STATUS_ICON = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
_STATUS_COLOUR = {"PASS": "", "WARN": "", "FAIL": ""}


def _render_text_report(results: list[ChapterDensity], remediate: bool = False) -> str:
    if not results:
        return "No chapters found.\n"

    lines: list[str] = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║          PODCAST-FACTORY — CHAPTER DENSITY AUDIT             ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    # ── per-book grouping
    books: dict[str, list[ChapterDensity]] = {}
    for r in results:
        key = f"{r.bucket}/{r.book_slug}"
        books.setdefault(key, []).append(r)

    total_pass = sum(1 for r in results if r.status == "PASS")
    total_warn = sum(1 for r in results if r.status == "WARN")
    total_fail = sum(1 for r in results if r.status == "FAIL")

    for book_key, chapters in books.items():
        lines.append(f"┌─ {book_key}")
        for ch in chapters:
            icon = _STATUS_ICON[ch.status]
            lines.append(
                f"│  {icon} {ch.chapter_file:<55} "
                f"concepts={ch.concept_count:>2}  "
                f"words={ch.total_words:>5}  "
                f"density={ch.density_score:>4.1f}/10"
            )
            if ch.concept_count > 0:
                for i, s in enumerate(ch.concept_sections, 1):
                    lines.append(f"│       {i:>2}. {s.title} ({s.word_count}w)")
        lines.append("│")

        if remediate:
            fails = [ch for ch in chapters if ch.status in ("WARN", "FAIL")]
            if fails:
                lines.append("│  ── REMEDIATION PLAN ──────────────────────────────────────")
                for ch in fails:
                    splits = ch.suggested_splits
                    if len(splits) <= 1:
                        continue
                    lines.append(f"│  {ch.chapter_file} → split into {len(splits)} sub-episodes:")
                    for j, group in enumerate(splits, 1):
                        group_words = sum(s.word_count for s in ch.concept_sections if s.title in group)
                        lines.append(f"│    Sub-episode {j} (~{group_words}w):")
                        for title in group:
                            lines.append(f"│       - {title}")
                lines.append("│")

        lines.append("└" + "─" * 64)
        lines.append("")

    lines.append(
        f"SUMMARY: {len(results)} chapters total | ✅ {total_pass} PASS | ⚠️  {total_warn} WARN | ❌ {total_fail} FAIL"
    )
    lines.append(f"Target: ≤{results[0].max_concepts} concept sections per chapter")
    lines.append("")
    return "\n".join(lines)


# ── CLI -----------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Audit chapter concept density across all podcast-factory books.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--slug", metavar="SLUG", help="Audit only this book slug.")
    p.add_argument(
        "--max-concepts",
        type=int,
        default=DEFAULT_MAX_CONCEPTS,
        metavar="N",
        help=f"Maximum concepts per chapter (default {DEFAULT_MAX_CONCEPTS}).",
    )
    p.add_argument(
        "--violations-only",
        action="store_true",
        help="Only show WARN and FAIL chapters.",
    )
    p.add_argument(
        "--remediate",
        action="store_true",
        help="Include suggested split plans for over-dense chapters.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON (machine-readable).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    results = audit_all(max_concepts=args.max_concepts, slug_filter=args.slug)

    if not results:
        print("No chapters found.", file=sys.stderr)
        return 2

    if args.violations_only:
        results = [r for r in results if r.status in ("WARN", "FAIL")]
        if not results:
            print("All chapters within density target. ✅")
            return 0

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(_render_text_report(results, remediate=args.remediate))

    any_fail = any(r.status == "FAIL" for r in results)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
