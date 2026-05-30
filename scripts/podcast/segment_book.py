#!/usr/bin/env python3
"""segment_book.py — WC8 holistic pipeline: segment unified book into balanced episodes.

Reads the unified-book.md produced by reconcile_book.py and uses Claude Sonnet
(single call) to segment it into equally-sized episodes targeting ~4,500 words each —
suitable for 25–30 min NotebookLM podcast episodes.

Claude Sonnet is used (not Gemini) because segmentation requires understanding
thematic coherence, Ghazali's own rhetorical structure, and what constitutes a
natural narrative break — judgment that benefits from Claude's deeper reasoning.

USAGE
    python3 scripts/podcast/segment_book.py --slug ayyuhal-walad
    python3 scripts/podcast/segment_book.py --slug ayyuhal-walad --target-words 4500
    python3 scripts/podcast/segment_book.py --slug ayyuhal-walad --dry-run

OUTPUT
    chapters-wc8/ch01-<slug>.txt  …  chNN-<slug>.txt   (new chapter files)
    _system/segment-report.json   (segment plan + word counts)
    _system/cost-ledger.json      (appended)

COST (~$0.07–0.15 for 1 Claude Sonnet call)
    Input:  ~20,000 tokens (unified book text + system prompt)
    Output: ~2,000 tokens (segment plan JSON)
    Total:  ~$0.09 at Sonnet 4.6 pricing ($3/$15 per M tokens)

NOTE: Output lands in `chapters-wc8/` NOT `chapters/`. The existing v3.5 chapters/
are preserved until the new chapters are reviewed and promoted. Use assemble_bundle.py
with --prefer-wc8 to use these chapters for podcast assembly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _paths import REPO_ROOT  # noqa: E402

# Claude Sonnet pricing (approximate)
C_IN  = 0.000_000_75   # $/char (~$3/M tokens, ~4 chars/token)
C_OUT = 0.000_003_75   # $/char (~$15/M tokens)

TARGET_WORDS_DEFAULT = 4500

_SEGMENT_SYSTEM = """\
You are a podcast episode architect for an Islamic scholarly text series.

You will receive the full unified text of *Ayyuhal Walad* by Imam al-Ghazali — a short
letter structured as a series of counsels to a spiritual student. The text has been
reconciled from Arabic, English, and scholarly sources and is divided into numbered
sections (## Section N).

YOUR TASK: Group these sections into EPISODES for a podcast series. Each episode should:
  1. Target {target_words} words of source text (suitable for a 25–30 min podcast episode).
  2. Respect Ghazali's thematic boundaries — do NOT cut in the middle of a counsel or argument.
  3. Have a natural narrative arc: an opening tension, a development, and a satisfying close.
  4. Be self-contained — a listener who missed earlier episodes can follow it.

Respond with a JSON object ONLY (no prose before or after):
{{
  "episodes": [
    {{
      "number": 1,
      "slug": "frame-and-first-counsel",
      "title": "The Frame and the First Counsel",
      "sections": [1, 2, 3, 4],
      "theme": "One sentence describing the episode's central question or teaching",
      "opening_tension": "What question or problem opens the episode",
      "closing_resolution": "What the listener will have understood by the end"
    }},
    ...
  ],
  "total_episodes": 5,
  "design_rationale": "2–3 sentences on how you chose the breaks"
}}

Aim for 5–7 episodes. Prioritise coherence over perfect word-count balance — ±30% from
{target_words} words per episode is acceptable if it preserves a natural thematic unit.
"""


def _load_claude_key() -> str:
    """Claude uses the Max subscription via `claude login` — no separate API key in keychain."""
    env = os.environ.get("ANTHROPIC_API_KEY")
    if env:
        return env.strip()
    # The Max subscription runs via `claude` CLI; if an API key is needed for direct calls,
    # it should be in the keychain as 'anthropic_api_key'
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "anthropic_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(
            "No ANTHROPIC_API_KEY env var and anthropic_api_key not in keychain.\n"
            "Set ANTHROPIC_API_KEY or add it to keychain to use Claude Sonnet for segmentation."
        )
    return r.stdout.strip()


def _claude_segment(unified_text: str, target_words: int) -> dict:
    """Call Claude Sonnet to produce the segmentation plan."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=_load_claude_key())
    system = _SEGMENT_SYSTEM.replace("{target_words}", str(target_words))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": unified_text}],
    )
    raw = response.content[0].text if response.content else "{}"
    # Extract JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON in Claude response: {raw[:200]}")
    plan = json.loads(raw[start:end])
    in_chars = len(system) + len(unified_text)
    out_chars = len(raw)
    cost = round(in_chars * C_IN + out_chars * C_OUT, 5)
    return plan, cost


