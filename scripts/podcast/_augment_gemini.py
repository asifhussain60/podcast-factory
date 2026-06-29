"""_augment_gemini.py — Gemini-backed book voice: Ismaili Concepts system instruction.

Re-voices a composed book chapter into the Ismaili Concepts voice:
accessible paragraphs with headings, Arabic terms in Arabic script (parenthetical
after the English word), etymology section at the end, Quran citations in Q|S:V
format, no bold/italic, no references shown.

PIPELINE HOOK
  Called from 0book-compose (or a future 0book-revoice phase) when:
    series:
      use_gemini_composer: true
  is present in the book's meta.yml. Default: false — Claude MAX compose unchanged.

ENGINE
  Pure stdlib urllib — no google-genai SDK dependency.
  API key: _secrets.get_gemini_key() → keychain `llm-gemini-api-key`.
  Default model: gemini-2.5-flash (pipeline standard).

SYSTEM INSTRUCTION
  Derived from the "Ismaili Concepts" Gem, adapted for pipeline use:
    - Removed "attached files / online websites" clause (Tier 1: no file grounding).
    - Added pipeline context: faithfully re-voice a chapter, do not omit.
  Version tracked in GEMINI_VOICE_VERSION below.

STANDALONE SMOKE-TEST
  python3 scripts/podcast/_augment_gemini.py <BOOK_DIR> [<chapter_text_file>]
  If chapter_text_file is omitted, uses stdin.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

# ─── version ─────────────────────────────────────────────────────────────────
GEMINI_VOICE_VERSION = "1.0"
_DEFAULT_MODEL = "gemini-2.5-flash"

# ─── system instruction ───────────────────────────────────────────────────────
# Full Ismaili Concepts Gem system instruction, adapted for pipeline use.
# Key change: "attached files / online websites" clause removed (Tier 1 — no
# file grounding; the Gem's doctrinal intelligence lives in this instruction).
# Added: pipeline-specific task framing at the top.

_SYSTEM_INSTRUCTION = """\
You are the Ismaili Concepts voice for a companion reading edition of a classical \
Ismaili scholarly text. You will receive a fully composed chapter. Your task is to \
re-voice it in the Ismaili Concepts style described below. Preserve every teaching, \
argument, citation, named figure, and Quranic reference from the source chapter — \
do not omit, summarize, or abridge any of them. If the source contains Arabic script \
(Quranic verses, hadith, attributed sayings), reproduce them exactly as given.

Act as an Ismaili Concepts advisor. Your primary goal is to explain complex Ismaili \
concepts in simple, accessible language. Utilize analogies and concrete examples to \
enhance understanding. Present information in a cohesive paragraph format with minimal, \
plain-text headings and subheadings. Understand Arabic terms through their etymology and \
linguistics. Write Arabic words using only the Arabic script, avoiding English \
transliteration. Use a tone that stirs emotions.

Purpose and Goals:
Break down complex Ismaili concepts into fundamental components.
Rephrase complex terminology into simpler terms.
Develop relevant and relatable analogies to illustrate concepts.
Provide clear, real-world examples demonstrating concepts in action.
Ensure all Arabic terms are rendered exclusively in Arabic script; do not bold them.
If there is an English translation of a term, place the Arabic-scripted term in \
parentheses after the English word (e.g., Prayer (صلاة)). Do not show transliterated \
Arabic words in parentheses.
Remove all postscripts and subscripts from the final result.

Behaviors and Rules:

1) Presentation:
Present the entire chapter as paragraphs, each explaining a concept in simple English.
Add headings and subheadings to enhance the readability of the text.
Aim for a smooth, flowing narrative.
Ensure the English explanation is readily copy-and-pastable into a document without \
requiring reformatting.
Do not link or show references in the output.
Avoid phrases like "The text suggests," "The author states," "I begin," or "I understand."
Use an instructional tone but remain casual like you are speaking to someone. \
Prefer "our" instead of "your" when giving examples.
Present explanations in well-structured paragraphs using straightforward language \
accessible to young students.
Do not translate Arabic text into English; keep the original script.
Instead of "God," use "Allah," and use "Maulana Ali" as a substitute for Imam Ali.
For Quran references, cite the specific Surah and verse in the format Q|Surah:Verse \
such as Q|2:10. For multiple consecutive verses, use the format \
Q|SurahNumber:StartVerse-EndVerse such as Q|2:5-10. Place this on a new line \
immediately following the quoted verse.
Do not bold or italicize any text.

2) Etymology Section:
Create a separate section called Etymology at the end of the chapter.
Present the linguistics and etymology of interesting key Arabic terms to provide a \
deeper understanding of how the root connects with the derived word in meaning.
Show the root words and their derivatives in Arabic script.

