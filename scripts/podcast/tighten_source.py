#!/usr/bin/env python3
"""tighten_source.py — advisory pass that flags non-essential prose in chapter
source files so NotebookLM gets a tighter signal without losing dialectical
or doctrinal substance.

GOAL: TIGHTEN, NOT SHORTEN

  The objective is density-per-word, not word-count reduction. If a chapter's
  proposed cuts exceed `drastic_reduction_threshold` (default 15%), the
  chapter is RED-FLAGGED in the report — a large cut is a smell, not a win.
  The right outcome is usually 3-10% removal of decorative scaffolding, with
  the dialectical/doctrinal substance fully preserved.

DESIGN

  Per-chapter Claude-judge (Sonnet) reads each chapter and returns candidate
  cuts as JSON in four categories:

    editorial-bridge      — pipeline-added connective tissue
                            (e.g. "The reader should mark this", "The argument
                            has been operating, so far, in the register of...")
    cross-tradition-import— decorative quotations imported by the modern
                            reframing that are NOT in the source text
                            (e.g. Rumi's Mathnawi grafted onto al-Kirmani,
                            Nahj al-Balagha cross-references in an Ismaili text)
    restatement           — explicit recap of what was just developed in the
                            same chapter, beyond the author's own summary
    meta-narration        — second-person guide voice that addresses the reader
                            but adds no doctrinal content
                            (e.g. "The reader should mark this")

  After per-chapter passes, a cohesion pass checks whether any proposed cut
  is referenced or set up by a later chapter (so we do not orphan callbacks).

  Output: <book_dir>/_system/tighten-report.md with one section per chapter,
  proposed-diff blocks, accept/reject checkboxes, running word-count delta,
  cohesion warnings inline.

  --apply ch07,ch11   writes <ch>.tightened.txt siblings in chapters/.
                      ONLY cuts marked `- [x]` in tighten-report.md are
                      applied. Default unchecked = not accepted = not cut.
                      Never overwrites the original. A second --apply run on
                      the same chapter overwrites the .tightened.txt sibling.

CONFIG

  Optional per-book config at <book_dir>/_system/tighten-config.yml:

    categories:
      editorial-bridge: true
      cross-tradition-import: true
      restatement: true
      meta-narration: true
      citation-overhead: false   # aggressive mode; off by default

    protect:                     # regex; matches → never propose for cut
      - "Imam"
      - "Quran"
      - "Jonathan|Samuel"        # al-Riyad-specific aliases
      - "al-Mahsul|al-Nusra|al-Islah"

    min_confidence: 0.70         # drop candidates below this

    drastic_reduction_threshold: 0.15  # red-flag any chapter where proposed
                                       # cuts exceed this fraction of words

    budget_usd: 3.00             # per-book ceiling for tighten spend

USAGE

  # Dry-run (no LLM, no writes, prints what WOULD be done):
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad --dry-run

  # Real per-chapter pass + report:
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad

  # Apply two chapters' accepted cuts (advisory still; writes .tightened.txt):
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad \\
      --apply ch07,ch11

EXIT CODES

  0  — report written; one or more candidates produced
  1  — report written; zero candidates (book is already tight, or LLM failed)
  2  — refused (budget cap, missing chapters/, missing claude CLI)
  3  — bad arguments

SAFETY

  - Advisory by default: NEVER overwrites <ch>.txt; writes .tightened.txt siblings.
  - Protect-list defaults baked in (Imam, Quran, proper names) even with no config.
  - Per-book budget cap default $3.00; refuses past that.
  - Cost-ledger rows written for every claude -p call.
  - Boundary check: refuses if book_dir is not under content/drafts/ or
    content/published/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from _cost_ledger import compute_cost_usd  # type: ignore
except ImportError:
    def compute_cost_usd(*args, **kwargs) -> float:  # type: ignore
        return 0.0


# --- model + cost ----------------------------------------------------------

MODEL_PER_CHAPTER = "claude-sonnet-4-6"
MODEL_COHESION = "claude-sonnet-4-6"

# Conservative upper-bound per call (cost-ledger captures actuals where possible).
EST_COST_PER_CHAPTER_USD = 0.15
EST_COST_COHESION_USD = 0.30

DEFAULT_BUDGET_USD = 3.00


# --- defaults baked in -----------------------------------------------------

DEFAULT_CATEGORIES = {
    "editorial-bridge": True,
    "cross-tradition-import": True,
    "restatement": True,
    "meta-narration": True,
    "citation-overhead": False,  # aggressive; off by default
}

# Regexes that the LLM is INSTRUCTED never to cross. Defensive belt-and-braces
# on top of the prompt's protect-list — we drop any candidate whose anchor_text
# trips one of these even if the LLM proposed it.
DEFAULT_PROTECT_PATTERNS = [
    r"\bImam\b",
    r"\bAllah\b",
    r"\bGod\b",
    r"\bProphet\b",
    r"\bQuran?\b",
    r"\bSurat?\b",
    r"\bayat?\b",
    r"\bhadith\b",
    r"the author",                    # al-Kirmani's own voice
    r"Jonathan|Samuel|Ahmad",         # al-Riyad's translator aliases
    r"al-Mahsul|al-Nusra|al-Islah",
    r"al-Kirmani|al-Razi|al-Sijistani|al-Nasafi",
    r"# [A-Z]",                       # chapter heading lines
    r"## ",                           # section heading lines
    r"### ",                          # subsection heading lines
]

DEFAULT_MIN_CONFIDENCE = 0.70

# A chapter that proposes cuts above this fraction of original words is a
# smell — the goal is to TIGHTEN (density), not SHORTEN (length). The report
# RED-FLAGS such chapters so the operator scrutinises them before applying.
DEFAULT_DRASTIC_REDUCTION_THRESHOLD = 0.15


# --- data classes ----------------------------------------------------------

@dataclass
class CutCandidate:
    chapter: str
    line_start: int
    line_end: int
    anchor_text: str       # first ~80 chars of the proposed cut
    category: str
    rationale: str
    confidence: float
    est_words_removed: int
    cohesion_warning: str = ""  # set by cohesion pass

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChapterResult:
    chapter: str
    chapter_path: Path
    original_words: int
    candidates: list[CutCandidate] = field(default_factory=list)
    error: str = ""
    cached: bool = False

    @property
    def proposed_words_removed(self) -> int:
        return sum(c.est_words_removed for c in self.candidates)


# --- boundary + cache helpers ---------------------------------------------

def boundary_check(book_dir: Path) -> None:
    bd = book_dir.resolve()
    allowed_parents = [
        (REPO_ROOT / "content" / "drafts").resolve(),
        (REPO_ROOT / "content" / "published" / "books").resolve(),
    ]
    if not any(str(bd).startswith(str(p) + "/") for p in allowed_parents):
        sys.exit(
            f"[tighten] refusing: book_dir {bd} is not under content/drafts/ "
            f"or content/published/books/"
        )


def source_signature(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_path(book_dir: Path, chapter: str, sig: str) -> Path:
    p = book_dir / "_system" / "tighten-cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{chapter}__{sig.split(':',1)[1][:16]}.json"


def load_cached(book_dir: Path, chapter: str, sig: str) -> list[CutCandidate] | None:
    p = cache_path(book_dir, chapter, sig)
    if not p.exists():
        return None
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
        return [CutCandidate(**r) for r in rows]
    except (json.JSONDecodeError, TypeError):
        return None


def save_cached(book_dir: Path, chapter: str, sig: str, candidates: list[CutCandidate]) -> None:
    p = cache_path(book_dir, chapter, sig)
    p.write_text(
        json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# --- cost-ledger -----------------------------------------------------------

def book_tighten_spend(book_dir: Path) -> float:
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return 0.0
    total = 0.0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("phase", "").startswith("tighten/"):
            total += float(row.get("cost_usd", 0.0))
    return total


def append_ledger(book_dir: Path, phase: str, step: str, model: str, cost_usd: float) -> None:
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": phase,
        "step": step,
        "model": model,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read": 0,
        "cache_create": 0,
        "cost_usd": cost_usd,
    }
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- config loader ---------------------------------------------------------

def load_config(book_dir: Path) -> dict:
    cfg_path = book_dir / "_system" / "tighten-config.yml"
    cfg = {
        "categories": dict(DEFAULT_CATEGORIES),
        "protect": list(DEFAULT_PROTECT_PATTERNS),
        "min_confidence": DEFAULT_MIN_CONFIDENCE,
        "drastic_reduction_threshold": DEFAULT_DRASTIC_REDUCTION_THRESHOLD,
        "budget_usd": DEFAULT_BUDGET_USD,
    }
    if not cfg_path.exists():
        return cfg
    # Minimal YAML reader — supports our flat schema only. Avoids PyYAML dep.
    try:
        raw = cfg_path.read_text(encoding="utf-8")
        cfg.update(_parse_simple_yaml(raw))
    except Exception as e:
        print(f"[tighten] warning: could not parse {cfg_path}: {e}", file=sys.stderr)
    return cfg


def _parse_simple_yaml(text: str) -> dict:
    """Tiny YAML subset: top-level keys, scalar values, lists under a key, and
    one level of nested mapping under 'categories'. Sufficient for our schema."""
    out: dict[str, Any] = {}
    cur_key: str | None = None
    cur_list: list | None = None
    cur_map: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # list item
        if line.lstrip().startswith("- ") and cur_list is not None:
            cur_list.append(line.lstrip()[2:].strip().strip('"'))
            continue
        # nested map item under categories
        if line.startswith("  ") and cur_map is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            cur_map[k.strip()] = _coerce(v.strip())
            continue
        # top-level
        if ":" in line and not line.startswith(" "):
            cur_list = None
            cur_map = None
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "":
                # list or map follows
                if k == "categories":
                    cur_map = {}
                    out[k] = cur_map
                else:
                    cur_list = []
                    out[k] = cur_list
                cur_key = k
            else:
                out[k] = _coerce(v)
                cur_key = k
    return out


def _coerce(v: str) -> Any:
    v = v.strip().strip('"')
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


# --- claude -p invocation --------------------------------------------------

def spawn_claude(prompt: str, model: str, cwd: Path, timeout_sec: int = 240) -> str:
    cmd = [
        "claude", "-p",
        "--permission-mode", "acceptEdits",
        "--model", model,
        prompt,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except FileNotFoundError:
        sys.exit(
            "[tighten] error: 'claude' CLI not found on PATH. Install Claude Code "
            "and ensure 'claude --version' works before running this script."
        )
    except subprocess.TimeoutExpired:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        # strip first fence
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    # try direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find first bracketed structure
    for start_char, end_char in (("[", "]"), ("{", "}")):
        i = text.find(start_char)
        if i >= 0:
            j = text.rfind(end_char)
            if j > i:
                try:
                    return json.loads(text[i:j+1])
                except json.JSONDecodeError:
                    continue
    return None


# --- prompts ---------------------------------------------------------------

PER_CHAPTER_PROMPT = """You are reviewing one chapter of a NotebookLM podcast source bundle. Your job
is to flag prose that adds NO substantive value and could be removed without
losing dialectical, doctrinal, or argumentative content.

