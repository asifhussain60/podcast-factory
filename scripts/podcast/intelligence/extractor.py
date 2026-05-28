"""Intelligence layer — phase 0h step 1: Atom Extractor.

Reads chapter `.txt` files, calls claude -p once per chapter to extract
Quran/hadith atoms as structured JSON, validates, and writes a per-book
scratch JSONL. Librarian (step 2) deduplicates.

Authority: architecture.md §Intelligence Layer; plan.md Wave B, B1.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ── local imports (scripts/podcast is on sys.path when run via orchestrator) ──
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge._atom_schemas import (
    quran_canonical_id,
    hadith_canonical_id,
    validate_atom,
)
from _rules import (
    R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_CHAPTER,
    R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_BOOK,
    R_KNOWLEDGE_EXTRACTOR_CONFIDENCE_THRESHOLD,
)
import _db

SCRATCH_FILENAME = "knowledge-atoms-scratch.jsonl"
_CLAUDE_CMD = "claude"

# Type alias: the LLM call function is injectable for testing.
ClaudeCaller = Callable[[str], tuple[int, str, str]]


# ─── public result types ──────────────────────────────────────────────────────

@dataclass
class ChapterExtractionResult:
    chapter_slug: str
    atoms: list[dict] = field(default_factory=list)
    needs_review_count: int = 0
    cost_usd: float = 0.0
    error: str | None = None


@dataclass
class ExtractionSummary:
    book_slug: str
    scratch_path: Path
    chapters_processed: int = 0
    atoms_extracted: dict[str, int] = field(default_factory=dict)   # type → count
    needs_review_count: int = 0
    total_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)


# ─── LLM helpers ─────────────────────────────────────────────────────────────

_EXTRACTION_PROMPT_TMPL = """\
You are a scholarly citation extractor for Islamic texts.
Extract every EXPLICITLY cited Quran verse and every EXPLICITLY cited hadith from the text.
Do NOT infer citations that are not explicitly stated.

Return ONLY a JSON object:
{{"atoms":[{{"type":"quran","surah":<int>,"ayah":<int>,"text_en":"<quoted text>","confidence":<0-1>}},{{"type":"hadith","collection":"<bukhari|muslim|tirmidhi|abu-dawud|nasai|ibn-majah|other>","number":<int|null>,"text_en":"<text>","grade":"<sahih|hasan|daif|unknown>","narrator":"<name|null>","confidence":<0-1>}}]}}

If no citations: {{"atoms":[]}}. Return ONLY the JSON.

CHAPTER SLUG: {chapter_slug}
BOOK SLUG: {book_slug}

CHAPTER TEXT:
{chapter_text}
"""


def _default_claude_caller(prompt: str) -> tuple[int, str, str]:
    """Shell out to `claude -p` and return (rc, stdout, cost_str)."""
    argv = [_CLAUDE_CMD, "-p", "--permission-mode", "acceptEdits",
            "--output-format", "json", prompt]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        rc, raw_stdout = proc.returncode, proc.stdout
        try:
            envelope = json.loads(raw_stdout)
            stdout = envelope.get("result", raw_stdout)
            cost_usd = float(envelope.get("cost_usd", 0.0))
        except (json.JSONDecodeError, KeyError, TypeError):
            stdout = raw_stdout
            cost_usd = 0.0
        return rc, stdout, str(cost_usd)
    except FileNotFoundError:
        return 1, "", "claude binary not found on PATH"
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


# ─── atom builder helpers ─────────────────────────────────────────────────────

def _book_tradition(book_dir: Path) -> str:
    """Read tradition_affinity from meta.yml, default 'universal'."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return "universal"
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return str(meta.get("tradition_affinity", "universal"))
    except Exception:  # noqa: BLE001
        return "universal"


def _build_atom(raw: dict, book_slug: str, chapter_slug: str,
                tradition: str = "universal") -> dict | None:
    """Convert raw LLM output to a validated Atom dict. Returns None on failure."""
    atom_type = raw.get("type")
    try:
        if atom_type == "quran":
            surah = int(raw["surah"])
            ayah = int(raw["ayah"])
            atom_id = quran_canonical_id(surah, ayah)
            body = {
                "surah": surah,
                "ayah": ayah,
                "text_en": raw.get("text_en", ""),
            }
        elif atom_type == "hadith":
            collection = raw.get("collection", "other")
            number = raw.get("number") or 0
            atom_id = hadith_canonical_id(collection, int(number))
            body = {
                "collection": collection,
                "number": int(number),
                "text_en": raw.get("text_en", ""),
                "grade": raw.get("grade", "unknown"),
                "narrator": raw.get("narrator"),
            }
        else:
            return None
        atom: dict = {
            "id": atom_id,
            "type": atom_type,
            "body": body,
            "tradition": tradition,
            "confidence": float(raw.get("confidence", 1.0)),
            "needs_review": float(raw.get("confidence", 1.0)) < R_KNOWLEDGE_EXTRACTOR_CONFIDENCE_THRESHOLD,
            "first_seen": {"book": book_slug, "chapter": chapter_slug},
            "sources": [{"book": book_slug, "chapter": chapter_slug, "locator": ""}],
        }
        validate_atom(atom)
        return atom
    except (KeyError, ValueError, TypeError):
        return None


