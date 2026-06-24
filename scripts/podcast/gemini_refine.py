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
from _rules import R_NOISE_APPARATUS_DIRECTIVE  # noqa: E402

# ─── SN-7 Terminus-technicus preservation (R_TERMINUS_PRESERVE) ───────────────
# house-voice.md §2b. The RULE is the standard; the protect-LIST is per-book, tradition-agnostic
# data loaded from <book>/_system/glossary.yml at run time (NOT hardcoded — a Sufi treatise, a
# Stoic letter, and a Vedanta commentary each carry their own terms of art). Orthogonal to
# R-PHONETICS-OUT: Arabic SCRIPT (تأویل) is still stripped (TTS can't read it); the doctrinal
# term is carried by its Arabic script and/or phonetic form, preserved on every occurrence,
# glossed once.

def load_protect_terms(slug: str) -> list[str]:
    """Phonetic + transliteration forms from the per-book glossary.yml (the protect-list).

    No PyYAML dependency — mirrors fill_glossary_arabic.parse_glossary_yml's minimal parser.
    Missing/empty glossary => empty list (guard states the general rule, no enumerated terms).
    """
    p = REPO_ROOT / "content" / "drafts" / "books" / slug / "_system" / "glossary.yml"
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
      "Arabic SCRIPT when present and in its PHONETIC/transliterated identity on EVERY occurrence; "
      "on the FIRST occurrence you MAY add a brief English gloss in parentheses, e.g. "
      "'تأويل / tawil (the inner, esoteric meaning of scripture)'. NEVER reduce a term to an "
      "English gloss only ('tawil' -> 'esoteric interpretation' is FORBIDDEN). Arabic SCRIPT is "
      "source content for the review pipeline, not audio noise; preserve it unless it belongs "
      "only to stripped publisher/OCR apparatus."
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
  "Quran/hadith quotations, poetry, Arabic-script terms, Arabic-script names, prayers, and "
  "doctrinal formulae exactly. (4) Preserve paragraph flow. Output plain text only."
  "\n\n" + R_NOISE_APPARATUS_DIRECTIVE
)

# ─── Consumer-voice denoise (category: sites) ────────────────────────────────
# Used when --mode web-consumer-denoise. Strips legal/compliance jargon from
# web-sourced product content and re-voices for a consumer podcast audience.
# Accuracy is mandatory — no exaggeration, no invented content.
DENOISE_SYS_WEB_CONSUMER = """\
You are a consumer-voice editor preparing health-benefits content for a podcast aimed at regular \
working Americans — people who have never studied tax law and do not want to. The source text \
describes health benefits products (HSAs, FSAs, HRAs, COBRA, commuter benefits, dependent care \
accounts). Your job is to remove all legal, regulatory, and compliance language and replace it \
with plain, warm, accurate English — without changing any fact, number, limit, or product feature.

WHAT TO STRIP — legal apparatus:
- IRS section citations (IRC §213(d), Section 106, etc.) — remove entirely
- Formal legal definitions ("for purposes of this subsection", "as defined under") — cut
- Compliance boilerplate: "pursuant to", "notwithstanding", "herein", "thereof", "therein" — cut
- Hedge clauses that add no listener value: "subject to applicable law", "consult your tax advisor",
  "may vary by jurisdiction" — cut unless genuinely material to a consumer decision
- Regulatory minimum/maximum framing ("federal minimums", "as required under ERISA") — just state
  the actual number or rule in plain English

WHAT TO REPLACE — jargon with plain equivalents:
- "qualifying event" → "a life change like losing your job, getting divorced, or having a baby"
- "continuation coverage" → "keeping your health insurance going"
- "plan document" → "your benefits guide" or "enrollment paperwork"
- "election" (benefits context) → "how much you choose to set aside"
- "incur eligible expenses" → "spend money on covered health costs"
- "open enrollment period" → "benefits sign-up season (usually each fall)"
- "gross misconduct" → "serious workplace misconduct"
- "FICA taxes" → "Social Security and Medicare taxes"
- "taxable income" → "the income the IRS taxes"
- "tax-advantaged" → on first use, explain: "meaning you never pay income tax on..."
- "HDHP" → always write "high-deductible health plan" — never the bare acronym
- "qualified medical expenses" / "QME" → "eligible health costs" or describe concretely
- "premium" → keep, but explain on first use ("the monthly cost of your health insurance")
- "deductible" → keep, but explain on first use ("the amount you pay before insurance kicks in")
- "ICHRA" / "QSEHRA" → write out once, then use "this type of HRA" or the descriptive name

WHAT TO KEEP UNCHANGED — accuracy is mandatory:
- Every dollar figure, contribution limit, percentage, and date
- Every product feature and benefit description (just in plain language)
- The COBRA acronym itself is fine — the legal scaffolding around it is not
- All company names, platform names, and proper nouns
- Any statistics or research findings cited in the source

VOICE:
- Second-person ("you", "your") wherever the source permits — speak to the listener
- Warm and encouraging — these products genuinely help people; treat that as true
- No promotional superlatives ("revolutionary", "game-changing") — plain and honest
- Do NOT add content not present in the source
- Do NOT exaggerate savings, benefits, or product capabilities
- Preserve the frontmatter block (--- ... ---) exactly as-is; only edit the prose body

OUTPUT DISCIPLINE: return ONLY the cleaned text. No preamble, no explanation, no task headings. \
Preserve the YAML frontmatter (--- block) verbatim. Begin the prose body where it begins in \
the input.\
"""