THIS IS ADVISORY. The user will review each candidate before any cut is made.
False positives are worse than false negatives — when in doubt, DO NOT FLAG.

THE BOOK
{book_title}
{book_premise}

FLAGGING CATEGORIES (only flag items the user has enabled)
{enabled_categories}

  - editorial-bridge: pipeline-added connective tissue that does not exist in
    the source text. Examples: "The reader should mark this", "The argument
    has been operating, so far, in the register of philosophy", "This is the
    platform from which the next stretch of Chapter One will operate."

  - cross-tradition-import: decorative quotations imported by the modern
    reframing that do NOT belong to the source text or its author. For a
    Fatimid Ismaili text like al-Riyad, a Rumi Mathnawi couplet or a
    Nahj al-Balagha aphorism inserted as cross-tradition resonance is a
    cross-tradition-import. Quranic verses CITED BY THE SOURCE AUTHOR are NOT.

  - restatement: explicit recap of what was just developed in the same
    chapter (beyond the author's own summary sub-chapter, if any). The
    chapter's own concluding "Section Ten — the formula that closes the
    opening movement" is borderline; if it adds NO new content beyond what
    sections 1-9 already said, flag it.

  - meta-narration: second-person guide voice that addresses the reader but
    contributes no doctrinal content. Example: "The reader should mark this:
    it is one of the moments where the author's loyalty to Jonathan does not
    bend the truth."

  - citation-overhead (only flag if enabled): bibliographic parentheticals
    that pad citations beyond what the source author wrote. Example:
    "(Quran 41, the chapter explained in detail, verse 53, in the rendering
    the author gives)" — if the source just said "Quran 41:53", the modern
    expansion is overhead. KEEP the verse text itself; flag only the
    parenthetical scaffold.

