"""Intelligence layer — phase 0h step 2: Atom Librarian.

Reads the Extractor's scratch JSONL, classifies each atom against the
canonical knowledge library in the DB, and writes the results back.
Pure Python — no LLM calls.

Classification logic:
  NEW       — id not in atoms table → INSERT
  KNOWN     — id present, body matches → add source reference
  VARIANT   — id present, text_en differs → add to atoms_variants
  CONFLICT  — id present, body has a structural contradiction → halt

Authority: architecture.md §Intelligence Layer; plan.md Wave B, B2.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _db

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[3] / "content" / "knowledge-base"

# Fields whose difference constitutes a true conflict (not just a variant)
_CONFLICT_FIELDS: dict[str, set[str]] = {
    "hadith": {"grade", "narrator"},
}


# ─── public types ─────────────────────────────────────────────────────────────

@dataclass
class MergeReport:
    book_slug: str = ""
    atoms_new: dict[str, int] = field(default_factory=dict)       # type → count
    atoms_merged: dict[str, int] = field(default_factory=dict)    # type → count
    atoms_variant: dict[str, int] = field(default_factory=dict)   # type → count
    atoms_conflict: dict[str, int] = field(default_factory=dict)  # type → count
    conflict_count: int = 0
    report_md_path: Path | None = None


# ─── classification helpers ───────────────────────────────────────────────────

def _is_conflict(existing_body: dict, incoming_body: dict, atom_type: str) -> bool:
    """True if the two bodies have a structural contradiction worth halting for."""
    conflict_keys = _CONFLICT_FIELDS.get(atom_type, set())
    for key in conflict_keys:
        ev, iv = existing_body.get(key), incoming_body.get(key)
        if ev and iv and ev != iv:
            return True
    return False


def _merge_source(conn, atom_id: str, book_slug: str, chapter_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO atoms_sources (atom_id, book_slug, chapter_id) VALUES (?, ?, ?)",
        (atom_id, book_slug, chapter_id),
    )


def _merge_variant(conn, atom_id: str, book_slug: str, text_en: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO atoms_variants (atom_id, book_slug, text_en) VALUES (?, ?, ?)",
        (atom_id, book_slug, text_en),
    )


def _record_conflict(conn, atom_id: str, existing_body: dict, incoming_body: dict) -> None:
    conn.execute(
        """INSERT INTO knowledge_base_conflicts
               (atom_id, source_file, existing_body, incoming_body)
           VALUES (?, ?, ?, ?)""",
        (
            atom_id,
            "knowledge-atoms-scratch.jsonl",
            json.dumps(existing_body, ensure_ascii=False),
            json.dumps(incoming_body, ensure_ascii=False),
        ),
    )
    conn.execute(
        """INSERT INTO manual_review_queue (book_slug, chapter_id, reason, payload)
           VALUES (?, ?, ?, ?)""",
        ("", "", "atom_conflict",
         json.dumps({"atom_id": atom_id})),
    )


# ─── core merge ───────────────────────────────────────────────────────────────

def _classify_and_write(conn, atom: dict, book_slug: str) -> str:
    """Classify one atom and write to DB. Returns 'new'|'merged'|'variant'|'conflict'."""
    atom_id = atom["id"]
    atom_type = atom.get("type", "")
    incoming_body = atom.get("body", {})
    chapter_id = atom.get("first_seen", {}).get("chapter", "")

    row = conn.execute("SELECT body FROM atoms WHERE id = ?", (atom_id,)).fetchone()

    if row is None:
        # NEW
        conn.execute(
            """INSERT INTO atoms
                   (id, type, body, first_seen_book, first_seen_chapter,
                    first_seen_date, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                atom_id,
                atom_type,
                json.dumps(incoming_body, ensure_ascii=False),
                book_slug,
                chapter_id,
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                float(atom.get("confidence", 1.0)),
            ),
        )
        _merge_source(conn, atom_id, book_slug, chapter_id)
        return "new"

    existing_body = json.loads(row[0])

    if _is_conflict(existing_body, incoming_body, atom_type):
        _record_conflict(conn, atom_id, existing_body, incoming_body)
        return "conflict"

    # Check for text variant
    existing_text = existing_body.get("text_en", "")
    incoming_text = incoming_body.get("text_en", "")
    if incoming_text and incoming_text != existing_text:
        _merge_variant(conn, atom_id, book_slug, incoming_text)
        _merge_source(conn, atom_id, book_slug, chapter_id)
        return "variant"

    # KNOWN identical
    _merge_source(conn, atom_id, book_slug, chapter_id)
    return "merged"


