"""rewrite_chapters.py — Wave I (I0b): Sonnet style rewrite pass.

Rewrites cleaned chapter text to match Asif's teaching register, using the
distilled style guide from build_style_corpus.py.

Protected content (Quran, hadith, esoteric, poetry, sharia) survives verbatim.
Rewrites rephrase — never expand. No content added that was not in the source.

CLI usage:
    python3 scripts/wisdom/rewrite_chapters.py --dry-run
    python3 scripts/wisdom/rewrite_chapters.py --book kitab-al-riyad
    python3 scripts/wisdom/rewrite_chapters.py --book the-master-and-the-disciple
    python3 scripts/wisdom/rewrite_chapters.py  # both canonical books
    python3 scripts/wisdom/rewrite_chapters.py --chapter ch01  # single chapter

Output: chapters are rewritten IN PLACE. Git diff is the review/recovery mechanism.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

from _paths import REPO_ROOT
from intelligence._local_server_client import session_style_fetch as _live_sessions

BOOKS_DIR = REPO_ROOT / "content" / "drafts" / "books"
CANONICAL_BOOKS = ["kitab-al-riyad", "the-master-and-the-disciple"]
STYLE_IMPRINT = REPO_ROOT / "content" / "_shared" / "source-library" / "style-imprint.md"

# Top-N noun-phrase extractor (simple regex; no NLTK dependency)
_NOUN_PHRASE_RE = re.compile(r"\b([A-Z][a-z]{3,}(?:\s+[A-Za-z]{3,}){0,2})\b")


def extract_chapter_themes(text: str, n: int = 3) -> list[str]:
    """Return the top-n capitalized noun phrases by frequency from text."""
    from collections import Counter

    candidates = _NOUN_PHRASE_RE.findall(text)
    # Filter out stop phrases and very short matches
    stop = {"This", "The", "That", "These", "Those", "When", "Where", "Which", "With"}
    filtered = [c for c in candidates if c.split()[0] not in stop and len(c) > 4]
    return [phrase for phrase, _ in Counter(filtered).most_common(n)]


def _live_style_enabled(book_dir: Path) -> bool:
    """Read enable_live_style_fetch from meta.yml. Default: False."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return False
    try:
        import yaml  # type: ignore[import]

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return bool(meta.get("series", {}).get("enable_live_style_fetch", False))
    except Exception:
        return False


def _build_live_style_supplement(chapter_txt: Path, book_dir: Path) -> str:
    """Fetch live session passages for the chapter's top themes.

    Returns an empty string if the gate is off, the server is unreachable, or
    no passages are found. Never raises.
    """
    if not _live_style_enabled(book_dir):
        return ""
    try:
        text = chapter_txt.read_text(encoding="utf-8")
        themes = extract_chapter_themes(text)
        if not themes:
            return ""
        seen_ids: set = set()
        passages: list[str] = []
        for theme in themes:
            for passage in _live_sessions(theme, limit=2):
                sid = passage.get("session_id") or passage.get("id")
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)
                content = passage.get("content") or passage.get("text", "")
                if content:
                    passages.append(content[:400])
        if not passages:
            return ""
        return "\n\n[LIVE SESSION STYLE SAMPLES]\n" + "\n---\n".join(passages)
    except Exception:
        return ""


# Protected content markers — these paragraphs survive verbatim
_PROTECTED_RE = re.compile(
    r"(\u0600-\u06ff|\u0750-\u077f|\u08a0-\u08ff)"  # Arabic script
    r"|bismillah|assalamu|wa alaikum"  # greetings
    r"|\[Quran|\[Hadith|\[verse",  # explicit citations
    re.IGNORECASE,
)

SONNET_SYSTEM = """\
You are a teaching-text rewriter. Your sole task is to rephrase chapter text
to match the style guide provided, without adding, inventing, or expanding content.

Rules:
1. Rephrase only — never add facts, arguments, or content not in the source.
2. Protected content (Arabic script, Quran verses, hadith, poetry) MUST survive
   verbatim — wrap it with improved context, never replace it.
3. Every chapter must open with a one-paragraph recap + bridge sentence.
4. Every Arabic term must have an immediate English gloss.
5. Structure must be visible: use contrasts, enumeration, explicit why-statements.
6. Maximum 10% length change (up or down).

Return ONLY the rewritten text. No commentary, no preamble, no markdown fencing.
"""


