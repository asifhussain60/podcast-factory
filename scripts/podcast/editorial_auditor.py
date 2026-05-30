#!/usr/bin/env python3
"""editorial_auditor.py — WC8 editorial quality auditor for narrator stage files.

Scans the narrator additions layer (_stages/<ch>/additions-narrator.md) of each
chapter and produces a structured findings JSON the Studio editor reads to pre-apply
suppress/consolidate annotations.

Two-layer detection:
  Layer 1 — deterministic pattern registry (zero cost, always runs).
  Layer 2 — Gemini judgment call (~$0.001/chapter, only when Layer 1 is ambiguous).

OUTPUT
    content/drafts/books/<slug>/_system/editorial-audit/<chapter>.json

    {
      "slug":       "ayyuhal-walad",
      "chapter":    "ch01-frame-and-first-counsel",
      "stage":      "narrator",
      "audited_at": "2026-05-30T...",
      "findings": [
        {
          "id":                    "EA-001",
          "paragraph_index":       0,       // 0-based, matches TipTap order after H1 strip
          "action":                "suppress",  // "suppress" | "consolidate" | "keep"
          "confidence":            "high",   // "high" (deterministic) | "medium" (LLM)
          "reason":                "Pipeline metadata artifact — lec transcript provenance",
          "pattern":               "METADATA_ITALIC",
          "condensed_replacement": null      // str for consolidate, null for suppress/keep
        }
      ],
      "pipeline_gap": false  // true when normalized word count < 400 (thin chapter warning)
    }

CLI
    python3 scripts/podcast/editorial_auditor.py --slug ayyuhal-walad
    python3 scripts/podcast/editorial_auditor.py --slug ayyuhal-walad --chapter ch01-frame-and-first-counsel
    python3 scripts/podcast/editorial_auditor.py --slug ayyuhal-walad --dry-run
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
from _paths import REPO_ROOT, resolve_content  # noqa: E402

STAGE = "narrator"
STAGE_FILE = "additions-narrator.md"
AUDIT_DIR_NAME = "editorial-audit"

# ── Pattern registry (Layer 1) ──────────────────────────────────────────────
# Each entry: (pattern_id, action, confidence, regex, reason_template)
# Patterns are checked against EACH paragraph. Order matters — first match wins.

PATTERN_REGISTRY = [
    # H1 stage label — always the very first paragraph when rendered
    (
        "H1_STAGE_LABEL",
        "suppress",
        "high",
        re.compile(r"^# .{5,120}$", re.MULTILINE),
        "Stage heading — redundant with editor stage tab; not content.",
    ),
    # Italic metadata paragraph (provenance comment)
    (
        "METADATA_ITALIC",
        "suppress",
        "high",
        re.compile(
            r"^_(?:Cleaned from lecture transcript|Extracted span:|Re-voiced from the)",
            re.IGNORECASE,
        ),
        "Pipeline metadata artifact — provenance comment not intended for the reader.",
    ),
    # Lecture recap bridge — "The previous lesson concluded with..."
    (
        "LECTURE_RECAP_BRIDGE",
        "consolidate",
        "high",
        re.compile(
            r"^(?:The (?:previous|last) (?:lesson|class|week|session)|"
            r"Recalling the previous|"
            r"Last week[,\s]|"
            r"Previous week[,\s])",
            re.IGNORECASE,
        ),
        "Lecture-bridge opener — references 'previous lesson', meaningless in a self-contained episode.",
    ),
    # Biographical run of ≥1 para (detected by bio-signal density; see _bio_block_scan)
    # — handled separately via _bio_block_scan, not here
]

# Bio-signal words that mark a paragraph as biographical background
_BIO_SIGNALS = re.compile(
    r"\b(?:was born|AH|[Aa]nno [Hh]egirae|passed away|died in|"
    r"lived for \d+ years?|appointed to|studied under|"
    r"his lineage|mastered all disciplines|began his studies|"
    r"[Bb]orn in \w+.*\d{3,4})\b"
)
BIO_MIN_PARAS = 2  # need at least this many consecutive bio paras to flag the block


# ── Gemini judge (Layer 2) ────────────────────────────────────────────────────

def _gemini_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit("gemini_api_key not in keychain — cannot run LLM judgment")
    return r.stdout.strip()


def _gemini_judge(paragraph: str) -> str:
    """Ask Gemini: is this paragraph background/biographical or substantive teaching?
    Returns 'background' or 'teaching'.
    """
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent?key=" + _gemini_key()
    )
    system = (
        "You are an editorial classifier for an Islamic scholarly podcast pipeline. "
        "Classify the paragraph as exactly one of: 'background' or 'teaching'.\n\n"
        "'background': biographical context about the author (birth, death, education, "
        "career, titles, lineage), encyclopedic historical facts, lecture recap phrases "
        "('last week we covered...'), administrative filler, or apparatus text.\n\n"
        "'teaching': the Shaykh's substantive commentary on what Ghazali is arguing — "
        "spiritual insight, doctrinal explanation, practical application, Quranic exegesis, "
        "hadith discussion, or direct engagement with the letter's teaching.\n\n"
        "Reply with ONLY one word: background OR teaching."
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": paragraph[:1200]}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10,
                             "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read())
    raw = d["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
    return "background" if "background" in raw else "teaching"


# ── Bio-block scanner ────────────────────────────────────────────────────────

def _bio_block_scan(
    paras: list[str],
    *,
    use_llm: bool,
    dry_run: bool,
) -> list[tuple[int, int]]:
    """Return list of (start_idx, end_idx) inclusive ranges of biographical blocks.

    A bio block is BIO_MIN_PARAS+ consecutive paragraphs each scoring ≥1 bio signal.
    When use_llm is True, ambiguous paragraphs (bio_signals == 1) are judged by Gemini.
    """
    bio_score: list[int] = []
    for para in paras:
        hits = len(_BIO_SIGNALS.findall(para))
        bio_score.append(hits)

    # Resolve ambiguous paragraphs with Gemini when enabled
    if use_llm and not dry_run:
        for i, (para, score) in enumerate(zip(paras, bio_score)):
            if score == 1 and len(para.split()) > 20:
                verdict = _gemini_judge(para)
                bio_score[i] = 3 if verdict == "background" else 0

    blocks: list[tuple[int, int]] = []
    i = 0
    while i < len(bio_score):
        if bio_score[i] >= 1:
            j = i
            while j < len(bio_score) and bio_score[j] >= 1:
                j += 1
            if j - i >= BIO_MIN_PARAS:
                blocks.append((i, j - 1))
            i = j
        else:
            i += 1
    return blocks


# ── Condensed replacement generator ─────────────────────────────────────────

def _make_condensed_bio(paras: list[str]) -> str:
    """Produce a 2-3 sentence condensed replacement for a biographical block."""
    # Extract key facts from the paragraphs heuristically.
    full_text = " ".join(paras)

    # Try to pull birth year, title, and key work
    born = re.search(r"born[^.]*?(\d{3,4}\s*AH|\d{3,4}\s*AD|\d{3,4}\s*CE)", full_text)
    title = re.search(r"(Hujjat al-Islam|Proof of Islam|Hujjatul Islam)", full_text)
    work = re.search(r"(Ihya Ulum al-Din|Ihya'? '?Ulum|Revival of the Religious Sciences)", full_text)

    parts = ["Imam al-Ghazali"]
    if title:
        parts.append(f"— {title.group(1)}")
    if born:
        parts.append(f"born {born.group(1)}")
    parts_str = " ".join(parts) + " — "

    suffix = ""
    if work:
        suffix = (
            "spent decades mastering the Islamic sciences before a spiritual crisis led him to "
            "produce the Ihya Ulum al-Din. Ayyuhal Walad is a later distillation of that work, "
            "written in response to a student's request for concise, actionable guidance."
        )
    else:
        suffix = (
            "was one of the most influential scholars in Islamic history, whose written legacy "
            "continues to shape Islamic spirituality. This letter is among his most personal works."
        )

    return parts_str + suffix


# ── Main auditor ─────────────────────────────────────────────────────────────

def audit_chapter(
    slug: str,
    chapter: str,
    *,
    use_llm: bool = True,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Run the full audit on one chapter's narrator stage file. Returns the findings dict."""
    book_dir = resolve_content(slug)
    stage_path = book_dir / "_stages" / chapter / STAGE_FILE

    if not stage_path.exists():
        print(f"  [{chapter}] narrator file not found — skipping", file=sys.stderr)
        return {}

    raw = stage_path.read_text(encoding="utf-8")

    # Split into paragraphs preserving order. Empty lines as separators.
    paras = [p.strip() for p in raw.split("\n\n") if p.strip()]

    # Check pipeline gap (thin normalized)
    normalized = book_dir / "_stages" / chapter / "normalized.md"
    norm_words = len(normalized.read_text().split()) if normalized.exists() else 0
    pipeline_gap = norm_words < 400

    findings: list[dict] = []
    ea_counter = 0

    def _finding(para_idx, action, confidence, reason, pattern, replacement=None):
        nonlocal ea_counter
        ea_counter += 1
        return {
            "id": f"EA-{ea_counter:03d}",
            "paragraph_index": para_idx,
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "pattern": pattern,
            "condensed_replacement": replacement,
        }

    # Layer 1: deterministic pattern scan
    matched_indices: set[int] = set()
    for i, para in enumerate(paras):
        for pat_id, action, confidence, regex, reason in PATTERN_REGISTRY:
            if regex.search(para):
                findings.append(_finding(i, action, confidence, reason, pat_id))
                matched_indices.add(i)
                if verbose:
                    print(f"  P{i:02d} [{pat_id}] {action.upper()}: {para[:80]}...")
                break

    # Bio-block scan (runs on unmatched paragraphs)
    unmatched_paras = [(i, p) for i, p in enumerate(paras) if i not in matched_indices]
    unmatched_texts = [p for _, p in unmatched_paras]
    bio_blocks = _bio_block_scan(unmatched_texts, use_llm=use_llm, dry_run=dry_run)

    for start, end in bio_blocks:
        # Map back to original para indices
        orig_start = unmatched_paras[start][0]
        orig_end   = unmatched_paras[end][0]
        block_paras = [unmatched_paras[j][1] for j in range(start, end + 1)]
        replacement = None if dry_run else _make_condensed_bio(block_paras)
        confidence = "medium" if use_llm else "high"

        for j in range(start, end + 1):
            orig_idx = unmatched_paras[j][0]
            findings.append(_finding(
                orig_idx,
                "consolidate",
                confidence,
                f"Biographical background — {end - start + 1} consecutive paragraphs "
                f"(P{orig_start}–P{orig_end}); condense to 1 para before substantive commentary.",
                "BIO_INTRO_BLOCK",
                replacement if j == start else "(see first paragraph of block)",
            ))
            matched_indices.add(orig_idx)
            if verbose:
                print(f"  P{orig_idx:02d} [BIO_INTRO_BLOCK] CONSOLIDATE: {unmatched_paras[j][1][:80]}...")

    # Sort by paragraph index
    findings.sort(key=lambda f: f["paragraph_index"])

    result = {
        "slug": slug,
        "chapter": chapter,
        "stage": STAGE,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "findings": findings,
        "pipeline_gap": pipeline_gap,
        "summary": {
            "suppress": sum(1 for f in findings if f["action"] == "suppress"),
            "consolidate": sum(1 for f in findings if f["action"] == "consolidate"),
            "pipeline_gap_words": norm_words if pipeline_gap else None,
        },
    }

    if not dry_run:
        out_dir = book_dir / "_system" / AUDIT_DIR_NAME
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{chapter}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if verbose:
            print(f"  [{chapter}] wrote {out_path.relative_to(REPO_ROOT)}")

    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Editorial auditor — scan narrator stage files for suppress/consolidate findings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--slug", required=True, help="Book slug (e.g. ayyuhal-walad)")
    ap.add_argument("--chapter", help="Audit only this chapter slug")
    ap.add_argument("--no-llm", action="store_true", help="Disable Gemini Layer-2 judgment (faster, less accurate)")
    ap.add_argument("--dry-run", action="store_true", help="Print findings; do not write JSON")
    ap.add_argument("--verbose", action="store_true", help="Print each finding as it fires")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit summary as JSON (for API callers)")
    args = ap.parse_args()

    book_dir = resolve_content(args.slug)
    if not book_dir.exists():
        print(f"ERROR: book directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    stages_root = book_dir / "_stages"
    if not stages_root.exists():
        print(f"ERROR: _stages directory not found for {args.slug}", file=sys.stderr)
        sys.exit(1)

    chapters = (
        [args.chapter] if args.chapter
        else sorted(d.name for d in stages_root.iterdir() if d.is_dir())
    )

    all_results = []
    for chapter in chapters:
        if args.verbose or not args.as_json:
            print(f"\nAudit: {chapter}")
        result = audit_chapter(
            args.slug, chapter,
            use_llm=not args.no_llm,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        if result:
            all_results.append(result)
            if not args.as_json:
                s = result.get("summary", {})
                gap = " ⚠ PIPELINE_GAP" if result.get("pipeline_gap") else ""
                print(f"  → {s.get('suppress', 0)} suppress, {s.get('consolidate', 0)} consolidate{gap}")

    if args.as_json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    elif not args.dry_run:
        out_dir = book_dir / "_system" / AUDIT_DIR_NAME
        print(f"\nFindings written to {out_dir.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
