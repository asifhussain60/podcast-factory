#!/usr/bin/env python3
"""kar_renumber_to_sequential.py — one-shot KaR rename to purely-sequential chNN/EP##.

Drops letter suffixes (3a, 4b, etc.) from chapter and episode filenames.
Source-baab provenance is preserved in chapter-contract YAML fields
(source_chapter_ref, section_index), so the filename redundancy can be removed.

Mapping (old → new):
  ch03a / EP03  → ch01 / EP01   (al-Kirmani Ch1 segment 1)
  ch04b / EP04  → ch02 / EP02   (al-Kirmani Ch1 segment 2)
  ch05c / EP05  → ch03 / EP03   (al-Kirmani Ch1 segment 3)
  ch01  / EP05.5 → ch04 / EP04  (chapter-group summary)
  ch06  / EP06  → ch05 / EP05
  ch07  / EP07  → ch06 / EP06
  ch08  / EP08  → ch07 / EP07
  ch09  / EP09  → ch08 / EP08
  ch10  / EP10  → ch09 / EP09
  ch11  / EP11  → ch10 / EP10
  ch12  / EP12  → ch11 / EP11
  ch13a / EP13  → ch12 / EP12   (al-Kirmani Ch9 segment 1)
  ch14b / EP14  → ch13 / EP13   (al-Kirmani Ch9 segment 2)
  ch15  / EP15  → ch14 / EP14
  ch99  / EP15.5 → ch15 / EP15  (book-end summary)

Runs in two passes:
  1. File renames (git mv): chapters/, episodes/, _system/episode-drafts/
  2. Content updates: chapter-contracts/*.yml + 6 system docs

Idempotent: re-running is a no-op if the new names already exist.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

BOOK_DIR = Path("content/podcast/library/books/kitab-al-riyad")

# Each entry: (slug, old_ch_prefix, new_ch_prefix, old_ep_id, new_ep_id, source_ch_ref, section_index)
RENAME_MAP = [
    ("the-perfect-and-the-perfection-of-the-soul",        "ch03a", "ch01", "EP03",   "EP01", 2, 1),
    ("soul-intellect-and-the-power-of-emanation",         "ch04b", "ch02", "EP04",   "EP02", 2, 2),
    ("the-soul-in-time-and-the-rejoinder-to-al-nusra",    "ch05c", "ch03", "EP05",   "EP03", 2, 3),
    ("summary-perfection-of-the-soul",                    "ch01",  "ch04", "EP05.5", "EP04", None, None),
    ("the-intellect-as-the-first-creation",               "ch06",  "ch05", "EP06",   "EP05", 3, 1),
    ("soul-and-spirit-one-substance-or-two",              "ch07",  "ch06", "EP07",   "EP06", 4, 1),
    ("souls-as-parts-or-traces",                          "ch08",  "ch07", "EP08",   "EP07", 5, 1),
    ("the-human-as-fruit-of-the-worlds",                  "ch09",  "ch08", "EP09",   "EP08", 6, 1),
    ("motion-stillness-hyle-and-form",                    "ch10",  "ch09", "EP10",   "EP09", 7, 1),
    ("the-sections-of-the-world",                         "ch11",  "ch10", "EP11",   "EP10", 8, 1),
    ("qada-and-qadar-fate-and-destiny",                   "ch12",  "ch11", "EP12",   "EP11", 9, 1),
    ("the-shariah-of-adam-and-the-first-speaker",         "ch13a", "ch12", "EP13",   "EP12", 10, 1),
    ("prophets-as-teachers-monotheism-and-the-ranks",     "ch14b", "ch13", "EP14",   "EP13", 10, 2),
    ("tawhid-and-the-critique-of-al-mahsul",              "ch15",  "ch14", "EP15",   "EP14", 11, 1),
    ("book-summary",                                      "ch99",  "ch15", "EP15.5", "EP15", None, None),
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def git_mv(old: Path, new: Path) -> bool:
    if new.exists() and not old.exists():
        return False  # idempotent skip
    if not old.exists():
        print(f"  WARN: source missing: {old}")
        return False
    r = run(["git", "mv", str(old), str(new)], check=False)
    if r.returncode != 0:
        print(f"  ERROR: git mv {old} → {new}\n  {r.stderr.strip()}")
        return False
    return True


def pass1_rename_files() -> int:
    chapters = BOOK_DIR / "chapters"
    episodes = BOOK_DIR / "episodes"
    drafts = BOOK_DIR / "_system" / "episode-drafts"
    count = 0

    print("=== Pass 1: file renames ===")
    for slug, old_ch, new_ch, old_ep, new_ep, _, _ in RENAME_MAP:
        old_chap = chapters / f"{old_ch}-{slug}.txt"
        new_chap = chapters / f"{new_ch}-{slug}.txt"
        if git_mv(old_chap, new_chap):
            print(f"  ch: {old_ch}-{slug} → {new_ch}-{slug}")
            count += 1

        old_epfile = episodes / f"{old_ep}-{slug}.txt"
        new_epfile = episodes / f"{new_ep}-{slug}.txt"
        if git_mv(old_epfile, new_epfile):
            print(f"  ep: {old_ep}-{slug} → {new_ep}-{slug}")
            count += 1

        old_draft = drafts / f"{old_ep}-{slug}"
        new_draft = drafts / f"{new_ep}-{slug}"
        if old_draft.is_dir() and git_mv(old_draft, new_draft):
            print(f"  draft: {old_ep}-{slug}/ → {new_ep}-{slug}/")
            count += 1
    return count


def pass2_update_contracts() -> int:
    contracts_dir = BOOK_DIR / "chapter-contracts"
    count = 0
    print("=== Pass 2: chapter-contract updates ===")
    for slug, old_ch, new_ch, old_ep, new_ep, _, _ in RENAME_MAP:
        if slug in ("summary-perfection-of-the-soul", "book-summary"):
            continue  # no contracts for summary chapters
        contract = contracts_dir / f"{slug}.yml"
        if not contract.exists():
            print(f"  WARN: contract missing: {contract}")
            continue
        text = contract.read_text()
        new_text = text
        new_text = new_text.replace(f"{old_ch}-{slug}", f"{new_ch}-{slug}")
        new_text = re.sub(
            r"^episode_number: \d+(\.\d+)?",
            f"episode_number: {int(float(new_ep[2:]))}",
            new_text,
            flags=re.MULTILINE,
        )
        if new_text != text:
            contract.write_text(new_text)
            print(f"  contract: {slug}.yml → {new_ch}-, EP{int(float(new_ep[2:]))}")
            count += 1
    return count


def pass3_update_docs() -> int:
    """Update all known internal docs that reference old chNN/EP## strings."""
    docs = [
        BOOK_DIR / "_system" / "series-plan.md",
        BOOK_DIR / "_system" / "source" / "text" / "chapters-rationale.md",
        BOOK_DIR / "_system" / "source" / "text" / "source-chapter-map.md",
        BOOK_DIR / "_system" / "enrichment-log.md",
        BOOK_DIR / "_system" / "challenger-report.md",
        BOOK_DIR / "operator-review.md",
    ]
    count = 0
    print("=== Pass 3: doc updates ===")
    # Build slug-keyed replacement list ordered longest-first to avoid partial matches
    repls = []
    for slug, old_ch, new_ch, old_ep, new_ep, _, _ in RENAME_MAP:
        repls.append((f"{old_ch}-{slug}", f"{new_ch}-{slug}"))
        # EP## refs as filename-form: "EP04-soul-intellect-and-the-power-of-emanation"
        repls.append((f"{old_ep}-{slug}", f"{new_ep}-{slug}"))
    repls.sort(key=lambda x: -len(x[0]))

    for doc in docs:
        if not doc.exists():
            print(f"  SKIP (missing): {doc}")
            continue
        text = doc.read_text()
        new_text = text
        for old, new in repls:
            new_text = new_text.replace(old, new)
        if new_text != text:
            doc.write_text(new_text)
            n_changes = sum(1 for old, new in repls if old in text and new in new_text)
            print(f"  doc: {doc.name} ({n_changes} replacements)")
            count += 1
    return count


def main() -> int:
    if not BOOK_DIR.exists():
        print(f"ERROR: KaR book dir not found: {BOOK_DIR}", file=sys.stderr)
        return 2
    n1 = pass1_rename_files()
    n2 = pass2_update_contracts()
    n3 = pass3_update_docs()
    print(f"\n=== Summary: {n1} file renames + {n2} contract updates + {n3} doc updates ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
