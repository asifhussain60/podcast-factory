#!/usr/bin/env python3
"""check_chapter_set.py — book-scope design-quality checks for the podcast-challenger Category P.

Reads a BOOK_DIR and emits a JSON list of findings on stdout. The challenger
agent invokes this via Bash and folds the JSON into its sidecar report.

Checks (per SKILL.md INVARIANT 6 + Category P in .github/agents/podcast-challenger.agent.md):

  P1  title-uniqueness        chapter titles unique within the book (case-insensitive)
  P2  title-conciseness       title ≤60 chars (hard); ≤6 words (soft advisory)
  P3  title-non-generic       title not "Chapter N" / "Introduction continued" /
                              "<Author> on X" / starts with "[TODO]"
  P4  band-fit                each chapter's word count lands in the band declared
                              in contract.length_target
                                brief:  1000–1800
                                default_deep_dive: 1800–2800
                                longer: 2800–4500
  P5  set-balance             ≤30% word-count variance across all chapters
  P6  cross-book-bleed        chapter text contains no slug or canonical-mangle-map
                              entry from any OTHER book

Chapter-set integrity wave (2026-06-10, docs/standards/chapter-density.md):

  P7  source-coverage         the union of Phase 0d source_chapters line ranges
                              covers the refined source — nothing silently DROPPED
                              (front/back-matter tolerance; needs _chunks/0d/source-toc.json)
  P8  no-duplication          (a) source line ranges do not overlap; (b) no
                              cross-chapter n-gram duplication of concept prose
  P9  sermon-integrity        every contract `sermon.present` section exists WHOLE
                              as an H2 in exactly ONE chapter of the set
  P10 set-density             per-chapter concept count within the density target
                              (advisory here; the $0 preflight gate does the halting)

Severity mapping (default; the challenger may override):

  P1, P4, P8(overlap), P9 → P0 (blocks ship)
  P3, P5, P7, P8(ngram), P10 → P1 (ship-with-caution)
  P2, P6 → P2 (advisory)

Usage:
  python3 scripts/podcast/check_chapter_set.py <BOOK_DIR>
  python3 scripts/podcast/check_chapter_set.py <BOOK_DIR> --format text

Exit codes:
  0 — no P0 findings (P1/P2 may exist)
  1 — at least one P0 finding
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _paths import REPO_ROOT

LIBRARY_DIR = REPO_ROOT / "content" / "drafts"

# Length-target → (min, max) inclusive bands. Per SKILL.md INVARIANT 6.
# Extended Deep Dive (~30–45 min audio) is the recommended default for dense /
# philosophical / technical sources; it requires explicit length steering in
# the customize prompt. See SKILL.md Phase 0d "Choosing the tier" and
# notebooklm-best-practices.md §3.
LENGTH_BANDS = {
    "brief": (1000, 1800),
    "default_deep_dive": (1800, 2800),
    "longer": (2800, 4500),
    "extended": (5500, 9500),
}

# Title is "generic" if it matches any of these patterns (case-insensitive).
GENERIC_TITLE_RES = [
    re.compile(r"^chapter\s+\d", re.IGNORECASE),
    re.compile(r"^introduction\s+continued", re.IGNORECASE),
    re.compile(r"^untitled", re.IGNORECASE),
    re.compile(r"^\[TODO\]"),
]


# ─── tiny YAML reader (mirrors extract_chapter.py's subset) ───────────────────


def _scalar(s: str):
    s = s.strip()
    if s.lower() in ("", "null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def parse_contract(text: str) -> dict:
    """Parse the subset of YAML used in chapter-contract.yml: top-level scalars,
    one-line lists ([]), block lists (`- item`), and block mappings."""
    out: dict = {}
    cur_key: str | None = None
    cur_list: list | None = None
    cur_map: dict | None = None
    for raw in text.splitlines():
        if raw.startswith("#") or raw.strip() == "":
            continue
        if not raw.startswith(" ") and ":" in raw:
            # New top-level key flushes anything in progress.
            cur_key = None
            cur_list = None  # noqa: F841
            cur_map = None  # noqa: F841
            k, sep, v = raw.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "":
                cur_key = k
                out[k] = None
            elif v == "[]":
                out[k] = []
            elif v == "{}":
                out[k] = {}
            else:
                out[k] = _scalar(v)
        elif raw.lstrip().startswith("- ") and cur_key is not None:
            item = raw.lstrip()[2:].strip()
            if not isinstance(out.get(cur_key), list):
                out[cur_key] = []
            out[cur_key].append(_scalar(item))
        elif raw.startswith("  ") and cur_key is not None and ":" in raw:
            k, _, v = raw.strip().partition(":")
            if not isinstance(out.get(cur_key), dict):
                out[cur_key] = {}
            out[cur_key][k.strip()] = _scalar(v) if v.strip() else None
    return out


# ─── load helpers ─────────────────────────────────────────────────────────────


def list_chapter_files(book_dir: Path) -> list[Path]:
    return sorted((book_dir / "chapters").glob("ch*.txt"))


def chapter_slug(p: Path) -> str:
    m = re.match(r"^ch(\d+)[a-z]?-(.+)$", p.stem)
    return m.group(2) if m else p.stem


def chapter_num(p: Path) -> int | None:
    m = re.match(r"^ch(\d+)[a-z]?-(.+)$", p.stem)
    return int(m.group(1)) if m else None


def load_contract_for(book_dir: Path, slug: str) -> dict | None:
    f = book_dir / "chapter-contracts" / f"{slug}.yml"
    if not f.exists():
        return None
    return parse_contract(f.read_text(encoding="utf-8"))


def word_count(text: str) -> int:
    return len(text.split())


def load_other_book_signals() -> dict[str, list[str]]:
    """Build a {book-slug → [canonical names + book-slug variants]} dict for
    every book except the one being checked. Caller filters out the in-scope book."""
    out: dict[str, list[str]] = {}
    if not LIBRARY_DIR.exists():
        return out
    for cat in sorted(LIBRARY_DIR.iterdir()):
        if not cat.is_dir():
            continue
        for book in sorted(cat.iterdir()):
            if not book.is_dir():
                continue
            mangle = book / "_system" / "mangle-map.md"
            # Require a mangle-map to treat a directory as a book. Without this,
            # sibling subdirs under _workspace/ (e.g. plan/view, plan/research)
            # get added as signals by their bare name, false-positiving on
            # ordinary English prose.
            if not mangle.exists():
                continue
            signals: list[str] = []
            for raw in mangle.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line.startswith("|") or line.startswith("|---") or line.startswith("| Canonical"):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells and cells[0]:
                    signals.append(cells[0])
            # Also include the book-slug itself.
            signals.append(book.name)
            out[book.name] = sorted(set(s for s in signals if s))
    return out


# ─── checks ───────────────────────────────────────────────────────────────────


def check_title_uniqueness(contracts: dict[str, dict]) -> list[dict]:
    seen: dict[str, str] = {}
    findings: list[dict] = []
    for slug, c in contracts.items():
        title = (c.get("title") or "").strip()
        if not title:
            continue
        norm = title.lower()
        if norm in seen and seen[norm] != slug:
            findings.append(
                {
                    "check": "P1",
                    "severity": "P0",
                    "slug": slug,
                    "msg": f"title {title!r} duplicates chapter {seen[norm]!r}",
                }
            )
        else:
            seen[norm] = slug
    return findings


def check_title_conciseness(contracts: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for slug, c in contracts.items():
        title = (c.get("title") or "").strip()
        if not title:
            continue
        if len(title) > 60:
            findings.append(
                {
                    "check": "P2",
                    "severity": "P0",
                    "slug": slug,
                    "msg": f"title is {len(title)} chars (>60); INVARIANT 6 hard cap",
                }
            )
        elif len(title.split()) > 6:
            findings.append(
                {
                    "check": "P2",
                    "severity": "P2",
                    "slug": slug,
                    "msg": f"title is {len(title.split())} words (>6); INVARIANT 6 soft target",
                }
            )
    return findings


def check_title_non_generic(contracts: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for slug, c in contracts.items():
        title = (c.get("title") or "").strip()
        if not title:
            findings.append(
                {
                    "check": "P3",
                    "severity": "P1",
                    "slug": slug,
                    "msg": "title is empty",
                }
            )
            continue
        for pat in GENERIC_TITLE_RES:
            if pat.match(title):
                findings.append(
                    {
                        "check": "P3",
                        "severity": "P1",
                        "slug": slug,
                        "msg": f"title {title!r} matches generic pattern {pat.pattern!r}",
                    }
                )
                break
    return findings


def _resolve_band(length_target) -> tuple[str, tuple[int, int]]:
    """Resolve a contract length_target into a (label, (lo, hi)) word band.

    Tolerates the three shapes contracts carry in the wild — a band TOKEN
    ('extended'), an explicit RANGE string ('5500-6000', en-dash allowed), or a
    single numeric TARGET (5800 as int or str). Previously this did
    ``(... or 'default_deep_dive').lower()`` which (a) crashed with
    AttributeError when length_target was an int, aborting the entire
    chapter-set run before the cross-chapter checks could execute, and (b)
    silently mis-banded range strings to default_deep_dive. Coercing to str and
    parsing each shape fixes both.
    """
    if length_target is None:
        return "default_deep_dive", LENGTH_BANDS["default_deep_dive"]
    s = str(length_target).strip().lower()
    if s in LENGTH_BANDS:
        return s, LENGTH_BANDS[s]
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", s)  # explicit range 'lo-hi'
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return s, ((lo, hi) if lo <= hi else (hi, lo))
    m = re.match(r"^(\d+)$", s)  # single numeric target
    if m:
        n = int(m.group(1))
        return s, (int(n * 0.85), int(n * 1.20))  # tolerance window
    return "default_deep_dive", LENGTH_BANDS["default_deep_dive"]


def check_band_fit(chapter_word_counts: dict[str, int], contracts: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for slug, wc in chapter_word_counts.items():
        c = contracts.get(slug)
        if c is None:
            findings.append(
                {
                    "check": "P4",
                    "severity": "P1",
                    "slug": slug,
                    "msg": f"chapter has no contract; cannot verify band fit ({wc} words)",
                }
            )
            continue
        band, (lo, hi) = _resolve_band(c.get("length_target"))
        if wc < lo or wc > hi:
            findings.append(
                {
                    "check": "P4",
                    "severity": "P0",
                    "slug": slug,
                    "msg": f"chapter is {wc} words; declared band {band!r} is {lo}-{hi}",
                }
            )
    return findings


def check_set_balance(chapter_word_counts: dict[str, int]) -> list[dict]:
    counts = list(chapter_word_counts.values())
    if len(counts) < 2:
        return []
    lo, hi = min(counts), max(counts)
    variance = (hi - lo) / hi if hi else 0
    if variance > 0.30:
        return [
            {
                "check": "P5",
                "severity": "P1",
                "slug": "<set>",
                "msg": (
                    f"chapter-set word-count variance is {variance:.0%} "
                    f"(min={lo}, max={hi}); >30% indicates the shape is uneven"
                ),
            }
        ]
    return []


def check_cross_book_bleed(book_slug: str, chapters: dict[str, str]) -> list[dict]:
    other = load_other_book_signals()
    other.pop(book_slug, None)
    findings: list[dict] = []
    for slug, body in chapters.items():
        for other_book, signals in other.items():
            for signal in signals:
                # Substring search; case-insensitive. Word-boundary anchor to
                # reduce false positives on common words (e.g. a 4-char book-slug).
                if len(signal) < 4:
                    continue
                if re.search(rf"(?i)\b{re.escape(signal)}\b", body):
                    findings.append(
                        {
                            "check": "P6",
                            "severity": "P2",
                            "slug": slug,
                            "msg": (
                                f"chapter text contains {signal!r} which belongs to "
                                f"book {other_book!r}'s mangle-map; possible cross-book bleed"
                            ),
                        }
                    )
    return findings


# ─── chapter-set integrity wave (2026-06-10) ──────────────────────────────────

# Lines of refined source allowed to fall outside every episode's line range
# before P7 flags a coverage gap (front/back matter, blank runs).
COVERAGE_GAP_TOLERANCE = 40
# Concept `## H2` section headings should read like headings, not statements.
# Target the same soft word cap as INVARIANT 6 chapter titles. Structural frames
# (openers/landings/closing) are excluded — they carry their own canonical shape.
HEADING_MAX_WORDS = 6
# Cross-chapter duplication: shingle size + how many distinct shared shingles
# between a chapter pair count as duplication (conservative on purpose).
SHINGLE_N = 12
SHINGLE_DUP_THRESHOLD = 3
# Formulaic phrases excluded from duplication shingles (legitimately recur).
_DUP_EXCLUDE_SUBSTRINGS = (
    "peace and blessings",
    "peace be upon",
    "praise be to allah",
    "commander of the faithful",
)
# Inline bibliographic citations are quoted apparatus, not teaching content. A
# scholarly book cites the same source (Daftary, Corbin, Halm, the canonical
# hadith collections) in several chapters by design — that is good scholarship,
# NOT "the same content taught twice". Strip parenthetical/bracketed citation
# spans before shingling so the cross-chapter dedup measures repeated PROSE, not
# repeated attribution. A span counts as a citation when, between its delimiters,
# it carries a publisher, edition/translation marker, page marker, or 4-digit
# year. (Verbatim scripture is handled by author judgment, not here.)
_CITATION_MARKER = (
    r"(?:university\s+press|cambridge|oxford|brill|crossroad|darussalam"
    r"|\bed\.|\bedition\b|\btrans\b|\bvol\.|\bpp\.|\bp\.\s*\d"
    r"|\b1[0-9]{3}\b|\b20[0-9]{2}\b)"
)
# Two delimiter forms — a parenthetical ref may carry inner brackets and a
# bracketed ref may carry inner parens (e.g. "[Corbin ... (London: Kegan Paul,
# 1983), pp. 84-86.]"), so each pattern excludes only its OWN delimiter from the
# span body and tolerates the other nested inside.
_CITATION_SPAN_RES = (
    re.compile(r"\([^()]*" + _CITATION_MARKER + r"[^()]*\)", re.IGNORECASE),
    re.compile(r"\[[^\[\]]*" + _CITATION_MARKER + r"[^\[\]]*\]", re.IGNORECASE),
)
# Minimum words for a sermon section to count as "captured whole", not a stub.
SERMON_MIN_WORDS = 150

_SERMON_PRESENT_RE = re.compile(r"^sermon:\s*$", re.MULTILINE)
# Capture the rest of the line; symmetric surrounding quotes are stripped at
# the use site. (The prior [^\"'\n]+ body truncated titles at embedded
# apostrophes — "The Sheikh's opening praise" became "The Sheikh" — a false P9.)
_SERMON_TITLE_RE = re.compile(r"section_title:\s*(.+)")


def _load_source_toc(book_dir: Path) -> list[dict] | None:
    toc = book_dir / "_system" / "source" / "text" / "_chunks" / "0d" / "source-toc.json"
    if not toc.is_file():
        return None
    try:
        data = json.loads(toc.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    scs = data.get("source_chapters") if isinstance(data, dict) else None
    if not isinstance(scs, list):
        return None
    ranges = []
    for sc in scs:
        try:
            ranges.append(
                {
                    "sc_index": int(sc.get("sc_index", 0)),
                    "start": int(sc["start_line"]),
                    "end": int(sc["end_line"]),
                    "title": str(sc.get("source_title", "?")),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return ranges or None


def check_source_coverage(book_dir: Path) -> list[dict]:
    """P7: union of source_chapters line ranges covers the refined source."""
    ranges = _load_source_toc(book_dir)
    if ranges is None:
        return []  # legacy book (pre-source-toc) — vacuous pass
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined.is_file():
        return []
    n_lines = len(refined.read_text(encoding="utf-8").splitlines())
    ordered = sorted(ranges, key=lambda r: r["start"])
    findings: list[dict] = []
    cursor = 1
    for r in ordered:
        gap = r["start"] - cursor
        if gap > COVERAGE_GAP_TOLERANCE:
            findings.append(
                {
                    "check": "P7",
                    "severity": "P1",
                    "slug": "<set>",
                    "msg": (
                        f"source lines {cursor}-{r['start'] - 1} ({gap} lines) are not "
                        f"assigned to any episode (next assigned: sc {r['sc_index']} "
                        f"{r['title']!r}) — content silently dropped from the split"
                    ),
                }
            )
        cursor = max(cursor, r["end"] + 1)
    tail_gap = n_lines - cursor + 1
    if tail_gap > COVERAGE_GAP_TOLERANCE:
        findings.append(
            {
                "check": "P7",
                "severity": "P1",
                "slug": "<set>",
                "msg": (
                    f"source lines {cursor}-{n_lines} ({tail_gap} lines) after the last "
                    f"assigned range are not covered by any episode"
                ),
            }
        )
    return findings


def check_source_overlap(book_dir: Path) -> list[dict]:
    """P8a: source line ranges must not overlap (no content doubled at the plan)."""
    ranges = _load_source_toc(book_dir)
    if ranges is None:
        return []
    ordered = sorted(ranges, key=lambda r: r["start"])
    findings: list[dict] = []
    for prev, cur in zip(ordered, ordered[1:]):
        if cur["start"] <= prev["end"]:
            findings.append(
                {
                    "check": "P8",
                    "severity": "P0",
                    "slug": "<set>",
                    "msg": (
                        f"source ranges overlap: sc {prev['sc_index']} {prev['title']!r} "
                        f"({prev['start']}-{prev['end']}) and sc {cur['sc_index']} "
                        f"{cur['title']!r} ({cur['start']}-{cur['end']}) — the same "
                        f"source lines feed two episodes"
                    ),
                }
            )
    return findings


def _concept_shingles(text: str) -> set[tuple[str, ...]]:
    """Normalized SHINGLE_N-grams of the chapter's CONCEPT prose (frames excluded)."""
    # Drop frame sections by heading.
    parts: list[str] = []
    keep = True
    for line in text.splitlines():
        if line.startswith("## "):
            keep = not re.match(
                r"^##\s+(where\s+this\s+episode|what\s+this\s+episode\s+lands|closing)",
                line,
                re.IGNORECASE,
            )
            continue
        if keep:
            parts.append(line)
    body = " ".join(parts)
    for _cre in _CITATION_SPAN_RES:  # drop inline bibliographic citations
        body = _cre.sub(" ", body)
    tokens = re.findall(r"[a-z']+", body.lower())
    shingles: set[tuple[str, ...]] = set()
    for i in range(len(tokens) - SHINGLE_N + 1):
        gram = tuple(tokens[i : i + SHINGLE_N])
        joined = " ".join(gram)
        if any(x in joined for x in _DUP_EXCLUDE_SUBSTRINGS):
            continue
        shingles.add(gram)
    return shingles


