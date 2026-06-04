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

Severity mapping (default; the challenger may override):

  P1, P4 → P0 (blocks ship)
  P3, P5 → P1 (ship-with-caution)
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
            cur_list = None
            cur_map = None
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
            findings.append({
                "check": "P1", "severity": "P0", "slug": slug,
                "msg": f"title {title!r} duplicates chapter {seen[norm]!r}",
            })
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
            findings.append({
                "check": "P2", "severity": "P0", "slug": slug,
                "msg": f"title is {len(title)} chars (>60); INVARIANT 6 hard cap",
            })
        elif len(title.split()) > 6:
            findings.append({
                "check": "P2", "severity": "P2", "slug": slug,
                "msg": f"title is {len(title.split())} words (>6); INVARIANT 6 soft target",
            })
    return findings


def check_title_non_generic(contracts: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for slug, c in contracts.items():
        title = (c.get("title") or "").strip()
        if not title:
            findings.append({
                "check": "P3", "severity": "P1", "slug": slug,
                "msg": "title is empty",
            })
            continue
        for pat in GENERIC_TITLE_RES:
            if pat.match(title):
                findings.append({
                    "check": "P3", "severity": "P1", "slug": slug,
                    "msg": f"title {title!r} matches generic pattern {pat.pattern!r}",
                })
                break
    return findings


def check_band_fit(chapter_word_counts: dict[str, int], contracts: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for slug, wc in chapter_word_counts.items():
        c = contracts.get(slug)
        if c is None:
            findings.append({
                "check": "P4", "severity": "P1", "slug": slug,
                "msg": f"chapter has no contract; cannot verify band fit ({wc} words)",
            })
            continue
        band = (c.get("length_target") or "default_deep_dive").lower()
        lo, hi = LENGTH_BANDS.get(band, LENGTH_BANDS["default_deep_dive"])
        if wc < lo or wc > hi:
            findings.append({
                "check": "P4", "severity": "P0", "slug": slug,
                "msg": f"chapter is {wc} words; declared band {band!r} is {lo}-{hi}",
            })
    return findings


def check_set_balance(chapter_word_counts: dict[str, int]) -> list[dict]:
    counts = list(chapter_word_counts.values())
    if len(counts) < 2:
        return []
    lo, hi = min(counts), max(counts)
    variance = (hi - lo) / hi if hi else 0
    if variance > 0.30:
        return [{
            "check": "P5", "severity": "P1", "slug": "<set>",
            "msg": (
                f"chapter-set word-count variance is {variance:.0%} "
                f"(min={lo}, max={hi}); >30% indicates the shape is uneven"
            ),
        }]
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
                    findings.append({
                        "check": "P6", "severity": "P2", "slug": slug,
                        "msg": (
                            f"chapter text contains {signal!r} which belongs to "
                            f"book {other_book!r}'s mangle-map; possible cross-book bleed"
                        ),
                    })
    return findings


# ─── main ─────────────────────────────────────────────────────────────────────


def run(book_dir: Path) -> tuple[list[dict], int]:
    if not book_dir.is_dir():
        return ([{
            "check": "FATAL", "severity": "P0", "slug": "<book>",
            "msg": f"BOOK_DIR not found: {book_dir}",
        }], 0)

    book_slug = book_dir.name
    chapter_files = list_chapter_files(book_dir)
    if not chapter_files:
        return ([{
            "check": "INFO", "severity": "P2", "slug": "<book>",
            "msg": "no chapters yet; nothing to check (run Phase 0a–0d first)",
        }], 0)

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

    return findings, len(chapter_files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("book_dir", type=Path, help="_workspace/<category>/<book-slug>/")
    ap.add_argument("--format", choices=("json", "text"), default="json")
    args = ap.parse_args()

    findings, n_chapters = run(args.book_dir.resolve())

    if args.format == "json":
        json.dump({
            "book": args.book_dir.name,
            "chapters": n_chapters,
            "findings": findings,
        }, sys.stdout, indent=2)
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
