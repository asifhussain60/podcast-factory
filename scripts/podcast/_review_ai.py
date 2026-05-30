#!/usr/bin/env python3
"""AI helper layer for the Operator Review Studio (P25.7).

10 helper features, each delegating to Gemini REST API (NO claude -p).
Uses the keychain `gemini_api_key` — same as every other WC8 script.

  feature_id    trigger                   description
  ─────────────────────────────────────────────────────────────────────────
  summarize     on-demand batch           1-line summary per page
  diff-explain  hover                     why did the LLM change X?
  arabic        on-demand (cached fwd)    detect Arabic terms + cross-ref manifest
  preflight     Cmd-K                     scan whole book for issues
  voice-shift   on-demand                 flag author/voice changes
  episode-plan  on-demand                 propose episode breakdown
  suggest-flags on-demand                 5-10 candidate flags
  autocomplete  200ms in textarea         ghost-text suggestions
  categorize    passive on note change    route note to right section
  content-range pre-fill                  detect body start/end pages

Caching: per-source-signature (sha256 of refined-english.md) for the
expensive whole-book features (summarize / arabic / voice-shift /
preflight / episode-plan). Light features (autocomplete / categorize /
diff-explain / content-range) are stateless.

Cost-ledger: every call writes a row via _cost_ledger.append_gemini_cost().

Boundary: book_dir is validated to be inside worktree_root before any
file read or API call.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Add scripts/podcast to sys.path for sibling imports when run as module
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from _paths import REPO_ROOT  # noqa: E402

try:
    from _cost_ledger import append_gemini_cost  # type: ignore
except ImportError:
    def append_gemini_cost(*args, **kwargs):  # type: ignore
        pass


# All features use gemini-2.5-flash (text-analysis tasks, no vision needed)
MODEL_FOR_FEATURE: dict[str, str] = {
    "summarize":     "gemini-2.5-flash",
    "diff-explain":  "gemini-2.5-flash",
    "arabic":        "gemini-2.5-flash",
    "preflight":     "gemini-2.5-flash",
    "voice-shift":   "gemini-2.5-flash",
    "episode-plan":  "gemini-2.5-flash",
    "suggest-flags": "gemini-2.5-flash",
    "autocomplete":  "gemini-2.5-flash",
    "categorize":    "gemini-2.5-flash",
    "content-range": "gemini-2.5-flash",
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



# ---------------------------------------------------------------------------
# Gemini REST call (replaces former claude -p subprocess)
# ---------------------------------------------------------------------------

def _load_gemini_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError("gemini_api_key not found in keychain — cannot call Studio AI features")
    return r.stdout.strip()


def _call_gemini(prompt: str, model: str = "gemini-2.5-flash", timeout_sec: int = 120) -> str:
    """Call Gemini generateContent endpoint. Returns the text response."""
    key = _load_gemini_key()
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           f":generateContent?key={key}")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8000},
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as r:
        d = json.loads(r.read())
    return d["candidates"][0]["content"]["parts"][0]["text"]


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
    prompt, in_chars = _build_prompt(feature, book_dir, params)

    raw = _call_gemini(prompt, model)
    payload = _extract_json(raw) if feature != "autocomplete" else {"completions": [s.strip() for s in raw.strip().split("\n") if s.strip()][:3]}
    elapsed = time.time() - start
    out_chars = len(raw)

    append_gemini_cost(book_dir, phase=f"ai/{feature}", step="review-studio",
                       model=model, in_chars=in_chars, out_chars=out_chars)

    if feature in CACHEABLE:
        _save_cache(book_dir, feature, source_signature, payload)

    return AIResult(
        feature=feature,
        model=model,
        cached=False,
        cost_usd=EST_COST_USD.get(feature, 0.10),
        payload=payload,
        elapsed_sec=elapsed,
    )


# ---------------------------------------------------------------------------
# Prompt builders (one per feature)
# ---------------------------------------------------------------------------

def _read_optional(path: Path) -> str:
    """Read a file; return empty string if missing (never raises)."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _build_prompt(feature: str, book_dir: Path, params: dict[str, Any]) -> tuple[str, int]:
    """Build the Gemini prompt for a feature. Returns (prompt_text, len(prompt_text))."""
    transcript_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    transcript_text = _read_optional(transcript_path)

    if feature == "summarize":
        p = _prompt_summarize(transcript_text)
    elif feature == "diff-explain":
        p = _prompt_diff_explain(params)
    elif feature == "arabic":
        manifest_path = REPO_ROOT / "content" / "_shared" / "arabic" / "03-arabic-english-manifest.md"
        p = _prompt_arabic(transcript_text, _read_optional(manifest_path))
    elif feature == "preflight":
        p = _prompt_preflight(transcript_text)
    elif feature == "voice-shift":
        p = _prompt_voice_shift(transcript_text)
    elif feature == "episode-plan":
        p = _prompt_episode_plan(transcript_text)
    elif feature == "suggest-flags":
        p = _prompt_suggest_flags(transcript_text)
    elif feature == "autocomplete":
        p = _prompt_autocomplete(params)
    elif feature == "categorize":
        p = _prompt_categorize(params)
    elif feature == "content-range":
        p = _prompt_content_range(transcript_text)
    else:
        raise ValueError(f"no prompt builder for feature {feature}")
    return p, len(p)


