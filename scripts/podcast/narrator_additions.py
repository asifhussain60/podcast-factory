#!/usr/bin/env python3
"""narrator_additions.py — WC8.1 attributed ADDITIONS layer from the lecture transcripts.

The 12 Shaykh Abdullah Misra lectures are the spoken EXPLAINER source. This tool assembles the
lecture(s) mapped to a chapter and Gemini-cleans the raw STT (filler, false starts, verbal tics
removed) into coherent attributed commentary — the narrator-additions layer, kept DISTINCT from
the core (it's the Shaykh's explanation, not the treatise text). Gemini-only; NO claude -p.

USAGE
    python3 scripts/podcast/narrator_additions.py --slug ayyuhal-walad \\
        --chapter ch03-the-path --lectures lec07-recognizing-the-true-spiritual-guide,lec08-adab-with-a-spiritual-guide
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _cost_ledger import append_gemini_cost  # noqa: E402
SYS = (
  "You are cleaning a raw speech-to-text transcript of a spoken Islamic lecture by Shaykh Abdullah "
  "Misra explaining al-Ghazali's 'Ayyuhal Walad'. Turn it into coherent, readable COMMENTARY prose. "
  "RULES: (1) Remove filler, false starts, repetitions, verbal tics, audience asides, and "
  "transcription noise. (2) Preserve the teaching content, examples, and explanations faithfully — "
  "this is the Shaykh's commentary, an attributed ADDITION, not the treatise itself; do NOT invent. "
  "(3) Keep it as the Shaykh's explanatory voice (third-person teaching), well-paragraphed. "
  "(4) Output ONLY the cleaned commentary — no preamble, no 'Here is', no notes."
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
    body = json.dumps({"system_instruction": {"parts": [{"text": system}]},
                       "contents": [{"parts": [{"text": user}]}],
                       "generationConfig": {"temperature": 0.3, "maxOutputTokens": 32000}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    return d["candidates"][0]["content"]["parts"][0]["text"]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True); ap.add_argument("--chapter", required=True)
    ap.add_argument("--lectures", required=True, help="comma-separated lecture slugs")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--force", action="store_true", help="overwrite existing output (re-spends Gemini)")
    a = ap.parse_args()
    book = content_dir(a.slug)
    dst = book / "_stages" / a.chapter / "additions-narrator.md"
    if dst.exists() and not a.force:
        print(f"[skip] {dst.name} already exists — use --force to re-run (re-spends Gemini).")
        return 0
    lec_dir = book / "_system" / "source" / "lectures"
    names = [n.strip() for n in a.lectures.split(",") if n.strip()]
    parts = []
    for n in names:
        f = lec_dir / f"{n}.txt"
        if not f.exists(): raise SystemExit(f"missing lecture {f}")
        parts.append(f"## {n}\n{f.read_text()}")
    raw = "\n\n".join(parts)
    out = gemini(a.model, SYS, raw)
    dst.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Narrator additions — {a.chapter} (Shaykh Abdullah Misra, attributed commentary)\n\n"
              f"_Cleaned from lecture transcript(s): {', '.join(names)}. This is the explainer's "
              f"commentary (an attributed ADDITION), distinct from the treatise core._\n\n")
    dst.write_text(header + out.strip() + "\n")
    append_gemini_cost(book, phase="wc8/narrator-additions", step=a.chapter,
                       model=a.model, in_chars=len(raw), out_chars=len(out))
    print(f"[narrator] {a.chapter}: {len(raw):,} -> {len(out):,} chars -> {dst.name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