def check_cross_chapter_duplication(chapters: dict[str, str]) -> list[dict]:
    """P8b: no chapter pair shares >= SHINGLE_DUP_THRESHOLD distinct n-grams."""
    slugs = sorted(chapters)
    shingle_map = {s: _concept_shingles(chapters[s]) for s in slugs}
    findings: list[dict] = []
    for i, a in enumerate(slugs):
        for b in slugs[i + 1 :]:
            shared = shingle_map[a] & shingle_map[b]
            if len(shared) >= SHINGLE_DUP_THRESHOLD:
                sample = " ".join(next(iter(shared)))
                findings.append(
                    {
                        "check": "P8",
                        "severity": "P1",
                        "slug": a,
                        "msg": (
                            f"chapters {a!r} and {b!r} share {len(shared)} distinct "
                            f"{SHINGLE_N}-word passages — same content taught twice. "
                            f'Sample: "{sample[:90]}…"'
                        ),
                    }
                )
    return findings


def _sermon_declarations(book_dir: Path) -> list[tuple[str, str]]:
    """Return (contract_slug, section_title) for contracts declaring a sermon.

    Raw-text scan (parser-independent): a `sermon:` block with `present: true`
    and a `section_title:` value.
    """
    out: list[tuple[str, str]] = []
    contracts_dir = book_dir / "chapter-contracts"
    if not contracts_dir.is_dir():
        return out
    for cf in sorted(contracts_dir.glob("*.yml")):
        text = cf.read_text(encoding="utf-8")
        if not _SERMON_PRESENT_RE.search(text):
            continue
        block = text[_SERMON_PRESENT_RE.search(text).end() :]
        if not re.search(r"present:\s*true", block):
            continue
        m = _SERMON_TITLE_RE.search(block)
        if m:
            title = m.group(1).strip()
            if len(title) >= 2 and title[0] == title[-1] and title[0] in "\"'":
                title = title[1:-1].strip()
            out.append((cf.stem, title))
    return out


