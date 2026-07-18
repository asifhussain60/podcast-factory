"""_tighten_helpers.py — Constants, data classes, helpers, prompts for tighten_source.py.

Split from tighten_source.py (DR-005 — files must stay under 600 lines).
Re-exported via tighten_source.py so all callers remain unaffected.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from _cost_ledger import compute_cost_usd  # type: ignore
except ImportError:

    def compute_cost_usd(*args, **kwargs) -> float:  # type: ignore
        return 0.0


from _rules import BUCKETS  # bucket registry is the single source of truth

# --- model + cost ----------------------------------------------------------

MODEL_PER_CHAPTER = "claude-sonnet-4-6"
MODEL_COHESION = "claude-sonnet-4-6"

EST_COST_PER_CHAPTER_USD = 0.15
EST_COST_COHESION_USD = 0.30

DEFAULT_BUDGET_USD = 3.00


# --- defaults baked in -----------------------------------------------------

DEFAULT_CATEGORIES = {
    "editorial-bridge": True,
    "cross-tradition-import": True,
    "restatement": True,
    "meta-narration": True,
    "citation-overhead": False,
}

DEFAULT_PROTECT_PATTERNS = [
    r"\bImam\b",
    r"\bAllah\b",
    r"\bGod\b",
    r"\bProphet\b",
    r"\bQuran?\b",
    r"\bSurat?\b",
    r"\bayat?\b",
    r"\bhadith\b",
    r"the author",
    r"Jonathan|Samuel|Ahmad",
    r"al-Mahsul|al-Nusra|al-Islah",
    r"al-Kirmani|al-Razi|al-Sijistani|al-Nasafi",
    r"# [A-Z]",
    r"## ",
    r"### ",
]

DEFAULT_MIN_CONFIDENCE = 0.70
DEFAULT_DRASTIC_REDUCTION_THRESHOLD = 0.15


# --- data classes ----------------------------------------------------------


@dataclass
class CutCandidate:
    chapter: str
    line_start: int
    line_end: int
    anchor_text: str
    category: str
    rationale: str
    confidence: float
    est_words_removed: int
    cohesion_warning: str = ""

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
    allowed_parents = [(REPO_ROOT / "content" / bucket).resolve() for bucket in BUCKETS] + [
        # Legacy pre-2026-06-04 layout, kept for back-compat (mirrors _paths fallback).
        (REPO_ROOT / "content" / "drafts").resolve(),
        (REPO_ROOT / "content" / "published" / "books").resolve(),
    ]
    if not any(str(bd).startswith(str(p) + "/") for p in allowed_parents):
        sys.exit(
            f"[tighten] refusing: book_dir {bd} is not under a content bucket "
            f"({', '.join('content/' + b + '/' for b in BUCKETS)}) "
            f"or the legacy content/drafts/ / content/published/books/ trees"
        )


def source_signature(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_path(book_dir: Path, chapter: str, sig: str) -> Path:
    p = book_dir / "_system" / "tighten-cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{chapter}__{sig.split(':', 1)[1][:16]}.json"


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
    try:
        raw = cfg_path.read_text(encoding="utf-8")
        cfg.update(_parse_simple_yaml(raw))
    except Exception as e:
        print(f"[tighten] warning: could not parse {cfg_path}: {e}", file=sys.stderr)
    return cfg


def _parse_simple_yaml(text: str) -> dict:
    """Tiny YAML subset: top-level keys, scalar values, lists, one nested map level."""
    out: dict[str, Any] = {}
    cur_key: str | None = None
    cur_list: list | None = None
    cur_map: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and cur_list is not None:
            cur_list.append(line.lstrip()[2:].strip().strip('"'))
            continue
        if line.startswith("  ") and cur_map is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            cur_map[k.strip()] = _coerce(v.strip())
            continue
        if ":" in line and not line.startswith(" "):
            cur_list = None
            cur_map = None
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "":
                if k == "categories":
                    cur_map = {}
                    out[k] = cur_map
                else:
                    cur_list = []
                    out[k] = cur_list
                cur_key = k
            else:
                out[k] = _coerce(v)
                cur_key = k  # noqa: F841
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


# --- Anthropic SDK invocation ----------------------------------------------


def spawn_claude(prompt: str, model: str, cwd: Path, timeout_sec: int = 240) -> str:
    """Call the Anthropic SDK directly (replaces the former claude -p path, F38/DR-015)."""
    if _anthropic is None:
        sys.stderr.write("[tighten] error: 'anthropic' package not installed. Run: pip install anthropic\n")
        return ""
    try:
        client = _anthropic.Anthropic()
        msg = client.messages.create(
            model=model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
            timeout=float(timeout_sec),
        )
        return msg.content[0].text if msg.content else ""
    except _anthropic.APITimeoutError:
        return ""
    except Exception as exc:
        sys.stderr.write(f"[tighten] SDK call failed: {exc!r}\n")
        return ""


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start_char, end_char in (("[", "]"), ("{", "}")):
        i = text.find(start_char)
        if i >= 0:
            j = text.rfind(end_char)
            if j > i:
                try:
                    return json.loads(text[i : j + 1])
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
    line_numbered = "\n".join(f"{i + 1:4d}\t{line}" for i, line in enumerate(chapter_text.splitlines()))
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
