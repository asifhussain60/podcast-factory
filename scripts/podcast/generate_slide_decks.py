#!/usr/bin/env python3
"""generate_slide_decks.py — WC8 Phase 8: Gemini-powered slide deck authoring.

For each chapter in the book, produces the two-file slide deck deliverable:

  slide-decks/chNN-deck-<slug>.txt     — visual-rewritten chapter (SLIDE SOURCE)
  slide-decks/chNN-framing-<slug>.md  — customize prompt (SLIDE FRAMING)

Uses Gemini 2.5 Flash exclusively. NO claude -p.

USAGE
    # Author slide decks for all chapters:
    python3 scripts/podcast/generate_slide_decks.py --slug ayyuhal-walad

    # Single chapter:
    python3 scripts/podcast/generate_slide_decks.py --slug ayyuhal-walad \\
        --chapter ch01-frame-and-first-counsel

    # Overwrite existing:
    python3 scripts/podcast/generate_slide_decks.py --slug ayyuhal-walad --force

COST (approx, Gemini 2.5 Flash)
    ~$0.006–$0.010 per chapter  →  ~$0.03–$0.05 for all 5 Ayyuhal chapters.

OUTPUTS
    slide-decks/chNN-deck-<slug>.txt       — uploaded to NotebookLM slide notebook
    slide-decks/chNN-framing-<slug>.md     — pasted into NotebookLM Customize box
    _system/cost-ledger.json               — running cost ledger (appended)
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

from _paths import REPO_ROOT  # noqa: E402

PRICE_IN = 0.000_000_1  # $/char Gemini 2.5 Flash input (approx)
PRICE_OUT = 0.000_000_4  # $/char output


# ---------------------------------------------------------------------------
# Gemini call (mirrors gemini_refine.py pattern — no shared state)
# ---------------------------------------------------------------------------

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
        raise SystemExit("gemini_api_key not in keychain — cannot call Gemini")
    return r.stdout.strip()


def _gemini(system: str, user: str, *, model: str = "gemini-2.5-flash") -> str:
    """Call Gemini with thinking disabled to keep output sizes predictable."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models"
        f"/{model}:generateContent?key={_load_key()}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8000,  # ~6,000 words max
            "thinkingConfig": {"thinkingBudget": 0},  # disable thinking to prevent runaways
        },
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    # Extract text from the first text part (skip thinking parts if present).
    parts = d["candidates"][0]["content"]["parts"]
    for part in parts:
        if part.get("thought"):
            continue  # skip thinking traces
        text = part.get("text", "")
        if text.strip():
            return text
    return d["candidates"][0]["content"]["parts"][0].get("text", "")


def _log_cost(slug: str, entry: dict) -> None:
    p = REPO_ROOT / "content" / "drafts" / "books" / slug / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry)
    led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Deck-source prompt
# ---------------------------------------------------------------------------

_DECK_SYSTEM = """\
You are an expert visual-content author for an academic Islamic text podcast pipeline.

Your task: rewrite the given chapter source as a VISUALLY-STRUCTURED document optimised for
NotebookLM to render as intelligent diagram slides (not bullet-list slides).

OUTPUT DISCIPLINE:
- Return ONLY the rewritten document. No preamble, no meta-commentary.
- Begin directly with the chapter's H1 title (e.g. "# The Frame and the First Counsel").
- Each section = H2 heading + short structured content.
- KEEP LINES SHORT. No line longer than 120 characters. Wrap table cell content across rows.

STRUCTURE RULES (use these, in this preference order):
1. Concise 3–5 row tables with SHORT cell content (≤ 60 chars per cell). Each concept = 1 row.
2. Named two-column contrasts: left column "Approach A", right column "Approach B".
3. Bulleted hierarchy with explicit indentation for nested relationships.
4. Directed chain: Entity A → Entity B → Entity C (one per line).
5. Prose ONLY for transitions between sections (1–2 sentences max).

AVOID: long tables with multi-sentence cells, unbroken paragraphs, generic bullet lists.

LENGTH: 1,000–2,500 words total. Preserve key ideas; prioritise clarity over completeness.

TERMINOLOGY: keep Arabic terms in phonetic form (tawil, wilaya, batin). Never replace with
English-only paraphrase.

QURAN REFERENCES: cite as Q[chapter]:[verse] (e.g. Q7:179) immediately after the quote.
"""


def _build_deck_source(chapter_text: str) -> str:
    raw = _gemini(_DECK_SYSTEM, chapter_text)
    # Strip trailing whitespace per line (Gemini sometimes pads table cells with thousands of spaces).
    return "\n".join(line.rstrip() for line in raw.splitlines())


# ---------------------------------------------------------------------------
# Slide framing template
# ---------------------------------------------------------------------------

_FRAMING_SYSTEM = """\
You are writing a Slide Customize Prompt for a NotebookLM slide notebook.

The Slide Customize Prompt is pasted into NotebookLM's "Customize" box. It steers NotebookLM's
Slide Deck mode to produce intelligent diagram slides — NOT bullet lists or transcript slides.

OUTPUT FORMAT (reproduce this structure exactly):
  # Slide Framing: {title}

  ## Purpose
  {2–3 sentences: what the slide deck must show that the audio cannot show linearly}

  ## Steering phrases (apply all of the following)
  - {3–5 specific steering phrases that tell NotebookLM which diagram types to produce}

  ## Slide types required
  - {list the diagram types that MUST appear, tied to specific chapter moments}

  ## Do not
  - Restate the audio discussion in bullet-point slides.
  - Produce "title + stock-photo illustration" slides.
  - Use generic relationship labels ("influences", "relates to") — name the specific relationship.

OUTPUT DISCIPLINE: return ONLY the framing. No preamble, no explanation. Begin directly with
the H1 title line.
"""