def _extract_section(unified_text: str, section_numbers: list[int]) -> str:
    """Extract the text of the specified section numbers from the unified book."""
    sections = re.split(r"\n(?=## Section \d+)", unified_text)
    out_parts = []
    for sec in sections:
        m = re.match(r"## Section (\d+)", sec)
        if m and int(m.group(1)) in section_numbers:
            out_parts.append(sec.strip())
    return "\n\n---\n\n".join(out_parts)


def _log_cost(slug: str, entry: dict) -> None:
    p = REPO_ROOT / "content" / "drafts" / "books" / slug / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry)
    led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")


def segment(slug: str, *, target_words: int = TARGET_WORDS_DEFAULT, dry_run: bool = False, force: bool = False) -> list[Path]:
    book_dir = REPO_ROOT / "content" / "drafts" / "books" / slug
    unified_path = book_dir / "_system" / "unified-book.md"
    out_dir = book_dir.parent.parent / "books" / slug / "chapters-wc8"  # same tree as chapters/

    # Actually keep it in the book_dir for cleanliness
    out_dir = book_dir / "chapters-wc8"
    report_path = book_dir / "_system" / "segment-report.json"

    if not unified_path.exists():
        raise FileNotFoundError(
            f"unified-book.md not found at {unified_path}. Run reconcile_book.py first."
        )

    if out_dir.exists() and list(out_dir.glob("ch*.txt")) and not force:
        print(f"  chapters-wc8/ already populated — skip (--force to re-segment)")
        return sorted(out_dir.glob("ch*.txt"))

    unified_text = unified_path.read_text(encoding="utf-8")
    total_words = len(unified_text.split())
    estimated_episodes = max(1, round(total_words / target_words))

    print(f"  Unified text: {total_words:,} words → targeting {target_words:,}w/episode "
          f"(~{estimated_episodes} episodes)")
    print(f"  Calling Claude Sonnet for holistic segmentation…", end="", flush=True)

    if dry_run:
        print(" (dry-run)")
        return []

    plan, cost = _claude_segment(unified_text, target_words)
    episodes = plan.get("episodes", [])
    print(f" {len(episodes)} episodes  ~${cost:.5f}")
    print(f"  Rationale: {plan.get('design_rationale', 'n/a')[:120]}")

    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    report_episodes = []

    for ep in episodes:
        n = ep["number"]
        ep_slug = ep.get("slug", f"episode-{n:02d}")
        title = ep.get("title", ep_slug)
        sections = ep.get("sections", [])

        chapter_text = _extract_section(unified_text, sections)
        if not chapter_text:
            print(f"  WARNING: no content found for episode {n} (sections {sections})")
            continue

        word_count = len(chapter_text.split())
        fname = f"ch{n:02d}-{ep_slug}.txt"
        out_path = out_dir / fname

        header = (
            f"# {title}\n\n"
            f"*Episode {n} of {len(episodes)} — {slug}*\n"
            f"*Sections: {', '.join(str(s) for s in sections)} · {word_count:,} words*\n\n"
        )
        out_path.write_text(header + chapter_text + "\n", encoding="utf-8")
        output_paths.append(out_path)

        report_episodes.append({
            "number": n, "slug": ep_slug, "title": title,
            "sections": sections, "word_count": word_count, "file": fname,
            "theme": ep.get("theme", ""), "opening_tension": ep.get("opening_tension", ""),
            "closing_resolution": ep.get("closing_resolution", ""),
        })
        print(f"  EP{n:02d} {fname}: {word_count:,}w  ({', '.join(str(s) for s in sections)} sections)")

    report = {
        "slug": slug,
        "segmented_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target_words": target_words,
        "total_episodes": len(episodes),
        "design_rationale": plan.get("design_rationale", ""),
        "episodes": report_episodes,
        "cost_usd": cost,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    _log_cost(slug, {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "op": "segment_book",
        "service": "claude/claude-sonnet-4-6",
        "in_chars": len(unified_text),
        "out_chars": 2000,
        "cost_usd": cost,
    })

    return output_paths


def main() -> None:
    ap = argparse.ArgumentParser(description="WC8 holistic segmentation — unified book → episodes.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--target-words", type=int, default=TARGET_WORDS_DEFAULT,
                    help=f"Target words per episode (default: {TARGET_WORDS_DEFAULT})")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    print(f"Segment book — {args.slug} (target {args.target_words:,}w/episode)")
    paths = segment(args.slug, target_words=args.target_words, dry_run=args.dry_run, force=args.force)

    ledger = REPO_ROOT / "content" / "drafts" / "books" / args.slug / "_system" / "cost-ledger.json"
    if ledger.exists():
        total = json.loads(ledger.read_text()).get("total_usd", 0.0)
        print(f"\nRunning total cost: ${total:.2f}")
    if paths and not args.dry_run:
        print(f"Episodes written to: {paths[0].parent.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
