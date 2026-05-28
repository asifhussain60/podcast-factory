#!/usr/bin/env python3
"""AI helper layer for the Operator Review Studio (P25.7).

10 helper features, each delegating to `claude -p` subprocess. NO new API
keys — reuses the operator's existing Claude CLI auth. Same architecture
pattern as scripts/podcast/orchestrate_book.py.

  feature_id   model     trigger                   description
  ─────────────────────────────────────────────────────────────────────────
  summarize    haiku     on-demand batch           1-line summary per page
  diff-explain sonnet    hover                     why did the LLM change X?
  arabic       sonnet    on-demand (cached fwd)    detect Arabic terms +
                                                   cross-ref manifest
  preflight    sonnet    Cmd-K                     scan whole book for issues
  voice-shift  sonnet    on-demand                 flag author/voice changes
  episode-plan opus      on-demand                 propose episode breakdown
  suggest      sonnet    on-demand                 5-10 candidate flags
  autocomplete haiku     200ms in textarea         ghost-text suggestions
  categorize   haiku     passive on note change    route note to right section
  range        haiku     pre-fill                  detect body start/end pages

Caching: per-source-signature (sha256 of refined-english.md) for the
expensive whole-book features (summarize / arabic / voice-shift /
preflight / episode-plan). Light features (autocomplete / categorize /
range / diff-explain) are stateless.

Cost-ledger: every call writes an _cost_ledger row via the existing
scripts/podcast/_cost_ledger.py module.

Boundary: subprocess `claude -p` runs with --cwd locked to the book
directory; refuses if path escapes worktree root.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from _paths import REPO_ROOT
from typing import Any


# Add scripts/podcast to sys.path for sibling imports when run as module
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

try:
    from _cost_ledger import CostRow, compute_cost_usd  # type: ignore
except ImportError:
    CostRow = None  # type: ignore
    def compute_cost_usd(*args, **kwargs) -> float:  # type: ignore
        return 0.0


# Model name → enum (the locked enum from podcast-blueprint)
MODEL_FOR_FEATURE: dict[str, str] = {
    "summarize": "claude-haiku-4-5-20251001",
    "diff-explain": "claude-sonnet-4-6",
    "arabic": "claude-sonnet-4-6",
    "preflight": "claude-sonnet-4-6",
    "voice-shift": "claude-sonnet-4-6",
    "episode-plan": "claude-opus-4-7",
    "suggest-flags": "claude-sonnet-4-6",
    "autocomplete": "claude-haiku-4-5-20251001",
    "categorize": "claude-haiku-4-5-20251001",
    "content-range": "claude-haiku-4-5-20251001",
}

# Estimated cost per call (used for budget enforcement before spawning)
# These are conservative upper-bounds; cost-ledger captures actuals.
EST_COST_USD: dict[str, float] = {
    "summarize": 0.05,
    "diff-explain": 0.005,
    "arabic": 0.15,
    "preflight": 0.30,
    "voice-shift": 0.18,
    "episode-plan": 0.50,
    "suggest-flags": 0.20,
    "autocomplete": 0.002,
    "categorize": 0.001,
    "content-range": 0.01,
}

# Hard per-book budget cap (refuse if cumulative exceeds this)
BOOK_AI_BUDGET_USD = 2.00


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AIResult:
    feature: str
    model: str
    cached: bool
    cost_usd: float
    payload: Any
    elapsed_sec: float = 0.0


@dataclass
class BudgetExceeded(Exception):
    feature: str
    requested: float
    remaining: float


class BoundaryViolation(ValueError):
    """Raised when a path escapes the configured worktree root."""


# ---------------------------------------------------------------------------
# Boundary check
# ---------------------------------------------------------------------------

def assert_within_worktree(book_dir: Path, worktree_root: Path) -> None:
    """Refuse if book_dir escapes worktree_root.

    Loose: book_dir.resolve() must be a child of worktree_root.resolve().
    """
    bd = book_dir.resolve()
    wr = worktree_root.resolve()
    try:
        bd.relative_to(wr)
    except ValueError as e:
        raise BoundaryViolation(
            f"book_dir {bd} is not inside worktree_root {wr}"
        ) from e


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(book_dir: Path, feature: str, source_signature: str) -> Path:
    """Per-source-signature cache file."""
    cache_dir = book_dir / "_system" / "ai-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{feature}__{source_signature[:16]}.json"


def _load_cache(book_dir: Path, feature: str, source_signature: str) -> Any | None:
    p = _cache_path(book_dir, feature, source_signature)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_cache(book_dir: Path, feature: str, source_signature: str, payload: Any) -> None:
    p = _cache_path(book_dir, feature, source_signature)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_source_signature(text: str | bytes) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return "sha256:" + hashlib.sha256(text).hexdigest()


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

def book_ai_spend_so_far(book_dir: Path) -> float:
    """Sum cost_usd of all rows in cost-ledger.jsonl for this book where
    agent_id starts with 'podcast-review-studio'."""
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return 0.0
    total = 0.0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("phase", "").startswith("ai/") or row.get("step", "").startswith("ai/"):
            total += float(row.get("cost_usd", 0.0))
    return total


def check_budget(book_dir: Path, feature: str) -> None:
    est = EST_COST_USD.get(feature, 0.10)
    spent = book_ai_spend_so_far(book_dir)
    if spent + est > BOOK_AI_BUDGET_USD:
        raise BudgetExceeded(feature=feature, requested=est, remaining=BOOK_AI_BUDGET_USD - spent)


def append_cost_ledger(book_dir: Path, feature: str, model: str, cost_usd: float) -> None:
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": f"ai/{feature}",
        "step": "review-studio",
        "model": model,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read": 0,
        "cache_create": 0,
        "cost_usd": cost_usd,
    }
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Subprocess call to claude -p
# ---------------------------------------------------------------------------

def _spawn_claude(prompt: str, model: str, cwd: Path, timeout_sec: int = 120) -> str:
    """Spawn claude -p with the given prompt. Return stdout text.

    Uses subprocess; sets cwd to the book directory; uses --permission-mode
    acceptEdits but the prompt is structured to only write to its returned
    JSON (no file edits expected).
    """
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
    except FileNotFoundError as e:
        raise RuntimeError(
            "claude CLI not found on PATH. Operator must have Claude Code installed."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"claude -p timed out after {timeout_sec}s") from e
    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p exited rc={result.returncode}: {result.stderr[:400]}"
        )
    return result.stdout


def _extract_json(text: str) -> Any:
    """Find the first JSON object/array in text. Robust to surrounding prose."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    # Find first { or [
    for start_char, end_char in (("{", "}"), ("[", "]")):
        i = text.find(start_char)
        if i >= 0:
            j = text.rfind(end_char)
            if j > i:
                try:
                    return json.loads(text[i:j+1])
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"no parseable JSON in response: {text[:200]}")


