"""Intelligence layer — phase 0h step 1: Atom Extractor.

Reads chapter `.txt` files, calls Gemini once per chapter to extract
Quran/hadith atoms as structured JSON, validates, and writes a per-book
scratch JSONL. Librarian (step 2) deduplicates.

Authority: architecture.md §Intelligence Layer; plan.md Wave B, B1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
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
_GEMINI_MODEL = "gemini-2.5-flash"
# Gemini 2.5-flash list price (approx, USD per 1M tokens) — mirrors gemini_refine.py.
_PRICE = {"in": 0.30 / 1e6, "out": 2.50 / 1e6}

# Type alias: the LLM call function is injectable for testing.
LLMCaller = Callable[[str], tuple[int, str, str]]


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


def _load_gemini_key() -> str:
    """Resolve Gemini API key: env var first, then Mac Keychain. Mirrors gemini_refine.py."""
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit("gemini_api_key not found in env or keychain")
    return r.stdout.strip()


def _default_llm_caller(prompt: str) -> tuple[int, str, str]:
    """Call Gemini and return (rc, stdout, cost_str). Mirrors gemini_refine.py exactly."""
    system = (
        "You are a scholarly citation extractor for Islamic texts. "
        "Return only valid JSON as instructed."
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{_GEMINI_MODEL}:generateContent?key={_load_gemini_key()}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192},
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            d = json.loads(resp.read())
        text = d["candidates"][0]["content"]["parts"][0]["text"]
        cost_usd = round(len(prompt) / 4 * _PRICE["in"] + len(text) / 4 * _PRICE["out"], 5)
        return 0, text, str(cost_usd)
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


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
    llm_caller: LLMCaller | None = None,
) -> ChapterExtractionResult:
    """Extract atoms from a single chapter's text using one LLM call."""
    caller = llm_caller or _default_llm_caller
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
        result.error = f"Gemini call failed (rc={rc}): {cost_str}"
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
    llm_caller: LLMCaller | None = None,
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
                llm_caller=llm_caller,
            )
            summary.chapters_processed += 1
            summary.total_cost_usd += ch_result.cost_usd
            summary.needs_review_count += ch_result.needs_review_count

            if ch_result.error:
                summary.errors.append(f"{chapter_slug}: {ch_result.error}")

            if ch_result.cost_usd > R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_CHAPTER:
                summary.errors.append(
                    f"Per-chapter cost cap exceeded for {chapter_slug}: "
                    f"${ch_result.cost_usd:.4f} > "
                    f"${R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_CHAPTER:.4f}"
                )

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