# ─── per-chapter extraction ───────────────────────────────────────────────────

def extract_chapter(
    chapter_slug: str,
    chapter_text: str,
    book_slug: str,
    *,
    claude_caller: ClaudeCaller | None = None,
) -> ChapterExtractionResult:
    """Extract atoms from a single chapter's text using one LLM call."""
    caller = claude_caller or _default_claude_caller
    prompt = _EXTRACTION_PROMPT_TMPL.format(
        chapter_slug=chapter_slug,
        book_slug=book_slug,
        chapter_text=chapter_text[:8000],   # guard context window
    )
    rc, stdout, cost_str = caller(prompt)
    result = ChapterExtractionResult(chapter_slug=chapter_slug)
    try:
        result.cost_usd = float(cost_str)
    except (ValueError, TypeError):
        result.cost_usd = 0.0

    if rc != 0:
        result.error = f"claude -p exited {rc}: {cost_str}"
        return result

    # Parse JSON response
    raw_text = stdout.strip()
    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = "\n".join(
            line for line in raw_text.splitlines()
            if not line.startswith("```")
        ).strip()
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        result.error = f"JSON parse failed: {exc}"
        return result

    for raw_atom in payload.get("atoms", []):
        atom = _build_atom(raw_atom, book_slug, chapter_slug)
        if atom is None:
            continue
        result.atoms.append(atom)
        if atom.get("needs_review"):
            result.needs_review_count += 1

    return result


# ─── per-book orchestration ───────────────────────────────────────────────────

def extract_atoms_for_book(
    book_dir: Path,
    *,
    claude_caller: ClaudeCaller | None = None,
) -> ExtractionSummary:
    """Extract atoms from all chapter .txt files; write scratch JSONL."""
    book_slug = book_dir.name
    chapters_dir = book_dir / "chapters"
    system_dir = book_dir / "_system"
    system_dir.mkdir(parents=True, exist_ok=True)
    scratch_path = system_dir / SCRATCH_FILENAME
    tradition = _book_tradition(book_dir)

    chapter_files = sorted(chapters_dir.glob("*.txt")) if chapters_dir.exists() else []
    summary = ExtractionSummary(book_slug=book_slug, scratch_path=scratch_path)

    with scratch_path.open("w", encoding="utf-8") as fh:
        for ch_path in chapter_files:
            chapter_slug = ch_path.stem
            chapter_text = ch_path.read_text(encoding="utf-8")

            ch_result = extract_chapter(
                chapter_slug, chapter_text, book_slug,
                claude_caller=claude_caller,
            )
            summary.chapters_processed += 1
            summary.total_cost_usd += ch_result.cost_usd
            summary.needs_review_count += ch_result.needs_review_count

            if ch_result.error:
                summary.errors.append(f"{chapter_slug}: {ch_result.error}")

            for atom in ch_result.atoms:
                # Stamp tradition from book meta if atom doesn't already have it
                if "tradition" not in atom:
                    atom["tradition"] = tradition
                fh.write(json.dumps(atom, ensure_ascii=False) + "\n")
                atom_type = atom.get("type", "unknown")
                summary.atoms_extracted[atom_type] = (
                    summary.atoms_extracted.get(atom_type, 0) + 1
                )

            if summary.total_cost_usd > R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_BOOK:
                summary.errors.append(
                    f"Cost cap exceeded at chapter {chapter_slug}: "
                    f"${summary.total_cost_usd:.2f} > "
                    f"${R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_BOOK:.2f}"
                )
                break

    # Write needs_review atoms to manual_review_queue in DB
    _flush_needs_review_to_db(scratch_path, book_slug)
    return summary


def _flush_needs_review_to_db(scratch_path: Path, book_slug: str) -> None:
    """Append low-confidence atoms to manual_review_queue."""
    if not scratch_path.exists():
        return
    conn = _db.get_connection()
    cur = conn.cursor()
    with scratch_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            atom = json.loads(line)
            if atom.get("needs_review"):
                cur.execute(
                    """
                    INSERT INTO manual_review_queue
                        (book_slug, chapter_id, reason, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        book_slug,
                        atom.get("first_seen", {}).get("chapter", ""),
                        "confidence_below_threshold",
                        json.dumps({"atom_id": atom["id"], "confidence": atom.get("confidence")}),
                    ),
                )
    conn.commit()


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Extract atoms from book chapters.")
    parser.add_argument("book_dir", help="Path to content/drafts/<slug>/")
    args = parser.parse_args()
    s = extract_atoms_for_book(Path(args.book_dir))
    print(f"Book: {s.book_slug} | chapters={s.chapters_processed} | atoms={s.atoms_extracted}")
    print(f"Needs review: {s.needs_review_count} | cost=${s.total_cost_usd:.4f}")
    for err in s.errors:
        print(f"ERROR: {err}", file=sys.stderr)
    print(f"Scratch: {s.scratch_path}")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(main())