def check_sermon_integrity(book_dir: Path, chapters: dict[str, str]) -> list[dict]:
    """P9: every declared sermon section exists WHOLE in exactly one chapter."""
    findings: list[dict] = []
    for contract_slug, section_title in _sermon_declarations(book_dir):
        heading_re = re.compile(rf"^##\s+\*?{re.escape(section_title)}\*?\s*$", re.MULTILINE | re.IGNORECASE)
        carriers = [s for s, body in chapters.items() if heading_re.search(body)]
        if not carriers:
            findings.append(
                {
                    "check": "P9",
                    "severity": "P0",
                    "slug": contract_slug,
                    "msg": (
                        f"contract declares sermon section {section_title!r} but no "
                        f"chapter carries that H2 — the sermon was dropped or fragmented"
                    ),
                }
            )
            continue
        if len(carriers) > 1:
            findings.append(
                {
                    "check": "P9",
                    "severity": "P0",
                    "slug": contract_slug,
                    "msg": (
                        f"sermon section {section_title!r} appears in {len(carriers)} "
                        f"chapters ({carriers}) — a sermon must live whole in exactly one"
                    ),
                }
            )
            continue
        body = chapters[carriers[0]]
        m = heading_re.search(body)
        rest = body[m.end() :]
        nxt = rest.find("\n## ")
        section = rest[:nxt] if nxt != -1 else rest
        n = len(section.split())
        if n < SERMON_MIN_WORDS:
            findings.append(
                {
                    "check": "P9",
                    "severity": "P1",
                    "slug": carriers[0],
                    "msg": (
                        f"sermon section {section_title!r} is only {n} words "
                        f"(<{SERMON_MIN_WORDS}) — likely a stub, not the sermon "
                        f"captured whole"
                    ),
                }
            )
    return findings


