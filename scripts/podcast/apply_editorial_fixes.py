"""apply_editorial_fixes.py — Apply editorial-auditor findings to narrator stage files.

Reads _system/editorial-audit/<chapter>.json for each chapter, then produces:
  - _stages/<chapter>/additions-narrator-clean.md   (cleaned content; original preserved)
  - _stages/<chapter>/additions-narrator-meta.json  (suppressed metadata for sidecar use)

Actions:
  suppress   → remove from clean .md; save to sidecar JSON
  consolidate (with replacement) → replace the block with condensed_replacement text
  consolidate (replacement null) → drop the paragraph (e.g. LECTURE_RECAP_BRIDGE)

Paragraph splitting uses double-newline boundaries (same as the auditor).

Usage:
    python3 scripts/podcast/apply_editorial_fixes.py --slug ayyuhal-walad
    python3 scripts/podcast/apply_editorial_fixes.py --slug ayyuhal-walad --chapter ch01-frame-and-first-counsel
    python3 scripts/podcast/apply_editorial_fixes.py --slug ayyuhal-walad --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT = REPO_ROOT / "content" / "drafts" / "books"


def _paragraphs(text: str) -> list[str]:
    """Split on blank-line boundaries; preserve original paragraph text."""
    return [p for p in re.split(r"\n\n+", text)]


def _rejoin(paras: list[str]) -> str:
    return "\n\n".join(paras).strip() + "\n"


def apply_fixes(
    stage_file: Path,
    audit_file: Path,
    *,
    dry_run: bool = False,
) -> dict:
    """Apply audit findings to one chapter's narrator additions.

    Returns a summary dict with counts of suppressed / consolidated paragraphs.
    """
    text = stage_file.read_text(encoding="utf-8")
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    findings = audit.get("findings", [])

    paras = _paragraphs(text)
    n_original = len(paras)

    # Build index sets.
    suppress_idxs: set[int] = set()
    consolidate_blocks: dict[int, str | None] = {}  # first-para-idx → replacement or None
    drop_idxs: set[int] = set()  # consolidate-secondary idxs (removed after first is replaced)

    for f in findings:
        action = f["action"]
        idx = f["paragraph_index"]
        replacement = f.get("condensed_replacement")

        if action == "suppress":
            suppress_idxs.add(idx)

        elif action == "consolidate":
            if replacement == "(see first paragraph of block)":
                # Secondary paragraph in a multi-para consolidate block — drop it.
                drop_idxs.add(idx)
            elif replacement is None:
                # LECTURE_RECAP_BRIDGE style — just remove.
                suppress_idxs.add(idx)
            else:
                # First paragraph of a consolidate block — replace with condensed text.
                consolidate_blocks[idx] = replacement

    # Build the sidecar: collect text of suppressed paragraphs.
    suppressed_entries = []
    for f in findings:
        if f["action"] == "suppress":
            idx = f["paragraph_index"]
            if idx < len(paras):
                suppressed_entries.append({
                    "paragraph_index": idx,
                    "pattern": f["pattern"],
                    "original_text": paras[idx],
                })

    # Build the cleaned paragraph list.
    cleaned: list[str] = []
    all_drop = suppress_idxs | drop_idxs
    for i, para in enumerate(paras):
        if i in all_drop:
            continue
        if i in consolidate_blocks:
            replacement = consolidate_blocks[i]
            if replacement:
                cleaned.append(replacement)
            # else: just drop (no replacement)
            continue
        cleaned.append(para)

    clean_text = _rejoin(cleaned)

    meta = {
        "chapter": audit.get("chapter", ""),
        "stage": audit.get("stage", "narrator"),
        "applied_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "findings_applied": len(suppress_idxs) + len(drop_idxs) + len(consolidate_blocks),
        "suppressed": suppressed_entries,
        "consolidate_blocks": list(consolidate_blocks.keys()),
    }

    summary = {
        "chapter": audit.get("chapter", stage_file.parent.name),
        "original_paragraphs": n_original,
        "cleaned_paragraphs": len(cleaned),
        "suppressed": len(suppress_idxs),
        "dropped_secondary": len(drop_idxs),
        "consolidated": len(consolidate_blocks),
    }

    if dry_run:
        print(f"  [dry-run] {summary['chapter']}: "
              f"{summary['suppressed']} suppressed, "
              f"{summary['consolidated']} consolidated, "
              f"{summary['dropped_secondary']} secondary-dropped "
              f"→ {n_original}→{len(cleaned)} paragraphs")
        return summary

    clean_path = stage_file.parent / "additions-narrator-clean.md"
    meta_path = stage_file.parent / "additions-narrator-meta.json"

    clean_path.write_text(clean_text, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✅ {summary['chapter']}: "
          f"{n_original}→{len(cleaned)} paragraphs "
          f"| clean → {clean_path.name} | meta → {meta_path.name}")

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply editorial-auditor findings to narrator stage files.")
    ap.add_argument("--slug", required=True, help="Book slug")
    ap.add_argument("--chapter", default=None, help="Process only this chapter slug")
    ap.add_argument("--dry-run", action="store_true", help="Print plan without writing files")
    args = ap.parse_args()

    book_dir = CONTENT / args.slug
    if not book_dir.exists():
        print(f"ERROR: book directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    audit_dir = book_dir / "_system" / "editorial-audit"
    stages_dir = book_dir / "_stages"

    if not audit_dir.exists():
        print(f"ERROR: no editorial-audit directory at {audit_dir}", file=sys.stderr)
        sys.exit(1)

    audit_files = sorted(audit_dir.glob("*.json"))
    if args.chapter:
        audit_files = [f for f in audit_files if f.stem == args.chapter]
        if not audit_files:
            print(f"ERROR: no audit file found for chapter '{args.chapter}'", file=sys.stderr)
            sys.exit(1)

    if not audit_files:
        print("No audit files found.", file=sys.stderr)
        sys.exit(1)

    print(f"\nApplying editorial fixes — {args.slug} "
          f"({'dry-run' if args.dry_run else 'live'})\n")

    total_suppressed = 0
    total_consolidated = 0
    errors = 0

    for audit_file in audit_files:
        chapter_slug = audit_file.stem
        stage_dir = stages_dir / chapter_slug
        additions_file = stage_dir / "additions-narrator.md"

        if not additions_file.exists():
            print(f"  ⚠️  {chapter_slug}: no additions-narrator.md found at {additions_file} — skipping")
            errors += 1
            continue

        result = apply_fixes(additions_file, audit_file, dry_run=args.dry_run)
        total_suppressed += result["suppressed"]
        total_consolidated += result["consolidated"]

    print(f"\nDone. {total_suppressed} suppress + {total_consolidated} consolidate applied across "
          f"{len(audit_files)} chapters.")
    if errors:
        print(f"⚠️  {errors} chapter(s) skipped (missing stage file).")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