# ─── report writer ────────────────────────────────────────────────────────────

def _write_report(book_dir: Path, report: MergeReport) -> Path:
    system_dir = book_dir / "_system"
    system_dir.mkdir(parents=True, exist_ok=True)
    out = system_dir / "knowledge-merge-report.md"
    lines = [
        f"# Knowledge Merge Report — {report.book_slug}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Category | quran | hadith | doctrine |",
        "|---|---|---|---|",
    ]
    for label, d in [("New", report.atoms_new), ("Merged (source added)", report.atoms_merged),
                     ("Variant (text added)", report.atoms_variant), ("Conflict (halted)", report.atoms_conflict)]:
        lines.append(f"| {label} | {d.get('quran',0)} | {d.get('hadith',0)} | {d.get('doctrine',0)} |")
    if report.conflict_count:
        lines += ["", f"> **{report.conflict_count} conflict(s) detected. Phase halted. Resolve via manual review queue.**"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _update_stats(conn) -> None:
    stats_path = KNOWLEDGE_BASE_DIR / "_index" / "stats.json"
    if not stats_path.exists():
        return
    try:
        stats = json.loads(stats_path.read_text())
        for atom_type in ("quran", "hadith", "doctrine"):
            count = conn.execute(
                "SELECT COUNT(*) FROM atoms WHERE type = ?", (atom_type,)
            ).fetchone()[0]
            stats.setdefault("counts", {})[atom_type] = count
        stats["last_updated"] = datetime.now(timezone.utc).isoformat()
        stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
    except Exception:   # noqa: BLE001 — stats update is best-effort
        pass


# ─── public API ───────────────────────────────────────────────────────────────

def merge_into_library(book_dir: Path, scratch_path: Path) -> MergeReport:
    """Merge scratch JSONL atoms into the canonical knowledge-base DB.

    Returns MergeReport; conflict_count > 0 means the caller should halt the phase.
    """
    book_slug = book_dir.name
    report = MergeReport(book_slug=book_slug)

    if not scratch_path.exists():
        report.report_md_path = _write_report(book_dir, report)
        return report

    conn = _db.get_connection()

    with scratch_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            atom = json.loads(line)
            atom_type = atom.get("type", "unknown")
            outcome = _classify_and_write(conn, atom, book_slug)
            target = {
                "new": report.atoms_new,
                "merged": report.atoms_merged,
                "variant": report.atoms_variant,
                "conflict": report.atoms_conflict,
            }.get(outcome, report.atoms_new)
            target[atom_type] = target.get(atom_type, 0) + 1
            if outcome == "conflict":
                report.conflict_count += 1

    conn.commit()
    _update_stats(conn)
    report.report_md_path = _write_report(book_dir, report)
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Merge scratch atoms into the knowledge library.")
    parser.add_argument("book_dir", help="Path to content/drafts/<slug>/")
    parser.add_argument("scratch", help="Path to knowledge-atoms-scratch.jsonl")
    args = parser.parse_args()
    r = merge_into_library(Path(args.book_dir), Path(args.scratch))
    print(f"New: {r.atoms_new} | Merged: {r.atoms_merged} | Variant: {r.atoms_variant} | Conflict: {r.atoms_conflict}")
    if r.conflict_count:
        print(f"HALTED: {r.conflict_count} conflicts — see {r.report_md_path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
