#!/usr/bin/env python3
"""full_book_denoise.py — WC8 holistic pipeline: denoise all source streams as full-book text.

Reads each OCR'd source from _system/source/multi/ocr/ and produces a clean
full-book text stream for each, stripping translator apparatus, footnotes,
page numbers, and editorial brackets via Gemini 2.5 Flash.

Unlike the per-chapter gemini_refine.py, this processes EACH SOURCE AS A SINGLE
STREAM — no chapter boundaries are imposed at this stage. Chapter segmentation
happens downstream in segment_book.py after reconciliation.

USAGE
    python3 scripts/podcast/full_book_denoise.py --slug ayyuhal-walad
    python3 scripts/podcast/full_book_denoise.py --slug ayyuhal-walad --source arabic

OUTPUTS
    _system/source/multi/denoised/{arabic,english,scholarly}.md
    _system/cost-ledger.json  (appended)

COST (approx, Gemini 2.5 Flash, thinking disabled)
    Arabic:   ~$0.011  (27K chars, ~70% retention — dense, clean text)
    English:  ~$0.045  (187K chars, ~35% retention — heavy translator apparatus)
    Scholarly:~$0.048  (184K chars, ~40% retention — commentary + apparatus)
    Total:    ~$0.104
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _paths import resolve_content
from _rules import R_NOISE_APPARATUS_DIRECTIVE, strip_noise_reference_attributions

PRICE_IN = 0.000_000_1  # $/char Gemini Flash input
PRICE_OUT = 0.000_000_4  # $/char output

SOURCES = ["arabic", "english", "scholarly"]

# Book-agnostic denoise prompt TEMPLATES (per source role). `{book}` is filled
# from the book's own metadata at run time — NEVER hardcode a title or author
# here (the prior version was hardcoded to "Ayyuhal Walad by Imam al-Ghazali",
# which mis-described every other book). The shared Wave-N apparatus directive
# (R_NOISE_APPARATUS_DIRECTIVE) is appended in build_system_prompts so circulation/
# provenance/colophon noise is stripped at the root for every book.
_TMPL_ARABIC = """\
You are processing a raw OCR of {book} — a classical Arabic scholarly text.

TASK: Strip all OCR artefacts, page numbers, page separators, and editorial apparatus.
Keep: every word of the author's actual Arabic text (in Arabic script), section numbers (Roman or
Arabic numerals), and paragraph breaks.
Remove: page number lines, OCR noise characters, transliteration guides, editor's square-bracket
additions, publisher notes.

OUTPUT DISCIPLINE: return ONLY the cleaned text. No preamble, no explanation.
"""

_TMPL_ENGLISH = """\
You are processing a raw OCR of a heavily-footnoted academic English translation of {book}.

TASK: Extract only the author's actual text in English. Remove ALL translator material:
footnotes (numbered or lettered), translator commentary, page numbers, page separators
(lines like "-51-", "<!-- page 37 -->"), chapter headings added by the translator, bibliographic
citations (Lane TON, Mishcat, etc.), and any text within square brackets [ ] added by the translator.

Keep: every sentence that is the author's own prose, section numbers
(Roman numerals like "I.", "II.", opening address forms), natural paragraph breaks, and Arabic
script attached to authorial terms, Quran/hadith/sayings, prayers, names, titles, and doctrinal
formulae. The Arabic-script terms belong in the chapter source and will be reviewed later during
the phonetic/pronunciation stage.

OUTPUT DISCIPLINE: return ONLY the author's cleaned English prose. No preamble, no explanation.
Begin directly with the first word of the author's text.
"""

_TMPL_SCHOLARLY = """\
You are processing a raw OCR of a scholarly commentary edition of {book}.
This edition interleaves the original text with scholarly commentary and footnotes.

TASK: Extract both (a) the author's original text and (b) substantive scholarly
commentary on the meaning. Remove: page numbers, page separators, bibliographic footnotes,
editorial apparatus, publisher information, OCR noise.

Mark the author's own text with: [AUTHOR] ... [/AUTHOR]
Mark scholarly commentary with: [COMMENTARY] ... [/COMMENTARY]
This attribution lets the reconcile step assign content to the right source layer.