def check_section_heading_conciseness(chapters: dict[str, str]) -> list[dict]:
    """P11: concept `## H2` section headings read like headings, not statements
    (R-HEADING-CONCISE). Flags any non-frame heading over HEADING_MAX_WORDS words.
    Structural frames (openers/landings/closing) are excluded via the canonical
    frame regex. Advisory (P2) — display polish, never blocks ship."""
    try:
        from chapter_density_audit import _FRAME_PATTERNS
    except ImportError:
        return []
    findings: list[dict] = []
    for slug in sorted(chapters):
        for line in chapters[slug].splitlines():
            if not line.startswith("## "):
                continue
            if _FRAME_PATTERNS.match(line):
                continue
            heading = line[3:].strip()
            wc = len(heading.split())
            if wc > HEADING_MAX_WORDS:
                findings.append(
                    {
                        "check": "P11",
                        "severity": "P2",
                        "slug": slug,
                        "msg": (
                            f"section heading is {wc} words (>{HEADING_MAX_WORDS}): "
                            f"{heading[:64]!r} — write a short noun-phrase heading, "
                            f"not a full statement"
                        ),
                    }
                )
    return findings


def check_set_density(chapter_files: list[Path], book_slug: str) -> list[dict]:
    """P10: per-chapter concept-count within target (advisory at set level —
    the $0 preflight gate owns halting; this keeps the set view in the report)."""
    try:
        from chapter_density_audit import audit_chapter
    except ImportError:
        return []
    findings: list[dict] = []
    for cf in chapter_files:
        d = audit_chapter(cf, book_slug, "")
        if d.status == "FAIL":
            findings.append(
                {
                    "check": "P10",
                    "severity": "P1",
                    "slug": chapter_slug(cf),
                    "msg": (
                        f"{d.concept_count} concept sections (target ≤{d.max_concepts}) "
                        f"— over-dense; see docs/standards/chapter-density.md"
                    ),
                }
            )
    return findings