def _prompt_summarize(transcript_text: str) -> str:
    return f"""The following is the English transcript of a scholarly book. For each page boundary (marked with `<!-- page N -->` or similar), emit a one-sentence summary of what happens on that page. The summary should be specific enough that a reader can decide whether to dive into that page or skim past it.

Return ONLY a JSON array, no prose, no markdown fences:

[
  {{"page": 1, "summary": "..."}},
  {{"page": 2, "summary": "..."}},
  ...
]

Keep each summary under 80 chars. Capture the SPECIFIC content (named concepts, doctrine introductions, voice shifts), not generic framings like 'the author continues to discuss...'.

TRANSCRIPT:
{transcript_text}"""


def _prompt_diff_explain(params: dict) -> str:
    raw = params.get("raw", "")
    refined = params.get("refined", "")
    return f"""Two passages — the raw OCR output (likely scrambled) and the LLM-refined version. Explain in ONE sentence (max 25 words) why the LLM made the change. Focus on what the operator should verify.

RAW: "{raw}"
REFINED: "{refined}"

Return ONLY a JSON object:
{{"explanation": "..."}}"""


def _prompt_arabic(transcript_text: str, manifest_text: str) -> str:
    return f"""Read the transcript below. Identify every transliterated Arabic term (e.g., daʿwa, jazāʾir, tawḥīd, ḥujja, Imām, fiṭra, etc.). For each unique term, return:

- term: the transliteration as it appears
- canonical_form: the manifest form (if present in the manifest below)
- pages: array of page numbers where it occurs
- manifest_match: true if found in manifest, false otherwise

Return ONLY a JSON array, no prose, no markdown fences.

MANIFEST:
{manifest_text}

TRANSCRIPT:
{transcript_text}"""


def _prompt_preflight(transcript_text: str) -> str:
    return f"""Scan the transcript below for likely operator-actionable issues: OCR scrambles, impossible word pairs, citation typos, voice ruptures, numeric inconsistencies. Be specific — quote the actual text.

Return ONLY a JSON array of findings:

[
  {{"page": N, "quote": "...", "issue_type": "ocr-scramble|impossible-pair|citation|voice-rupture|numeric", "confidence": 0.0-1.0, "suggestion": "what the operator should check"}}
]

Limit to top 10 findings by confidence. Quote the exact text from the transcript.

TRANSCRIPT:
{transcript_text}"""


def _prompt_voice_shift(transcript_text: str) -> str:
    return f"""Read the transcript below. Identify passages where the prose voice noticeably shifts — tense changes, register changes, reportative→assertive ("they say" → "I affirm"), dialect drift, or signs of a second author/editor.

Return ONLY a JSON array:

[
  {{"page": N, "before_quote": "...", "after_quote": "...", "shift_type": "voice|register|tense|author", "confidence": 0.0-1.0, "note": "..."}}
]

Quote ≤30 words for each before/after.

TRANSCRIPT:
{transcript_text}"""


def _prompt_episode_plan(transcript_text: str) -> str:
    return f"""Read the transcript below. Propose an episode breakdown for a podcast series based on this book. Consider chapter structure, thematic units, density.

Return ONLY a JSON object:

{{
  "episode_count": N,
  "rationale": "1-sentence overall rationale",
  "episodes": [
    {{"n": 1, "title": "...", "page_range": [start, end], "target_word_count": N, "recap_cue": "...", "preview_cue": "..."}}
  ]
}}

Typical: 4-8 episodes, 2000-4000 words each. Title should be evocative + accurate.

TRANSCRIPT:
{transcript_text}"""


def _prompt_suggest_flags(transcript_text: str) -> str:
    return f"""Read the transcript below. Suggest 5-10 candidate "translation issue" flags the operator should review — passages where the English looks suspect or could benefit from clarification.

Return ONLY a JSON array:

[
  {{"page": N, "quote": "...", "reason": "1-sentence why this needs operator attention", "confidence": 0.0-1.0}}
]

Quote ≤40 words. Sort by descending confidence.

TRANSCRIPT:
{transcript_text}"""


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


def _prompt_content_range(transcript_text: str) -> str:
    words = transcript_text.split()
    head = " ".join(words[:4000])
    tail = " ".join(words[-4000:])
    return f"""From the beginning and end of this transcript, identify:
1. First page of body content (after preface/intro/TOC)
2. Last page of body content (before index/biblio/errata)

Return ONLY a JSON object:

{{"body_starts_at_page": N, "body_ends_at_page": N, "rationale": "1-sentence"}}

BEGINNING OF TRANSCRIPT:
{head}

END OF TRANSCRIPT:
{tail}"""


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
