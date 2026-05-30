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
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT  # noqa: E402

# Gemini 2.5-flash list price (approx, USD per 1M tokens).
PRICE = {"in": 0.30 / 1e6, "out": 2.50 / 1e6}

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

def log_cost(slug, entry):
    p = REPO_ROOT / "content" / "drafts" / "books" / slug / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry); led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True); ap.add_argument("--chapter", required=True)
    ap.add_argument("--mode", required=True, choices=["denoise", "normalize"])
    ap.add_argument("--model", default="gemini-2.5-flash")
    a = ap.parse_args()
    sd = REPO_ROOT / "content" / "drafts" / "books" / a.slug / "_stages" / a.chapter
    if a.mode == "denoise":
        src, dst, system = sd / "core.md", sd / "denoised.md", DENOISE_SYS
        title = f"# Denoised — {a.chapter} (apparatus stripped via Gemini)"
    else:
        hv = (REPO_ROOT / "docs" / "standards" / "house-voice.md").read_text()
        system = ("OUTPUT DISCIPLINE: return ONLY the re-voiced chapter text. No preamble, no "
                  "'Here is...', no notes, no explanation, no headings about the task. Begin directly "
                  "with the chapter's first words.\n\n" + hv)
        src, dst = sd / "denoised.md", sd / "normalized.md"
        title = f"# Normalized — {a.chapter} (house voice via Gemini)"
    if not src.exists(): raise SystemExit(f"missing input {src}")
    text = src.read_text()
    out = gemini(a.model, system, text)
    dst.write_text(title + "\n\n" + out.strip() + "\n")
    cost = round(len(text)/4*PRICE["in"] + len(out)/4*PRICE["out"], 5)
    log_cost(a.slug, {"ts": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"), "op": a.mode,
                      "service": f"gemini/{a.model}", "chapter": a.chapter,
                      "in_chars": len(text), "out_chars": len(out), "cost_usd": cost})
    print(f"[{a.mode}] {a.chapter}: {len(text):,} -> {len(out):,} chars -> {dst.name}  (~${cost:.5f})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