def _build_slide_framing(chapter_text: str, chapter_title: str) -> str:
    user = f"Chapter title: {chapter_title}\n\nChapter source:\n\n{chapter_text}"
    raw = _gemini(_FRAMING_SYSTEM, user)
    # Ensure the H1 title is present.
    if not raw.strip().startswith("#"):
        raw = f"# Slide Framing: {chapter_title}\n\n{raw}"
    return raw


# ---------------------------------------------------------------------------
# Chapter discovery
# ---------------------------------------------------------------------------

def _load_episode_map(book_dir: Path) -> list[dict]:
    p = book_dir / "_system" / "episode-chapter-map.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())["mapping"]


def _load_contract(book_dir: Path, chapter_slug: str) -> dict:
    contracts_dir = book_dir / "chapter-contracts"
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    for candidate in [f"{chapter_slug}.yml", f"{short_slug}.yml"]:
        p = contracts_dir / candidate
        if p.exists():
            result: dict = {}
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
            return result
    return {}


def _resolve_chapter_file(book_dir: Path, chapter_slug: str) -> Path | None:
    chapters_dir = book_dir / "chapters"
    exact = chapters_dir / f"{chapter_slug}.txt"
    if exact.exists():
        return exact
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    matches = list(chapters_dir.glob(f"ch*-{short_slug}.txt"))
    return matches[0] if matches else None


def _chapter_prefix(chapter_slug: str, ep_num: int) -> str:
    """Return chNN prefix string."""
    return f"ch{ep_num:02d}"


# ---------------------------------------------------------------------------
# Per-chapter authoring
# ---------------------------------------------------------------------------

def author_chapter(
    slug: str,
    book_dir: Path,
    chapter_slug: str,
    ep_num: int,
    *,
    force: bool = False,
) -> bool:
    """Author deck source + framing for one chapter. Returns True on success."""
    sd_dir = book_dir / "slide-decks"
    sd_dir.mkdir(exist_ok=True)

    contract = _load_contract(book_dir, chapter_slug)
    title = contract.get("title", chapter_slug)
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    prefix = _chapter_prefix(chapter_slug, ep_num)

    deck_path = sd_dir / f"{prefix}-deck-{short_slug}.txt"
    framing_path = sd_dir / f"{prefix}-framing-{short_slug}.md"

    if deck_path.exists() and framing_path.exists() and not force:
        print(f"  [{chapter_slug}] already done — skip (--force to overwrite)")
        return True

    chapter_path = _resolve_chapter_file(book_dir, chapter_slug)
    if not chapter_path:
        print(f"  [{chapter_slug}] ERROR: chapter source not found", file=sys.stderr)
        return False

    chapter_text = chapter_path.read_text(encoding="utf-8")
    in_chars = len(chapter_text)

    print(f"  [{chapter_slug}] authoring deck source ({in_chars:,} chars)…", end="", flush=True)
    deck_text = _build_deck_source(chapter_text)
    deck_path.write_text(deck_text + "\n", encoding="utf-8")
    deck_cost = round(in_chars * PRICE_IN + len(deck_text) * PRICE_OUT, 5)
    print(f" {len(deck_text):,} chars → ~${deck_cost:.5f}")

    print(f"  [{chapter_slug}] authoring slide framing…", end="", flush=True)
    framing_text = _build_slide_framing(chapter_text, title)
    framing_path.write_text(framing_text + "\n", encoding="utf-8")
    framing_cost = round(in_chars * PRICE_IN + len(framing_text) * PRICE_OUT, 5)
    print(f" {len(framing_text):,} chars → ~${framing_cost:.5f}")

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _log_cost(slug, {
        "ts": ts, "op": "slide_deck", "service": "gemini/gemini-2.5-flash",
        "chapter": chapter_slug,
        "in_chars": in_chars * 2,
        "out_chars": len(deck_text) + len(framing_text),
        "cost_usd": round(deck_cost + framing_cost, 5),
    })

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="WC8 Phase 8 — slide deck authoring (Gemini).")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--chapter", help="Author only this chapter (full slug, e.g. ch01-frame-and-first-counsel)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing decks")
    ap.add_argument("--model", default="gemini-2.5-flash")
    args = ap.parse_args()

    book_dir = REPO_ROOT / "content" / "drafts" / "books" / args.slug
    if not book_dir.exists():
        print(f"ERROR: book directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    mapping = _load_episode_map(book_dir)
    if not mapping:
        print("ERROR: episode-chapter-map.json missing or empty.", file=sys.stderr)
        sys.exit(1)

    if args.chapter:
        entry = next((e for e in mapping if e["chapter"] == args.chapter), None)
        if entry is None:
            print(f"ERROR: chapter {args.chapter!r} not in episode map.", file=sys.stderr)
            sys.exit(1)
        entries = [entry]
    else:
        entries = mapping

    print(f"Slide deck authoring — {args.slug} ({len(entries)} chapter(s))")
    total_cost = 0.0
    ok = 0
    for entry in entries:
        chapter_slug = entry["chapter"]
        ep_num = entry["n"]
        print(f"\nChapter {ep_num}: {chapter_slug}")
        success = author_chapter(
            args.slug, book_dir, chapter_slug, ep_num, force=args.force,
        )
        if success:
            ok += 1

    # Read updated total cost.
    ledger_path = book_dir / "_system" / "cost-ledger.json"
    if ledger_path.exists():
        total_cost = json.loads(ledger_path.read_text()).get("total_usd", 0.0)

    print(f"\nDone: {ok}/{len(entries)} chapters. Running total cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
