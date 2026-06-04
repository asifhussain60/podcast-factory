"""import_annotations.py — Wave I (I0a): Load annotation JSON into reader DB.

Reads annotation JSON files produced by annotate_chapters.py and imports them
into the SQLite knowledge.db paragraph_annotations and annotation_tags tables.

CLI usage:
    python3 scripts/wisdom/import_annotations.py --dry-run
    python3 scripts/wisdom/import_annotations.py --book kitab-al-riyad
    python3 scripts/wisdom/import_annotations.py  # all canonical books
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE / "podcast"))

from _paths import REPO_ROOT  # noqa: E402
from _db import get_connection, run_migrations  # noqa: E402

BOOKS_DIR = REPO_ROOT / "CONTENT" / "drafts" / "books"
CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]

# Canonical tag definitions — seeded once into annotation_tags
CANONICAL_TAGS = [
    ("mark-for-deletion",   "#ef4444", "Trash2",    False, 10),
    ("mark-for-improvement","#f97316", "Edit",       False, 20),
    ("esoteric",            "#7c3aed", "Eye",        True,  30),
    ("reality",             "#2563eb", "Sparkles",   True,  40),
    ("sharia",              "#059669", "Scale",      True,  50),
    ("quran",               "#d97706", "BookOpen",   True,  60),
    ("hadith",              "#0891b2", "MessageCircle", True, 70),
    ("poetry",              "#db2777", "Music",      True,  80),
]


def seed_tags(conn) -> dict[str, int]:
    """Ensure all canonical tags exist; return label→id mapping."""
    for label, color, icon, is_default, sort_order in CANONICAL_TAGS:
        conn.execute(
            "INSERT OR IGNORE INTO annotation_tags "
            "(tag_label, tag_color, tag_icon, is_default, sort_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (label, color, icon, 1 if is_default else 0, sort_order),
        )
    conn.commit()
    rows = conn.execute(
        "SELECT id, tag_label FROM annotation_tags"
    ).fetchall()
    return {label: tag_id for tag_id, label in rows}


def import_book(slug: str, *, dry_run: bool = False) -> dict:
    """Import all annotation JSON files for a book into the DB."""
    book_dir = BOOKS_DIR / slug
    annotations_dir = book_dir / "_system" / "annotations"
    if not annotations_dir.is_dir():
        return {"error": f"No annotations dir for {slug}. Run annotate_chapters.py first."}

    run_migrations()
    conn = get_connection()
    tag_map = seed_tags(conn)

    total_imported = 0
    total_skipped = 0
    errors: list[str] = []

    for json_file in sorted(annotations_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            chapter_id = data.get("chapter", json_file.stem)
            annotations = data.get("annotations", [])

            for ann in annotations:
                para_idx = ann.get("para_idx")
                tag_label = ann.get("tag", "mark-for-improvement")
                note = ann.get("note", "")
                tag_id = tag_map.get(tag_label)
                if tag_id is None:
                    total_skipped += 1
                    continue

                if dry_run:
                    total_imported += 1
                    continue

                conn.execute(
                    "INSERT OR REPLACE INTO paragraph_annotations "
                    "(book_slug, chapter_id, para_idx, tag_id, note) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (slug, chapter_id, para_idx, tag_id, note),
                )
                total_imported += 1

            if not dry_run:
                conn.commit()

        except Exception as exc:  # noqa: BLE001
            errors.append(f"{json_file.name}: {exc}")

    return {
        "slug": slug,
        "imported": total_imported,
        "skipped": total_skipped,
        "dry_run": dry_run,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import annotations into reader DB.")
    parser.add_argument("--book", choices=CANONICAL_BOOKS + ["all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    books = CANONICAL_BOOKS if args.book == "all" else [args.book]
    for slug in books:
        print(f"\n==> Importing: {slug}")
        result = import_book(slug, dry_run=args.dry_run)
        if result.get("error"):
            print(f"  ERROR: {result['error']}", file=sys.stderr)
        else:
            print(f"  imported={result['imported']}, skipped={result['skipped']}"
                  f"{' [DRY RUN]' if result['dry_run'] else ''}")
            for e in result["errors"]:
                print(f"  WARN: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
