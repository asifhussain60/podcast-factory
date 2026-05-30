#!/usr/bin/env python3
"""gemini_refine.py — WC8 denoise + normalize stages via Gemini (engine routing; NO claude -p).

The ch01-tuned regex denoiser is brittle across chapters (the academic edition's footnote
apparatus is interleaved unpredictably). Gemini handles it robustly. This script runs the two
LLM stages of the chain on a chapter:
  --mode denoise   : strip the scholarly apparatus (footnotes, MS notes, editorial brackets,
                     inline reference digits) and return ONLY the treatise body, VERBATIM.
  --mode normalize : re-voice into the global house style (docs/standards/house-voice.md),
                     scripture/poetry preserved.

Gemini (paid, keychain `gemini_api_key`) per the standing spend authorization. Cost logged.

USAGE
    python3 scripts/podcast/gemini_refine.py --slug ayyuhal-walad --chapter ch02-hatim-eight-benefits --mode denoise
    python3 scripts/podcast/gemini_refine.py --slug ayyuhal-walad --chapter ch02-hatim-eight-benefits --mode normalize
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _cost_ledger import append_gemini_cost  # noqa: E402

# ─── SN-7 Terminus-technicus preservation (R_TERMINUS_PRESERVE) ───────────────
# house-voice.md §2b. The RULE is the standard; the protect-LIST is per-book, tradition-agnostic
# data loaded from <book>/_system/glossary.yml at run time (NOT hardcoded — a Sufi treatise, a
# Stoic letter, and a Vedanta commentary each carry their own terms of art). Orthogonal to
# R-PHONETICS-OUT: Arabic SCRIPT (تأویل) is still stripped (TTS can't read it); the doctrinal
# term is carried by its PHONETIC form (tawil), preserved on every occurrence, glossed once.

def load_protect_terms(slug: str) -> list[str]:
    """Phonetic + transliteration forms from the per-book glossary.yml (the protect-list).

    No PyYAML dependency — mirrors fill_glossary_arabic.parse_glossary_yml's minimal parser.
    Missing/empty glossary => empty list (guard states the general rule, no enumerated terms).
    """
    p = content_dir(slug) / "_system" / "glossary.yml"
    if not p.exists():
        return []
    terms: list[str] = []
    in_entries = False
    for raw in p.read_text(encoding="utf-8").splitlines():
        if raw.startswith("#") or not raw.strip():
            continue
        if raw.startswith("entries:"):
            in_entries = True
            continue
        if not in_entries:
            continue
        line = raw[4:] if raw.startswith("  - ") else (raw[4:] if raw.startswith("    ") else "")
        if not line:
            continue
        k, _, v = line.partition(":")
        if k.strip() in ("phonetic", "transliteration"):
            v = v.strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            if v:
                terms.append(v)
    # de-dupe, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def sn7_guard(terms: list[str]) -> str:
    """The SN-7 terminus-technicus guard, identical for both stages (R_TERMINUS_PRESERVE)."""
    base = (
      "TERMINUS-TECHNICUS GUARD (R_TERMINUS_PRESERVE, mandatory): a terminus technicus is a "
      "precise doctrinal term, not stylistic vocabulary. Preserve every such term in its "
      "PHONETIC (transliterated) form on EVERY occurrence; on the FIRST occurrence you MAY add "
      "a brief English gloss in parentheses, e.g. 'tawil (the inner, esoteric meaning of "
      "scripture)'. NEVER reduce a term to an English gloss only ('tawil' -> 'esoteric "
      "interpretation' is FORBIDDEN). Arabic SCRIPT itself is stripped (the phonetic form "
      "carries the term) — this is about the term's IDENTITY, not its script."
    )
    if terms:
        base += " Known terms for this book (case/diacritic-insensitive): " + ", ".join(terms) + "."
    return base


DENOISE_SYS = (
  "You are a text-cleaning tool for a scholarly book. The input is an OCR'd academic edition of a "
  "classical Islamic treatise, with the treatise BODY interleaved with scholarly APPARATUS "
  "(numbered footnotes, manuscript/variant notes, biographical glosses, editorial brackets [...] "
  "and {...}, page numbers, and inline footnote-reference digits attached to words). "
  "Return ONLY the treatise body text, cleaned of all apparatus. RULES: (1) Do NOT reword, "
  "rewrite, summarize, translate, or add anything — output the body VERBATIM minus apparatus. "
  "(2) Remove footnotes, glosses, manuscript notes, editorial brackets and their contents, page "
  "numbers, section-number labels like 'XVIII.', and stray inline footnote digits. (3) Keep all "
  "Quran/hadith quotations and poetry exactly. (4) Preserve paragraph flow. Output plain text only."
)

def load_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env: return env.strip()
    r = subprocess.run(["security", "find-generic-password", "-s", "gemini_api_key",
                        "-a", os.environ.get("USER", ""), "-w"], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit("gemini_api_key not in keychain")
    return r.stdout.strip()

def gemini(model: str, system: str, user: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={load_key()}"
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16000},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    return d["candidates"][0]["content"]["parts"][0]["text"]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True); ap.add_argument("--chapter", required=True)
    ap.add_argument("--mode", required=True, choices=["denoise", "normalize"])
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--force", action="store_true", help="overwrite existing output (re-spends Gemini)")
    a = ap.parse_args()
    book = content_dir(a.slug)
    sd = book / "_stages" / a.chapter
    guard = sn7_guard(load_protect_terms(a.slug))  # SN-7 protect-list, per-book, run time
    if a.mode == "denoise":
        src, dst = sd / "core.md", sd / "denoised.md"
        system = DENOISE_SYS + "\n\n" + guard
        title = f"# Denoised — {a.chapter} (apparatus stripped via Gemini)"
    else:
        hv = (REPO_ROOT / "docs" / "standards" / "house-voice.md").read_text()
        system = ("OUTPUT DISCIPLINE: return ONLY the re-voiced chapter text. No preamble, no "
                  "'Here is...', no notes, no explanation, no headings about the task. Begin directly "
                  "with the chapter's first words.\n\n" + hv + "\n\n" + guard)
        src, dst = sd / "denoised.md", sd / "normalized.md"
        title = f"# Normalized — {a.chapter} (house voice via Gemini)"
    if not src.exists(): raise SystemExit(f"missing input {src}")
    if dst.exists() and not a.force:
        print(f"[skip] {dst.name} already exists — use --force to re-run (re-spends Gemini).")
        return 0
    text = src.read_text()
    out = gemini(a.model, system, text)
    dst.write_text(title + "\n\n" + out.strip() + "\n")
    append_gemini_cost(book, phase=f"wc8/{a.mode}", step=a.chapter,
                       model=a.model, in_chars=len(text), out_chars=len(out))
    print(f"[{a.mode}] {a.chapter}: {len(text):,} -> {len(out):,} chars -> {dst.name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