Overall Tone:
Keep a clear, straightforward, and friendly tone.
Be informative and supportive.
Emphasize clarity and simplicity.
Present all results in plain English text, without links to sources.
Adopt a third-person instructional tone. The final output should be plain text, \
ready for easy copying and pasting into a document.
"""


# ─── meta.yml gate ────────────────────────────────────────────────────────────

def gemini_composer_enabled(book_dir: Path) -> bool:
    """Return True iff series.use_gemini_composer is true in meta.yml."""
    meta = Path(book_dir) / "meta.yml"
    if not meta.exists():
        return False
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        return bool(data.get("series", {}).get("use_gemini_composer", False))
    except Exception:  # noqa: BLE001
        return False


# ─── API call ─────────────────────────────────────────────────────────────────

def _call_gemini(
    text: str,
    *,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 16000,
) -> str:
    """Single-shot Gemini call with the Ismaili Concepts system instruction.

    Pure stdlib urllib — no SDK dependency. Mirrors full_book_denoise._gemini().
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _secrets import get_gemini_key

    api_key = get_gemini_key()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            d = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Gemini HTTP {exc.code}: {exc.read().decode(errors='replace')[:400]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    candidates = d.get("candidates", [])
    if not candidates:
        finish = d.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini returned no candidates (blockReason={finish})")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if not part.get("thought"):
            text_out = part.get("text", "").strip()
            if text_out:
                return "\n".join(line.rstrip() for line in text_out.splitlines())

    raise RuntimeError("Gemini response contained no usable text part")


# ─── public API ───────────────────────────────────────────────────────────────

def revoice_chapter_gemini(
    chapter_text: str,
    book_dir: Path,
    *,
    model: str = _DEFAULT_MODEL,
    log=print,
) -> str:
    """Re-voice a composed book chapter using the Ismaili Concepts voice.

    Args:
        chapter_text: The Claude-composed chapter prose (from 0book-compose).
        book_dir:     Book content directory (used for gate check and cost logging).
        model:        Gemini model override. Default: gemini-2.5-flash.
        log:          Callable for progress messages.

    Returns:
        Re-voiced chapter text in the Ismaili Concepts style, with an
        Etymology section appended.

    Raises:
        RuntimeError: on Gemini API errors (caller decides whether to fall back).
    """
    book_dir = Path(book_dir)
    log(f"  gemini-voice: revoicing chapter ({len(chapter_text)} chars) via {model}…")
    result = _call_gemini(chapter_text, model=model)
    log(f"  gemini-voice: done — {len(result)} chars returned")
    return result


def revoice_book_gemini(
    book_dir: Path,
    *,
    model: str = _DEFAULT_MODEL,
    force: bool = False,
    log=print,
) -> Path:
    """Re-voice every chapter in book/book.md and write book/book-revoiced.md.

    Idempotent: if book-revoiced.md already exists and force=False, skips.
    Uses per-chapter chunk files (book/_chunks/book/bk-NNN.md) if present;
    falls back to splitting book.md on H2 headings.

    Returns the path to book-revoiced.md.
    """
    book_dir = Path(book_dir)
    out_path = book_dir / "book" / "book-revoiced.md"

    if out_path.exists() and not force:
        log(f"  gemini-voice: book-revoiced.md already exists — skipping (pass force=True to redo)")
        return out_path

    chunks_dir = book_dir / "book" / "_chunks" / "book"
    if chunks_dir.exists():
        chunk_files = sorted(chunks_dir.glob("bk-*.md"))
    else:
        chunk_files = []

    if chunk_files:
        log(f"  gemini-voice: revoicing {len(chunk_files)} chapter chunk(s) from {chunks_dir}")
        revoiced_parts: list[str] = []
        for cf in chunk_files:
            chapter_text = cf.read_text(encoding="utf-8").strip()
            if not chapter_text:
                continue
            try:
                revoiced = revoice_chapter_gemini(chapter_text, book_dir, model=model, log=log)
            except RuntimeError as exc:
                log(f"  gemini-voice: ERROR on {cf.name}: {exc} — using original")
                revoiced = chapter_text
            revoiced_parts.append(revoiced)
        assembled = "\n\n---\n\n".join(revoiced_parts)
    else:
        book_md = book_dir / "book" / "book.md"
        if not book_md.exists():
            raise RuntimeError(
                f"book.md not found at {book_md} — run 0book-compose first"
            )
        full_text = book_md.read_text(encoding="utf-8").strip()
        log(f"  gemini-voice: revoicing full book.md ({len(full_text)} chars) as single pass")
        assembled = revoice_chapter_gemini(full_text, book_dir, model=model, log=log)

    out_path.write_text(assembled + "\n", encoding="utf-8")
    log(f"  gemini-voice: wrote {out_path.relative_to(book_dir.parent.parent)}")
    return out_path


# ─── standalone smoke-test ────────────────────────────────────────────────────

def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Smoke-test: revoice a chapter through the Ismaili Concepts voice"
    )
    p.add_argument("book_dir", help="Path to content/<Bucket>/<slug>/")
    p.add_argument(
        "chapter_file",
        nargs="?",
        default="-",
        help="Chapter text file (default: stdin)",
    )
    p.add_argument("--model", default=_DEFAULT_MODEL, help="Gemini model override")
    p.add_argument(
        "--full-book",
        action="store_true",
        help="Revoice all chapter chunks in book/book.md → book/book-revoiced.md",
    )
    p.add_argument("--force", action="store_true", help="Re-run even if output exists")
    args = p.parse_args()

    book_dir = Path(args.book_dir)
    if not book_dir.exists():
        print(f"ERROR: book_dir not found: {book_dir}", file=sys.stderr)
        return 1

    if args.full_book:
        try:
            out = revoice_book_gemini(book_dir, model=args.model, force=args.force)
            print(f"\nOutput written to: {out}")
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.chapter_file == "-":
        chapter_text = sys.stdin.read()
    else:
        cf = Path(args.chapter_file)
        if not cf.exists():
            print(f"ERROR: chapter file not found: {cf}", file=sys.stderr)
            return 1
        chapter_text = cf.read_text(encoding="utf-8")

    if not chapter_text.strip():
        print("ERROR: empty chapter text", file=sys.stderr)
        return 1

    try:
        result = revoice_chapter_gemini(chapter_text, book_dir, model=args.model)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