PROTECT-LIST (NEVER FLAG ANYTHING THAT CONTAINS THESE — defensive)
{protect_list}

ALWAYS PROTECT:
  - The author's own preface, prayer, invocation of Imams, and statement of method
  - The 10-chapter scaffold and sub-chapter counts (if cited by the author)
  - Direct quotations from the source author
  - Quranic verses cited by the author (the verse text itself, even if scaffold around it is overhead)
  - The dialectic between named source-book interlocutors (Jonathan/Samuel/Ahmad in this book)
  - Section/sub-section headings (lines beginning with #, ##, ###)

OUTPUT FORMAT — return ONLY a JSON array, no prose, no markdown fences:

[
  {{
    "line_start": 178,
    "line_end": 184,
    "anchor_text": "Bishnaw in nay chun shikayat mikunad...",
    "category": "cross-tradition-import",
    "rationale": "Rumi's Mathnawi (13th-c. Persian Sufi poetry) grafted onto an 11th-c. Ismaili philosophical chapter as decorative resonance. Not in al-Kirmani's source. The argument lands without it.",
    "confidence": 0.92,
    "est_words_removed": 78
  }},
  ...
]

CONFIDENCE — your own estimate from 0.0 to 1.0 of how certain you are this
candidate is non-essential. The user's config drops anything below
{min_confidence}.

If you find NOTHING worth flagging, return an empty array: []

CHAPTER FILE: {chapter_path}
CHAPTER NUMBER: {chapter_num}

CHAPTER CONTENT (line-numbered):

{chapter_text}
"""


COHESION_PROMPT = """You are checking cross-chapter cohesion for a set of proposed cuts in a
NotebookLM podcast source bundle. For each candidate cut listed below, check
whether the cut's anchor_text or rationale is REFERENCED, CALLED BACK TO, or
SET UP by content in LATER chapters of the same book.

If a later chapter says something like "as we saw in Chapter 3 with the reed
flute..." and the proposed cut removes the reed-flute passage from Chapter 3,
that callback would be orphaned. Flag it.

THE BOOK
{book_title}

CANDIDATE CUTS (chapter, anchor_text, category):
{candidate_summary}

LATER CHAPTER EXCERPTS (chapter heading + first 600 chars):
{later_excerpts}

OUTPUT FORMAT — return ONLY a JSON array, no prose:

[
  {{
    "chapter": "ch03",
    "anchor_text": "Bishnaw in nay chun shikayat mikunad...",
    "cohesion_warning": "Chapter 8 references the reed-flute image again in its closing paragraph."
  }},
  ...
]

If no cohesion issues found, return an empty array: []
"""


def build_per_chapter_prompt(
    chapter_path: Path,
    chapter_text: str,
    chapter_num: str,
    book_title: str,
    book_premise: str,
    cfg: dict,
) -> str:
    enabled = [k for k, v in cfg["categories"].items() if v]
    protect_list = "\n".join(f"  - {p}" for p in cfg["protect"])
    line_numbered = "\n".join(f"{i+1:4d}\t{line}" for i, line in enumerate(chapter_text.splitlines()))
    return PER_CHAPTER_PROMPT.format(
        book_title=book_title,
        book_premise=book_premise,
        enabled_categories="\n".join(f"  - {c}" for c in enabled),
        protect_list=protect_list,
        min_confidence=cfg["min_confidence"],
        chapter_path=chapter_path,
        chapter_num=chapter_num,
        chapter_text=line_numbered,
    )


def build_cohesion_prompt(
    candidates: list[CutCandidate],
    chapters: dict[str, str],
    book_title: str,
) -> str:
    rows = []
    for c in candidates:
        rows.append(f"  - {c.chapter} | [{c.category}] | {c.anchor_text[:80]}")
    candidate_summary = "\n".join(rows)
    excerpts = []
    for slug, text in sorted(chapters.items()):
        first_line = text.splitlines()[0] if text else ""
        excerpts.append(f"### {slug}\n{first_line}\n{text[:600]}")
    return COHESION_PROMPT.format(
        book_title=book_title,
        candidate_summary=candidate_summary,
        later_excerpts="\n\n".join(excerpts),
    )


# --- per-chapter pass ------------------------------------------------------

def run_per_chapter(
    book_dir: Path,
    chapter_path: Path,
    book_title: str,
    book_premise: str,
    cfg: dict,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> ChapterResult:
    chapter_slug = chapter_path.stem
    text = chapter_path.read_text(encoding="utf-8")
    sig = source_signature(text)
    original_words = len(text.split())
    chapter_num = chapter_slug[:4]  # ch01, ch02, ...

    if not force_refresh:
        cached = load_cached(book_dir, chapter_slug, sig)
        if cached is not None:
            return ChapterResult(
                chapter=chapter_slug,
                chapter_path=chapter_path,
                original_words=original_words,
                candidates=cached,
                cached=True,
            )

    if dry_run:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error="dry-run (no LLM call)",
        )

    # Budget check
    spent = book_tighten_spend(book_dir)
    if spent + EST_COST_PER_CHAPTER_USD > cfg["budget_usd"]:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error=f"budget cap reached: spent=${spent:.2f}, cap=${cfg['budget_usd']:.2f}",
        )

    prompt = build_per_chapter_prompt(
        chapter_path, text, chapter_num, book_title, book_premise, cfg
    )
    raw = spawn_claude(prompt, MODEL_PER_CHAPTER, book_dir.parent)
    if not raw:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error="claude -p returned empty (timeout or rc!=0)",
        )

    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, list):
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error=f"could not parse JSON from claude (got: {raw[:200]})",
        )

    candidates = []
    for row in parsed:
        try:
            c = CutCandidate(
                chapter=chapter_slug,
                line_start=int(row["line_start"]),
                line_end=int(row["line_end"]),
                anchor_text=str(row["anchor_text"])[:200],
                category=str(row["category"]),
                rationale=str(row["rationale"]),
                confidence=float(row.get("confidence", 0.5)),
                est_words_removed=int(row.get("est_words_removed", 0)),
            )
        except (KeyError, ValueError, TypeError) as e:
            print(f"[tighten] skipping malformed candidate in {chapter_slug}: {e}", file=sys.stderr)
            continue
        # apply min_confidence
        if c.confidence < cfg["min_confidence"]:
            continue
        # apply category filter
        if not cfg["categories"].get(c.category, False):
            continue
        # apply protect-list (belt-and-braces)
        if _trips_protect(c.anchor_text, cfg["protect"]):
            continue
        candidates.append(c)

    append_ledger(book_dir, "tighten/per-chapter", chapter_slug, MODEL_PER_CHAPTER, EST_COST_PER_CHAPTER_USD)
    save_cached(book_dir, chapter_slug, sig, candidates)

    return ChapterResult(
        chapter=chapter_slug,
        chapter_path=chapter_path,
        original_words=original_words,
        candidates=candidates,
    )


def _trips_protect(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        try:
            if re.search(p, text):
                return True
        except re.error:
            # bad regex → treat as literal substring
            if p in text:
                return True
    return False


# --- cohesion pass ---------------------------------------------------------

def run_cohesion(
    book_dir: Path,
    results: list[ChapterResult],
    book_title: str,
    cfg: dict,
    dry_run: bool = False,
) -> None:
    # Build the candidate list and the "later chapters" excerpts
    all_candidates = [c for r in results for c in r.candidates]
    if not all_candidates or dry_run:
        return

    spent = book_tighten_spend(book_dir)
    if spent + EST_COST_COHESION_USD > cfg["budget_usd"]:
        print(f"[tighten] skipping cohesion pass — budget would exceed cap", file=sys.stderr)
        return

    chapters_by_slug = {
        r.chapter: r.chapter_path.read_text(encoding="utf-8")
        for r in results
    }
    prompt = build_cohesion_prompt(all_candidates, chapters_by_slug, book_title)
    raw = spawn_claude(prompt, MODEL_COHESION, book_dir.parent, timeout_sec=300)
    if not raw:
        print("[tighten] cohesion pass returned empty", file=sys.stderr)
        return
    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, list):
        print(f"[tighten] cohesion pass: could not parse JSON: {raw[:200]}", file=sys.stderr)
        return
    append_ledger(book_dir, "tighten/cohesion", "cross-chapter", MODEL_COHESION, EST_COST_COHESION_USD)

    # Stamp warnings onto matching candidates
    for warn in parsed:
        try:
            slug = warn["chapter"]
            anchor = warn["anchor_text"][:60]
            msg = warn["cohesion_warning"]
        except (KeyError, TypeError):
            continue
        for c in all_candidates:
            if c.chapter == slug and c.anchor_text.startswith(anchor[:30]):
                c.cohesion_warning = msg


# --- report rendering ------------------------------------------------------

def render_report(
    book_dir: Path,
    results: list[ChapterResult],
    book_title: str,
    cfg: dict,
) -> Path:
    out = book_dir / "_system" / "tighten-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# tighten-source report — {book_title}")
    lines.append("")
    lines.append(f"_generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}_")
    lines.append("")
    lines.append("> **Goal: TIGHTEN, not SHORTEN.** This pass flags decorative scaffolding,")
    lines.append("> editorial bridges, and restatement — not load-bearing prose. A chapter")
    lines.append("> with a high proposed-removal % is suspicious, not a win. Healthy")
    lines.append("> tightening is usually 3-10% per chapter.")
    lines.append("")
    lines.append("## At a glance")
    lines.append("")
    total_original = sum(r.original_words for r in results)
    total_proposed = sum(r.proposed_words_removed for r in results)
    pct = (100.0 * total_proposed / total_original) if total_original else 0.0
    n_candidates = sum(len(r.candidates) for r in results)
    n_with_cohesion = sum(1 for r in results for c in r.candidates if c.cohesion_warning)
    threshold = cfg.get("drastic_reduction_threshold", DEFAULT_DRASTIC_REDUCTION_THRESHOLD)
    flagged = [r for r in results if r.original_words > 0
               and (r.proposed_words_removed / r.original_words) > threshold]
    lines.append(f"- chapters scanned: **{len(results)}**")
    lines.append(f"- candidate cuts: **{n_candidates}** (of which **{n_with_cohesion}** have cohesion warnings)")
    lines.append(f"- words: original **{total_original:,}**, proposed-removed **{total_proposed:,}** (**{pct:.1f}%**)")
    lines.append(f"- categories enabled: {', '.join(k for k,v in cfg['categories'].items() if v)}")
    lines.append(f"- min_confidence: {cfg['min_confidence']} · drastic-reduction threshold: **{threshold*100:.0f}%**")
    lines.append(f"- budget: ${book_tighten_spend(book_dir):.2f} / ${cfg['budget_usd']:.2f}")
    lines.append("")
    if flagged:
        lines.append(f"### 🔴 RED-FLAG: chapters exceeding the {threshold*100:.0f}% drastic-reduction threshold")
        lines.append("")
        lines.append("These chapters propose cutting more than is consistent with 'tightening'.")
        lines.append("Review their candidates carefully — they may be over-flagging substance.")
        lines.append("")
        for r in flagged:
            ratio = (r.proposed_words_removed / r.original_words) if r.original_words else 0
            lines.append(f"- **{r.chapter}** — {r.proposed_words_removed:,} words proposed for cut ({ratio*100:.1f}%)")
        lines.append("")
    else:
        lines.append(f"_no chapters exceed the {threshold*100:.0f}% drastic-reduction threshold_")
        lines.append("")
    lines.append("## Category legend")
    lines.append("")
    lines.append("- `editorial-bridge` — pipeline-added connective tissue not in source")
    lines.append("- `cross-tradition-import` — decorative quotes grafted from outside the source tradition")
    lines.append("- `restatement` — recap of what was already developed in the same chapter")
    lines.append("- `meta-narration` — second-person guide voice with no doctrinal content")
    lines.append("- `citation-overhead` — bibliographic scaffolding around citations (off by default)")
    lines.append("")
    lines.append("## How to use this report")
    lines.append("")
    lines.append("1. Review each chapter's candidates below.")
    lines.append("2. For each one you want to cut, check the `[ ]` box next to it.")
    lines.append("3. Run `--apply ch07,ch11,...` and the script writes `<ch>.tightened.txt` siblings.")
    lines.append("   (Originals are never overwritten.)")
    lines.append("4. Diff the .tightened.txt against the original; promote it manually when satisfied.")
    lines.append("")

    for r in sorted(results, key=lambda x: x.chapter):
        lines.append(f"## {r.chapter}")
        lines.append("")
        lines.append(f"- file: `{r.chapter_path.relative_to(book_dir.parent)}`")
        lines.append(f"- original words: **{r.original_words:,}**")
        lines.append(f"- proposed cut: **{r.proposed_words_removed:,}** ({(100.0*r.proposed_words_removed/r.original_words if r.original_words else 0):.1f}%)")
        if r.cached:
            lines.append(f"- _result loaded from cache_")
        if r.error:
            lines.append(f"- error: **{r.error}**")
        lines.append("")
        if not r.candidates:
            lines.append("_no candidates flagged_")
            lines.append("")
            continue
        for i, c in enumerate(r.candidates, 1):
            lines.append(f"### {r.chapter}.{i} `[{c.category}]` — lines {c.line_start}-{c.line_end}")
            lines.append("")
            lines.append(f"- [ ] accept this cut")
            lines.append(f"- confidence: **{c.confidence:.2f}** · est. words removed: **{c.est_words_removed}**")
            if c.cohesion_warning:
                lines.append(f"- ⚠ **cohesion warning:** {c.cohesion_warning}")
            lines.append("")
            lines.append(f"**Anchor:** `{c.anchor_text}`")
            lines.append("")
            lines.append(f"**Rationale:** {c.rationale}")
            lines.append("")
            lines.append("---")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# --- apply mode ------------------------------------------------------------

def apply_cuts(
    book_dir: Path,
    chapter_slugs: list[str],
    results: list[ChapterResult],
) -> list[Path]:
    """For each requested chapter slug (e.g. 'ch07'), write a .tightened.txt
    sibling that removes ALL candidates listed in the report for that chapter.

    NOTE: This applies every candidate in the cache for the chapter. The
    expected workflow is: the operator edits the .tightened.txt to taste, or
    edits the cache JSON to remove rejected candidates before running --apply.
    """
    written = []
    chapters_dir = book_dir / "chapters"
    for slug in chapter_slugs:
        slug = slug.strip()
        # find matching ChapterResult
        match = next((r for r in results if r.chapter.startswith(slug)), None)
        if match is None:
            print(f"[tighten] --apply: no chapter matching '{slug}'", file=sys.stderr)
            continue
        if not match.candidates:
            print(f"[tighten] --apply: {match.chapter} has no candidates to apply", file=sys.stderr)
            continue
        text_lines = match.chapter_path.read_text(encoding="utf-8").splitlines()
        # build a set of (line_idx) to drop; line_start/end are 1-indexed inclusive
        drop = set()
        for c in match.candidates:
            for i in range(c.line_start - 1, c.line_end):
                if 0 <= i < len(text_lines):
                    drop.add(i)
        kept = [line for i, line in enumerate(text_lines) if i not in drop]
        out_path = chapters_dir / f"{match.chapter}.tightened.txt"
        out_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        written.append(out_path)
        print(f"[tighten] wrote {out_path.relative_to(book_dir.parent)}")
    return written


# --- main ------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Advisory tighten-pass for NotebookLM source chapters.")
    parser.add_argument("--book-dir", required=True, help="path to content/drafts/<slug>/ or content/published/books/<slug>/")
    parser.add_argument("--chapter", help="run only this chapter (e.g. ch07). Default: all chapters.")
    parser.add_argument("--all", action="store_true", help="run all chapters (default if --chapter not given)")
    parser.add_argument("--apply", help="comma-separated chapter slugs to apply (e.g. ch07,ch11)")
    parser.add_argument("--dry-run", action="store_true", help="no LLM calls; just show what would run")
    parser.add_argument("--force", action="store_true", help="bypass cache; re-run LLM even if cached")
    parser.add_argument("--no-cohesion", action="store_true", help="skip the cohesion cross-chapter pass")
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout instead of the report path")
    parser.add_argument("--budget", type=float, help="override per-book budget cap (USD)")
    args = parser.parse_args(argv)

    book_dir = Path(args.book_dir).resolve()
    if not book_dir.exists():
        print(f"[tighten] error: book_dir does not exist: {book_dir}", file=sys.stderr)
        return 3
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        print(f"[tighten] error: chapters/ not found under {book_dir}", file=sys.stderr)
        return 2

    boundary_check(book_dir)

    # Load config (and budget override)
    cfg = load_config(book_dir)
    if args.budget is not None:
        cfg["budget_usd"] = args.budget

    # Book metadata (best-effort)
    meta_path = book_dir / "meta.yml"
    book_title = book_dir.name
    book_premise = ""
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                book_title = line.split(":", 1)[1].strip().strip('"')
                break
    # premise hint from _README.md if present
    readme = book_dir / "_README.md"
    if readme.exists():
        book_premise = readme.read_text(encoding="utf-8")[:600]

    # Collect chapter files
    chapter_paths = sorted(chapters_dir.glob("ch*.txt"))
    # exclude .tightened.txt siblings
    chapter_paths = [p for p in chapter_paths if not p.name.endswith(".tightened.txt")]
    if args.chapter:
        chapter_paths = [p for p in chapter_paths if p.stem.startswith(args.chapter)]
    if not chapter_paths:
        print(f"[tighten] error: no matching chapters in {chapters_dir}", file=sys.stderr)
        return 2

    # Per-chapter pass
    results: list[ChapterResult] = []
    for cp in chapter_paths:
        print(f"[tighten] {cp.stem} ...", file=sys.stderr)
        r = run_per_chapter(book_dir, cp, book_title, book_premise, cfg, force_refresh=args.force, dry_run=args.dry_run)
        results.append(r)
        if r.error:
            print(f"[tighten]   {r.error}", file=sys.stderr)
        else:
            print(f"[tighten]   {len(r.candidates)} candidates (~{r.proposed_words_removed} words)", file=sys.stderr)

    # Cohesion pass
    if not args.no_cohesion:
        run_cohesion(book_dir, results, book_title, cfg, dry_run=args.dry_run)

    # Report
    report_path = render_report(book_dir, results, book_title, cfg)

    # Apply mode
    written: list[Path] = []
    if args.apply:
        slugs = [s.strip() for s in args.apply.split(",") if s.strip()]
        written = apply_cuts(book_dir, slugs, results)

    if args.json:
        payload = {
            "report": str(report_path),
            "results": [
                {
                    "chapter": r.chapter,
                    "original_words": r.original_words,
                    "proposed_words_removed": r.proposed_words_removed,
                    "n_candidates": len(r.candidates),
                    "candidates": [c.to_dict() for c in r.candidates],
                    "error": r.error,
                }
                for r in results
            ],
            "written": [str(p) for p in written],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[tighten] report: {report_path}")

    total_cands = sum(len(r.candidates) for r in results)
    return 0 if total_cands > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