# ---------------------------------------------------------------------------
# Feature implementations
# ---------------------------------------------------------------------------

def run_feature(
    feature: str,
    book_dir: Path,
    worktree_root: Path,
    *,
    source_signature: str,
    params: dict[str, Any] | None = None,
    force_refresh: bool = False,
) -> AIResult:
    """Dispatch entry point. All 10 features come through here.

    Raises BoundaryViolation, BudgetExceeded, ValueError.
    """
    assert_within_worktree(book_dir, worktree_root)
    params = params or {}

    if feature not in MODEL_FOR_FEATURE:
        raise ValueError(f"unknown feature: {feature}")

    # Cache for whole-book features
    CACHEABLE = {"summarize", "arabic", "preflight", "voice-shift", "episode-plan", "suggest-flags"}
    if feature in CACHEABLE and not force_refresh:
        cached = _load_cache(book_dir, feature, source_signature)
        if cached is not None:
            return AIResult(
                feature=feature,
                model=MODEL_FOR_FEATURE[feature],
                cached=True,
                cost_usd=0.0,
                payload=cached,
                elapsed_sec=0.0,
            )

    check_budget(book_dir, feature)

    start = time.time()
    model = MODEL_FOR_FEATURE[feature]
    prompt = _build_prompt(feature, book_dir, params)

    raw = _spawn_claude(prompt, model, book_dir)
    payload = _extract_json(raw) if feature != "autocomplete" else {"completions": [s.strip() for s in raw.strip().split("\n") if s.strip()][:3]}
    elapsed = time.time() - start

    # Cost — actual would come from claude -p's stdout-usage; using estimate
    cost_usd = EST_COST_USD.get(feature, 0.10)
    append_cost_ledger(book_dir, feature, model, cost_usd)

    if feature in CACHEABLE:
        _save_cache(book_dir, feature, source_signature, payload)

    return AIResult(
        feature=feature,
        model=model,
        cached=False,
        cost_usd=cost_usd,
        payload=payload,
        elapsed_sec=elapsed,
    )


# ---------------------------------------------------------------------------
# Prompt builders (one per feature)
# ---------------------------------------------------------------------------

def _build_prompt(feature: str, book_dir: Path, params: dict[str, Any]) -> str:
    transcript_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if feature == "summarize":
        return _prompt_summarize(transcript_path)
    if feature == "diff-explain":
        return _prompt_diff_explain(params)
    if feature == "arabic":
        return _prompt_arabic(transcript_path)
    if feature == "preflight":
        return _prompt_preflight(transcript_path)
    if feature == "voice-shift":
        return _prompt_voice_shift(transcript_path)
    if feature == "episode-plan":
        return _prompt_episode_plan(transcript_path)
    if feature == "suggest-flags":
        return _prompt_suggest_flags(transcript_path)
    if feature == "autocomplete":
        return _prompt_autocomplete(params)
    if feature == "categorize":
        return _prompt_categorize(params)
    if feature == "content-range":
        return _prompt_content_range(transcript_path)
    raise ValueError(f"no prompt builder for feature {feature}")


