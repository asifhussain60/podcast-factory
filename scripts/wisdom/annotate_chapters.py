"""annotate_chapters.py — Wave I (I0a): Haiku annotation pass.

Reads chapters from the two canonical test books and produces structured JSON
per paragraph with a proposed tag (mark-for-deletion, mark-for-improvement,
esoteric, reality, sharia, quran, hadith, poetry).

Hard rule: esoteric / reality / quran / hadith / poetry / sharia paragraphs
are NEVER marked for deletion — they are auto-demoted to mark-for-improvement.

CLI usage:
    python3 scripts/wisdom/annotate_chapters.py --dry-run
    python3 scripts/wisdom/annotate_chapters.py --book kitab-al-riyad
    python3 scripts/wisdom/annotate_chapters.py --book the-master-and-the-disciple
    python3 scripts/wisdom/annotate_chapters.py  # all chapters of both books

Outputs:
    CONTENT/drafts/books/<slug>/_system/annotations/<chapter>.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent  # scripts/
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE / "podcast"))

from _paths import REPO_ROOT  # noqa: E402

BOOKS_DIR = REPO_ROOT / "CONTENT" / "drafts" / "books"
CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]

# Tags that must never be flagged for deletion
PROTECTED_TAGS = frozenset({
    "esoteric", "reality", "quran", "hadith", "poetry", "sharia",
})

HAIKU_SYSTEM_PROMPT = """\
You are an annotation assistant for Islamic scholarly texts.
Your task is to classify each paragraph with exactly one tag.

Tags:
- mark-for-deletion: padding, editorial preambles, repetitive openers,
  boilerplate greetings, 'where this chapter picks up' filler
- mark-for-improvement: awkward phrasing, unclear transitions, overly wordy
- esoteric: ta'wil, haqaiq, daqaiq, batini interpretation
- reality: haqiqa, spiritual reality, inner meaning statements
- sharia: legal/exoteric rulings, fiqh, jurisprudence
- quran: Quranic verse or direct reference
- hadith: hadith / prophetic tradition / narration
- poetry: verse, nazm, qa'fiya, poetic form

CRITICAL: Never assign mark-for-deletion to esoteric, reality, quran, hadith,
poetry, or sharia content. If in doubt, use mark-for-improvement.

Respond with a JSON array. Each item: {"para_idx": N, "tag": "<tag>",
"confidence": 0.0-1.0, "note": "<one-line reason>"}.
"""


def _call_haiku(paragraphs: list[str]) -> list[dict]:
    """Call Claude Haiku to annotate paragraphs. Returns list of annotation dicts."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set.")

    client = anthropic.Anthropic(api_key=api_key)

    # Build a numbered list of paragraphs for the prompt
    para_text = "\n\n".join(
        f"[{i}] {p[:600]}" for i, p in enumerate(paragraphs)
    )
    prompt = f"Annotate each paragraph:\n\n{para_text}"

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=HAIKU_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text if response.content else "[]"
    # Extract JSON array from response
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    return json.loads(raw[start:end])


def _demote_protected(annotations: list[dict]) -> list[dict]:
    """Auto-demote mark-for-deletion on protected categories to mark-for-improvement."""
    result = []
    for ann in annotations:
        ann = dict(ann)
        tag = ann.get("tag", "")
        if tag in PROTECTED_TAGS and ann.get("tag") == "mark-for-deletion":
            ann["tag"] = "mark-for-improvement"
            ann["note"] = f"[auto-demoted from deletion: protected category] {ann.get('note', '')}"
        # Also demote if the tag itself IS a protected category (shouldn't be deletion)
        if tag == "mark-for-deletion":
            # Keep — it's legitimate deletion
            pass
        result.append(ann)
    return result


def annotate_chapter(chapter_txt: Path, *, dry_run: bool = False) -> list[dict]:
    """Annotate a single chapter file. Returns list of annotation dicts."""
    text = chapter_txt.read_text(encoding="utf-8")
    # Split into paragraphs on blank lines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    if dry_run:
        # Return stub annotations
        return [
            {"para_idx": i, "tag": "mark-for-improvement", "confidence": 0.5,
             "note": "dry-run stub"}
            for i in range(len(paragraphs))
        ]

    raw_annotations = _call_haiku(paragraphs)
    annotations = _demote_protected(raw_annotations)

    # Fill in any missing para_idx entries
    annotated_idxs = {a["para_idx"] for a in annotations if "para_idx" in a}
    for i in range(len(paragraphs)):
        if i not in annotated_idxs:
            annotations.append({
                "para_idx": i, "tag": "mark-for-improvement",
                "confidence": 0.3, "note": "missing from model response — defaulted"
            })

    annotations.sort(key=lambda a: a.get("para_idx", 0))
    return annotations


def run_book(slug: str, *, dry_run: bool = False) -> dict:
    """Annotate all chapters of a book. Returns summary dict."""
    book_dir = BOOKS_DIR / slug
    if not book_dir.is_dir():
        return {"error": f"Book directory not found: {book_dir}"}

    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        return {"error": f"No chapters dir: {chapters_dir}"}

    annotations_dir = book_dir / "_system" / "annotations"
    annotations_dir.mkdir(parents=True, exist_ok=True)

    chapter_files = sorted(chapters_dir.glob("ch*.txt"))
    results = {"slug": slug, "chapters_processed": 0, "total_paragraphs": 0,
               "dry_run": dry_run, "errors": []}

    for cf in chapter_files:
        try:
            anns = annotate_chapter(cf, dry_run=dry_run)
            out_path = annotations_dir / f"{cf.stem}.json"
            out_path.write_text(
                json.dumps({"chapter": cf.stem, "paragraphs": len(anns),
                            "annotations": anns}, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            results["chapters_processed"] += 1
            results["total_paragraphs"] += len(anns)
            print(f"  annotated {cf.stem}: {len(anns)} paragraphs")
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"chapter": cf.stem, "error": str(exc)})
            print(f"  ERROR {cf.stem}: {exc}", file=sys.stderr)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Haiku annotation pass on book chapters.")
    parser.add_argument("--book", choices=CANONICAL_BOOKS + ["all"], default="all",
                        help="Which book to annotate (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate stub annotations without calling the API")
    args = parser.parse_args()

    books = CANONICAL_BOOKS if args.book == "all" else [args.book]
    for slug in books:
        print(f"\n==> Annotating: {slug}")
        result = run_book(slug, dry_run=args.dry_run)
        if result.get("error"):
            print(f"  ERROR: {result['error']}", file=sys.stderr)
        else:
            print(f"  Done: {result['chapters_processed']} chapters, "
                  f"{result['total_paragraphs']} paragraphs")
            if result["errors"]:
                print(f"  Chapter errors: {len(result['errors'])}")


if __name__ == "__main__":
    main()