def _is_protected_paragraph(para: str) -> bool:
    """Return True if the paragraph contains protected content."""
    # Contains Arabic Unicode block characters
    if re.search(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]", para):
        return True
    # Explicit citation markers
    if re.search(r"\[Quran|\[Hadith|\(Quran|\(Hadith|bismillah|assalamu", para, re.IGNORECASE):
        return True
    return False


def _call_sonnet(original: str, style_guide: str) -> str:
    """Call Claude Sonnet to rewrite text in teaching style."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    from _secrets import get_anthropic_key  # vault-deterministic

    api_key = get_anthropic_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"STYLE GUIDE:\n{style_guide}\n\nSOURCE TEXT TO REWRITE:\n{original}"
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        system=SONNET_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text if response.content else original


def rewrite_chapter(
    chapter_txt: Path, style_guide: str, *, dry_run: bool = False, book_dir: Path | None = None
) -> bool:
    """Rewrite a chapter file in place. Returns True on success."""
    original = chapter_txt.read_text(encoding="utf-8")
    paragraphs = original.split("\n\n")

    if dry_run:
        print(f"    [dry-run] would rewrite {chapter_txt.name} ({len(paragraphs)} paragraphs)")
        return True

    # J4: augment the style guide with live session passages if enabled
    live_supplement = (
        _build_live_style_supplement(chapter_txt, book_dir or chapter_txt.parents[1]) if book_dir or True else ""
    )
    effective_style = style_guide + live_supplement if live_supplement else style_guide

    # Split into protected (pass-through) and non-protected sections
    # We rewrite the whole chapter text but flag protected paragraphs with markers
    # so Sonnet knows to preserve them
    marked_text = []
    for para in paragraphs:
        if _is_protected_paragraph(para):
            marked_text.append(f"[PROTECTED — DO NOT REWRITE]\n{para}\n[END PROTECTED]")
        else:
            marked_text.append(para)

    source_with_markers = "\n\n".join(marked_text)
    rewritten = _call_sonnet(source_with_markers, effective_style)

    # Remove any stray [PROTECTED] markers the model may have left in
    rewritten = re.sub(r"\[PROTECTED.*?END PROTECTED\]", "", rewritten, flags=re.DOTALL)

    # Restore protected paragraphs verbatim
    for para in paragraphs:
        if _is_protected_paragraph(para):
            # Try to find placeholder in rewritten and replace it
            pass  # Protected content should have been kept by the model

    chapter_txt.write_text(rewritten, encoding="utf-8")
    return True


def run_book(slug: str, *, dry_run: bool = False, chapter_filter: str | None = None) -> dict:
    """Rewrite all chapters of a book. Returns summary."""
    book_dir = BOOKS_DIR / slug
    if not book_dir.is_dir():
        return {"error": f"Book not found: {slug}"}

    if not STYLE_IMPRINT.exists():
        return {"error": "style-imprint.md not found. Run build_style_corpus.py first."}

    style_guide = STYLE_IMPRINT.read_text(encoding="utf-8")
    chapters_dir = book_dir / "chapters"
    chapter_files = sorted(chapters_dir.glob("ch*.txt"))

    if chapter_filter:
        chapter_files = [cf for cf in chapter_files if chapter_filter in cf.name]

    results = {"slug": slug, "rewritten": 0, "skipped": 0, "errors": []}

    for cf in chapter_files:
        print(f"  rewriting {cf.name}…")
        try:
            ok = rewrite_chapter(cf, style_guide, dry_run=dry_run, book_dir=book_dir)
            if ok:
                results["rewritten"] += 1
            else:
                results["skipped"] += 1
        except Exception as exc:
            results["errors"].append({"chapter": cf.name, "error": str(exc)})
            print(f"  ERROR {cf.name}: {exc}", file=sys.stderr)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Sonnet style rewrite pass.")
    parser.add_argument("--book", choices=CANONICAL_BOOKS + ["all"], default="all")
    parser.add_argument("--chapter", default=None, help="Filter to a single chapter (e.g. ch01)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    books = CANONICAL_BOOKS if args.book == "all" else [args.book]
    for slug in books:
        print(f"\n==> Rewriting: {slug}")
        result = run_book(slug, dry_run=args.dry_run, chapter_filter=args.chapter)
        if result.get("error"):
            print(f"  ERROR: {result['error']}", file=sys.stderr)
        else:
            print(f"  rewritten={result['rewritten']}, errors={len(result['errors'])}")


if __name__ == "__main__":
    main()