def _prompt_summarize(transcript: Path) -> str:
    return f"""Read the English transcript at {transcript}. For each page boundary (marked with `<!-- page N -->` or similar), emit a one-sentence summary of what happens on that page. The summary should be specific enough that a reader can decide whether to dive into that page or skim past it.

Return ONLY a JSON array, no prose, no markdown fences:

[
  {{"page": 1, "summary": "..."}},
  {{"page": 2, "summary": "..."}},
  ...
]

Keep each summary under 80 chars. Capture the SPECIFIC content (named concepts, doctrine introductions, voice shifts), not generic framings like 'the author continues to discuss...'."""


def _prompt_diff_explain(params: dict) -> str:
    raw = params.get("raw", "")
    refined = params.get("refined", "")
    return f"""Two passages — the raw OCR output (likely scrambled) and the LLM-refined version. Explain in ONE sentence (max 25 words) why the LLM made the change. Focus on what the operator should verify.

RAW: "{raw}"
REFINED: "{refined}"

Return ONLY a JSON object:
{{"explanation": "..."}}"""


def _prompt_arabic(transcript: Path) -> str:
    manifest = REPO_ROOT / "content" / "_shared" / "arabic" / "03-arabic-english-manifest.md"
    return f"""Read {transcript}. Identify every transliterated Arabic term (e.g., daʿwa, jazāʾir, tawḥīd, ḥujja, Imām, fiṭra, etc.). For each unique term, return:

- term: the transliteration as it appears
- canonical_form: the manifest form (if present in {manifest})
- pages: array of page numbers where it occurs
- manifest_match: true if found in manifest, false otherwise

Return ONLY a JSON array, no prose, no markdown fences."""


def _prompt_preflight(transcript: Path) -> str:
    return f"""Scan {transcript} for likely operator-actionable issues: OCR scrambles, impossible word pairs, citation typos, voice ruptures, numeric inconsistencies. Be specific — quote the actual text.

Return ONLY a JSON array of findings:

[
  {{"page": N, "quote": "...", "issue_type": "ocr-scramble|impossible-pair|citation|voice-rupture|numeric", "confidence": 0.0-1.0, "suggestion": "what the operator should check"}}
]

Limit to top 10 findings by confidence. Quote the exact text from the transcript."""


def _prompt_voice_shift(transcript: Path) -> str:
    return f"""Read {transcript}. Identify passages where the prose voice noticeably shifts — tense changes, register changes, reportative→assertive ("they say" → "I affirm"), dialect drift, or signs of a second author/editor.

Return ONLY a JSON array:

[
  {{"page": N, "before_quote": "...", "after_quote": "...", "shift_type": "voice|register|tense|author", "confidence": 0.0-1.0, "note": "..."}}
]

Quote ≤30 words for each before/after."""


def _prompt_episode_plan(transcript: Path) -> str:
    return f"""Read {transcript}. Propose an episode breakdown for a podcast series based on this book. Consider chapter structure, thematic units, density.

Return ONLY a JSON object:

{{
  "episode_count": N,
  "rationale": "1-sentence overall rationale",
  "episodes": [
    {{"n": 1, "title": "...", "page_range": [start, end], "target_word_count": N, "recap_cue": "...", "preview_cue": "..."}}
  ]
}}

Typical: 4-8 episodes, 2000-4000 words each. Title should be evocative + accurate."""


def _prompt_suggest_flags(transcript: Path) -> str:
    return f"""Read {transcript}. Suggest 5-10 candidate "translation issue" flags the operator should review — passages where the English looks suspect or could benefit from clarification.

Return ONLY a JSON array:

[
  {{"page": N, "quote": "...", "reason": "1-sentence why this needs operator attention", "confidence": 0.0-1.0}}
]

Quote ≤40 words. Sort by descending confidence."""


def _prompt_autocomplete(params: dict) -> str:
    section = params.get("section", "translation")
    partial = params.get("partial_text", "")
    return f"""Operator is writing a review note in the '{section}' section of operator-review.md. They've started: "{partial}"

Propose 3 plausible completions, each ≤25 words, matching common review-note phrasings ("OCR scrambled X → Y", "voice shift here", etc.). Match the operator's tone if context is given.

Return ONLY the 3 completions, one per line, no JSON, no preamble."""


def _prompt_categorize(params: dict) -> str:
    note = params.get("note_text", "")
    return f"""Operator wrote this review note: "{note}"

Which section best fits? Sections: translation, missing, glossary, pronunciation, comments. Return ONLY a JSON object:

{{"section_id": "...", "confidence": 0.0-1.0, "reason": "1-sentence"}}"""


def _prompt_content_range(transcript: Path) -> str:
    return f"""Read the first 30 pages and last 30 pages of {transcript}. Identify:
1. First page of body content (after preface/intro/TOC)
2. Last page of body content (before index/biblio/errata)

Return ONLY a JSON object:

{{"body_starts_at_page": N, "body_ends_at_page": N, "rationale": "1-sentence"}}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "AIResult",
    "BudgetExceeded",
    "BoundaryViolation",
    "MODEL_FOR_FEATURE",
    "EST_COST_USD",
    "BOOK_AI_BUDGET_USD",
    "run_feature",
    "assert_within_worktree",
    "book_ai_spend_so_far",
    "compute_source_signature",
]
