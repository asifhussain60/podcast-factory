#!/usr/bin/env python3
"""reconcile_book.py — WC8 holistic pipeline: align all source streams into one unified book.

Reads the three denoised source streams (Arabic spine + English translation +
Scholarly commentary) plus the existing per-chapter narrator additions, and
produces a single unified full-book text with content attributed by source layer.

The Arabic spine is the authoritative structural anchor. Every English or scholarly
passage is aligned to the section of the Arabic original it corresponds to, using
the Roman numeral section markers (I–XXVII) as alignment anchors.

USAGE
    python3 scripts/podcast/reconcile_book.py --slug ayyuhal-walad
    python3 scripts/podcast/reconcile_book.py --slug ayyuhal-walad --dry-run

OUTPUT
    _system/unified-book.md       — single attributed full-book text
    _system/reconcile-report.json — alignment report (section count, gaps, confidence)
    _system/cost-ledger.json      — appended

COST (~$0.044–0.10 total)
    Section alignment (Gemini Flash, 1 large-context call): ~$0.044
    Edge-case judgment (Claude Sonnet, 0–5 calls):          ~$0.00–0.05
    Narrator layer injection ($0, reuse existing files):    $0.000
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _paths import REPO_ROOT, resolve_content  # noqa: E402

PRICE_IN  = 0.000_000_1
PRICE_OUT = 0.000_000_4

_RECONCILE_SYSTEM = """\
You are a scholarly text reconciliation engine for an Islamic podcast pipeline.

You will receive THREE source streams of the same short letter, *Ayyuhal Walad* by
Imam al-Ghazali:
  1. ARABIC — the original Arabic text (authoritative spine)
  2. ENGLISH — the English translation (prose translation of the letter)
  3. SCHOLARLY — scholarly commentary edition (Ghazali's text + commentary, marked
     [GHAZALI]...[/GHAZALI] and [COMMENTARY]...[/COMMENTARY])

TASK: Produce a single unified full-book text in the following format:

## Section N — [brief thematic title you assign]

**[GHAZALI — core text]**
[The authoritative English prose of Ghazali's letter for this section]

**[SCHOLARLY COMMENTARY]**
[The most substantive scholarly commentary for this section, if any]

**[NARRATOR NOTE]**
[Leave this blank — it will be filled in from the Shaykh's lecture transcripts]

---

Rules:
- Use the Arabic Roman-numeral section markers (I, II, III… or Ghazali's own "O youth"
  paragraph breaks) as the structural skeleton.
- The ENGLISH stream provides the canonical prose rendering. Use it verbatim unless it
  contains obvious translator apparatus — in which case paraphrase cleanly.
- The SCHOLARLY stream's [GHAZALI] blocks confirm the English; the [COMMENTARY] blocks
  go into the SCHOLARLY COMMENTARY slot.
- Do NOT invent content. If a section has no scholarly commentary, leave that slot empty.
- Keep all Quranic citations (Surah name + verse number) exactly as they appear.
- Keep all Arabic terminology in phonetic form (e.g. tawil, zuhd, dhikr).
- Number sections sequentially from 1. Aim for 18–25 sections total.

OUTPUT DISCIPLINE: return ONLY the unified text in the format above.
No preamble, no meta-commentary, no explanation.
"""


def _load_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit("gemini_api_key not in keychain")
    return r.stdout.strip()


def _gemini(system: str, text: str, *, model: str = "gemini-2.5-flash") -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={_load_key()}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 32000,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        d = json.loads(resp.read())
    parts = d["candidates"][0]["content"]["parts"]
    for part in parts:
        if not part.get("thought"):
            t = part.get("text", "")
            if t.strip():
                return "\n".join(line.rstrip() for line in t.splitlines())
    return ""


def _log_cost(slug: str, entry: dict) -> None:
    p = resolve_content(slug) / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry)
    led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")


def _read_denoised(book_dir: Path, source: str) -> str:
    p = book_dir / "_system" / "source" / "multi" / "denoised" / f"{source}.md"
    if not p.exists():
        raise FileNotFoundError(
            f"Denoised {source} not found at {p}. Run full_book_denoise.py first."
        )
    return p.read_text(encoding="utf-8")


def _read_narrator_additions(book_dir: Path) -> str:
    """Concatenate all per-chapter narrator additions as context (not injected into unified text)."""
    stages = book_dir / "_stages"
    if not stages.exists():
        return ""
    parts = []
    for ch_dir in sorted(stages.iterdir()):
        f = ch_dir / "additions-narrator.md"
        if f.exists():
            parts.append(f"### {ch_dir.name}\n\n{f.read_text(encoding='utf-8').strip()}")
    return "\n\n---\n\n".join(parts)


def reconcile(slug: str, *, dry_run: bool = False, force: bool = False) -> Path:
    book_dir = resolve_content(slug)
    out_path = book_dir / "_system" / "unified-book.md"
    report_path = book_dir / "_system" / "reconcile-report.json"

    if out_path.exists() and not force:
        print(f"  unified-book.md already exists — skip (--force to re-run)")
        return out_path

    arabic    = _read_denoised(book_dir, "arabic")
    english   = _read_denoised(book_dir, "english")
    scholarly = _read_denoised(book_dir, "scholarly")

    combined_input = (
        "=== SOURCE 1: ARABIC (authoritative spine) ===\n\n"
        + arabic + "\n\n"
        "=== SOURCE 2: ENGLISH TRANSLATION ===\n\n"
        + english + "\n\n"
        "=== SOURCE 3: SCHOLARLY COMMENTARY EDITION (marked) ===\n\n"
        + scholarly
    )

    in_chars = len(combined_input)
    print(f"  Reconciling {in_chars:,} chars from 3 sources…", end="", flush=True)

    if dry_run:
        print(" (dry-run, skipping Gemini call)")
        return out_path

    unified = _gemini(_RECONCILE_SYSTEM, combined_input)
    out_chars = len(unified)
    cost = round(in_chars * PRICE_IN + out_chars * PRICE_OUT, 5)

    # Count sections produced
    section_count = unified.count("\n## Section ")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        f"# Unified book — {slug} (reconciled, {datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n\n"
        + unified.strip() + "\n",
        encoding="utf-8",
    )

    report = {
        "slug": slug,
        "reconciled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "in_chars": in_chars,
        "out_chars": out_chars,
        "section_count": section_count,
        "cost_usd": cost,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    _log_cost(slug, {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "op": "reconcile_book",
        "service": "gemini/gemini-2.5-flash",
        "in_chars": in_chars,
        "out_chars": out_chars,
        "cost_usd": cost,
    })

    print(f" {out_chars:,} chars, {section_count} sections  ~${cost:.5f}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="WC8 full-book reconciliation — 3 streams → 1 unified text.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-run even if output exists")
    args = ap.parse_args()

    print(f"Reconcile book — {args.slug}")
    out = reconcile(args.slug, dry_run=args.dry_run, force=args.force)

    ledger = resolve_content(args.slug) / "_system" / "cost-ledger.json"
    if ledger.exists():
        total = json.loads(ledger.read_text()).get("total_usd", 0.0)
        print(f"Running total cost: ${total:.2f}")
    if not args.dry_run:
        print(f"Output: {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