Keep all substantive content — both the original and the commentary that explains it.
OUTPUT DISCIPLINE: return ONLY the marked-up text. No preamble, no explanation.
"""

_TEMPLATES = {
    "arabic": _TMPL_ARABIC,
    "english": _TMPL_ENGLISH,
    "scholarly": _TMPL_SCHOLARLY,
}


def _book_label(slug: str) -> str:
    """Best-effort human label for the book (title from work.yml), book-agnostic.

    Falls back to a generic phrase so a missing/odd metadata file never reinstates
    a hardcoded title. No external YAML dependency — a tiny line scan suffices.
    """
    for rel in ("work.yml", "meta.yml"):
        for base in (resolve_content(slug), resolve_content(slug).parent):
            p = base / rel
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("title:"):
                        title = line.split("title:", 1)[1].strip().strip("'\"")
                        if title:
                            return title
    return "this classical Islamic treatise"


def build_system_prompts(slug: str) -> dict[str, str]:
    """Fill the per-source templates with this book's label and append the
    shared Wave-N apparatus directive. Result is book-specific yet never hardcoded."""
    book = _book_label(slug)
    return {
        src: (tmpl.format(book=book).rstrip() + "\n\n" + R_NOISE_APPARATUS_DIRECTIVE + "\n")
        for src, tmpl in _TEMPLATES.items()
    }


def _load_key() -> str:
    # Vault-deterministic: env -> keychain -> Azure Key Vault (llm-gemini-api-key).
    from _secrets import get_gemini_key

    return get_gemini_key()


def _gemini(system: str, text: str, *, model: str = "gemini-2.5-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={_load_key()}"
    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 32000,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        d = json.loads(resp.read())
    parts = d["candidates"][0]["content"]["parts"]
    for part in parts:
        if not part.get("thought"):
            text_out = part.get("text", "")
            if text_out.strip():
                return "\n".join(line.rstrip() for line in text_out.splitlines())
    return ""


def _log_cost(slug: str, entry: dict) -> None:
    p = resolve_content(slug) / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry)
    led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")


def denoise_source(slug: str, source: str, *, force: bool = False) -> Path:
    """Denoise one source stream. Returns the output path."""
    book_dir = resolve_content(slug)
    in_path = book_dir / "_system" / "source" / "multi" / "ocr" / f"{source}.md"
    out_dir = book_dir / "_system" / "source" / "multi" / "denoised"
    out_path = out_dir / f"{source}.md"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(f"OCR source not found: {in_path}")

    if out_path.exists() and not force:
        print(f"  [{source}] already denoised — skip (--force to re-run)")
        return out_path

    text = in_path.read_text(encoding="utf-8")
    system = build_system_prompts(slug)[source]
    in_chars = len(text)

    print(f"  [{source}] denoising {in_chars:,} chars…", end="", flush=True)
    out = _gemini(system, text)
    out, _reference_tail_strips = strip_noise_reference_attributions(out)
    out_path.write_text(f"# Denoised — {slug} — {source} source\n\n" + out.strip() + "\n", encoding="utf-8")

    out_chars = len(out)
    cost = round(in_chars * PRICE_IN + out_chars * PRICE_OUT, 5)
    retention = round(out_chars / max(in_chars, 1) * 100, 1)
    print(f" {out_chars:,} chars ({retention}% retained)  ~${cost:.5f}")

    _log_cost(
        slug,
        {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "op": f"full_book_denoise_{source}",
            "service": "gemini/gemini-2.5-flash",
            "in_chars": in_chars,
            "out_chars": out_chars,
            "cost_usd": cost,
        },
    )
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="WC8 full-book denoise — all source streams.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--source", choices=SOURCES, help="Denoise only this source")
    ap.add_argument("--force", action="store_true", help="Re-run even if output exists")
    args = ap.parse_args()

    sources = [args.source] if args.source else SOURCES
    print(f"Full-book denoise — {args.slug} ({len(sources)} source(s))")

    for source in sources:
        try:
            denoise_source(args.slug, source, force=args.force)
        except FileNotFoundError as e:
            print(f"  [{source}] SKIP — {e}", file=sys.stderr)

    # The Arabic stream is final once it is denoised, so this is where its marks
    # go on. Idempotent against the fingerprint of each stream, so re-running the
    # denoise with --force re-vowels only what actually changed. Never fatal — an
    # unvowelled source still composes, and `vowel_book` is the net behind it.
    if "arabic" in sources:
        try:
            from vowel_source import vowel_source

            print("\nVowelling the Arabic source…")
            vowel_source(resolve_content(args.slug), apply=True)
        except Exception as e:
            print(f"  vowelling failed (continuing): {e}", file=sys.stderr)

    ledger = resolve_content(args.slug) / "_system" / "cost-ledger.json"
    if ledger.exists():
        total = json.loads(ledger.read_text()).get("total_usd", 0.0)
        print(f"\nRunning total cost: ${total:.2f}")


if __name__ == "__main__":
    main()