def load_key() -> str:
    # Vault-deterministic (llm-gemini-api-key).
    from _secrets import get_gemini_key
    return get_gemini_key()


def gemini(model: str, system: str, user: str) -> str:
    from _engine import engine_guard, TASK_DENOISE, ENGINE_GEMINI
    engine_guard(TASK_DENOISE, ENGINE_GEMINI)
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
    ap = argparse.ArgumentParser(
        description="Gemini denoise/normalize for the podcast pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  denoise              Scholarly OCR apparatus strip (WC8 / classical books)\n"
            "  normalize            House-voice re-voice (WC8 / classical books)\n"
            "  web-consumer-denoise Legal/compliance jargon strip for sites category content\n\n"
            "For web-consumer-denoise, use --input / --output to specify arbitrary file paths\n"
            "instead of the default _stages/<chapter>/ layout."
        ),
    )
    ap.add_argument("--slug", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--mode", required=True, choices=["denoise", "normalize", "web-consumer-denoise"])
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--force", action="store_true", help="overwrite existing output (re-spends Gemini)")
    ap.add_argument("--input", dest="input_path", default=None,
                    help="Override source file path (used with web-consumer-denoise)")
    ap.add_argument("--output", dest="output_path", default=None,
                    help="Override output file path (used with web-consumer-denoise; "
                         "omit to edit in-place)")
    a = ap.parse_args()
    book = content_dir(a.slug)

    if a.mode == "web-consumer-denoise":
        # ── Consumer jargon strip for sites category ──────────────────────────
        if a.input_path is None:
            raise SystemExit(
                "web-consumer-denoise requires --input <file>  "
                "(e.g. content/drafts/<slug>/chapters/ch01-foo.md)"
            )
        src = Path(a.input_path)
        # Default: edit in-place (overwrite the source file)
        dst = Path(a.output_path) if a.output_path else src
        system = DENOISE_SYS_WEB_CONSUMER
        label = f"web-consumer-denoise/{src.name}"
        if not src.exists():
            raise SystemExit(f"missing input {src}")
        if dst.exists() and dst != src and not a.force:
            print(f"[skip] {dst} already exists — use --force to re-run.")
            return 0
        text = src.read_text(encoding="utf-8")
        out = gemini(a.model, system, text)
        dst.write_text(out.strip() + "\n", encoding="utf-8")
        append_gemini_cost(book, phase="consumer-denoise", step=src.stem,
                           model=a.model, in_chars=len(text), out_chars=len(out))
        delta = len(out) - len(text)
        sign = "+" if delta >= 0 else ""
        print(f"[web-consumer-denoise] {src.name}: {len(text):,} → {len(out):,} chars "
              f"({sign}{delta:,})  →  {dst}")
        return 0

    # ── Existing WC8 scholarly modes ─────────────────────────────────────────
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