# ─── main ─────────────────────────────────────────────────────────────────────


def run(book_dir: Path) -> tuple[list[dict], int]:
    if not book_dir.is_dir():
        return (
            [
                {
                    "check": "FATAL",
                    "severity": "P0",
                    "slug": "<book>",
                    "msg": f"BOOK_DIR not found: {book_dir}",
                }
            ],
            0,
        )

    book_slug = book_dir.name
    chapter_files = list_chapter_files(book_dir)
    if not chapter_files:
        return (
            [
                {
                    "check": "INFO",
                    "severity": "P2",
                    "slug": "<book>",
                    "msg": "no chapters yet; nothing to check (run Phase 0a–0d first)",
                }
            ],
            0,
        )

    chapters: dict[str, str] = {chapter_slug(p): p.read_text(encoding="utf-8") for p in chapter_files}
    word_counts: dict[str, int] = {s: word_count(t) for s, t in chapters.items()}
    contracts: dict[str, dict] = {}
    for s in chapters:
        c = load_contract_for(book_dir, s)
        if c is not None:
            contracts[s] = c

    findings: list[dict] = []
    findings += check_title_uniqueness(contracts)
    findings += check_title_conciseness(contracts)
    findings += check_title_non_generic(contracts)
    findings += check_band_fit(word_counts, contracts)
    findings += check_set_balance(word_counts)
    findings += check_cross_book_bleed(book_slug, chapters)
    # Chapter-set integrity wave (2026-06-10) — P7–P10.
    findings += check_source_coverage(book_dir)
    findings += check_source_overlap(book_dir)
    findings += check_cross_chapter_duplication(chapters)
    findings += check_sermon_integrity(book_dir, chapters)
    findings += check_set_density(chapter_files, book_slug)
    findings += check_section_heading_conciseness(chapters)

    return findings, len(chapter_files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("book_dir", type=Path, help="_workspace/<category>/<book-slug>/")
    ap.add_argument("--format", choices=("json", "text"), default="json")
    args = ap.parse_args()

    findings, n_chapters = run(args.book_dir.resolve())

    if args.format == "json":
        json.dump(
            {
                "book": args.book_dir.name,
                "chapters": n_chapters,
                "findings": findings,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"check_chapter_set: {args.book_dir.name} ({n_chapters} chapter(s))")
        if not findings:
            print("  No findings.")
        else:
            for f in findings:
                print(f"  [{f['severity']}] {f['check']} · {f['slug']}: {f['msg']}")

    return 1 if any(f["severity"] == "P0" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
