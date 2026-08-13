#!/usr/bin/env python3
"""_engine.py — central engine-selection policy (single source of truth).

The pipeline uses four AI engine families with different billing models. This
module is the ONE place that decides which engine runs a given task, so engine
choice is a tested policy rather than scattered hardcoding.

LOCKED HIERARCHY (Asif, 2026-06-06):
  Tier 1 — Claude Max (`claude -p`, flat-rate, $0 marginal): the DEFAULT engine,
           prioritized over Gemini.
  Tier 2 — Azure (committed/attached services): Document Intelligence (OCR),
           Translator (bulk/utility translation), Speech (TTS/STT). Used for the
           jobs those services provide.
  Tier 3 — Gemini (pay-as-you-go): NOT banned — used when needed or when it is
           genuinely better than Claude (e.g. image generation, which has NO
           Azure equivalent in the current subscription).
  Fallback — Codex ChatGPT (`codex exec`, flat-rate ChatGPT subscription): used
             explicitly when Claude Max is exhausted; never a metered API path.

  Registered exception: 0b/0c windowed refinement runs on the metered Anthropic
  SDK because it parallelizes windows in-process — the `claude -p` CLI cannot.

Two policy facts that follow from the current Azure subscription + quality:
  - There is NO Azure image generation (no Azure OpenAI/DALL·E provisioned), so
    `image_gen` → Gemini. Routed through here so it is swappable if Azure image
    gen is ever added.
  - LITERARY translation → Claude Max (tier 1, far better than machine
    translation on classical text); only BULK/utility translation → Azure.

Usage:
    from _engine import select_engine, TASK_IMAGE_PROMPT, ENGINE_CLAUDE_MAX
    if select_engine(TASK_IMAGE_PROMPT) == ENGINE_CLAUDE_MAX:
        ...   # run claude -p
    # per-task override (e.g. a book that pins Gemini for a task it does better):
    eng = select_engine(TASK_REVOICE, override=ENGINE_GEMINI)
"""

from __future__ import annotations

# ─── Engine identifiers ───────────────────────────────────────────────────────
ENGINE_CLAUDE_MAX = "claude_max"  # claude -p, flat-rate Max, $0 marginal
ENGINE_CODEX_CHATGPT = "codex_chatgpt"  # codex exec, flat-rate ChatGPT subscription
ENGINE_AZURE = "azure"  # committed Azure services
ENGINE_GEMINI = "gemini"  # pay-as-you-go Google
ENGINE_ANTHROPIC_SDK = "anthropic_sdk"  # metered Anthropic API (windowed exception)

ENGINE_TIER = {
    ENGINE_CLAUDE_MAX: 1,
    ENGINE_CODEX_CHATGPT: 1,
    ENGINE_AZURE: 2,
    ENGINE_GEMINI: 3,
    ENGINE_ANTHROPIC_SDK: "exception",
}

# ─── Task identifiers ─────────────────────────────────────────────────────────
TASK_TRANSLATE_LITERARY = "translate_literary"
TASK_TRANSLATE_BULK = "translate_bulk"
TASK_OCR = "ocr"
TASK_TRANSCRIBE = "transcribe"
TASK_TTS = "tts"
TASK_REFINE_WINDOWED = "refine_windowed"  # phase 0b / 0c windowed refine
TASK_CHAPTER_DESIGN = "chapter_design"  # phase 0d
TASK_ENRICH = "enrich"  # phase 0e
TASK_AUTHOR = "author"  # per-chapter framing/authoring
TASK_IMAGE_PROMPT = "image_prompt"  # storyboard / slide-manifest text
TASK_IMAGE_GEN = "image_gen"  # actual image rendering (DALL-E 3 via Azure OpenAI)
TASK_AUGMENT = "augment"  # augmentation (any profile)
TASK_REVOICE = "revoice"  # literary re-voice (_literary.py)
TASK_DENOISE = "denoise"  # WC8 denoise/normalize (gemini_refine)
TASK_VOWEL = "vowel"  # Arabic vocalisation (vowel_book / vowel_source / vowel_glossary)
TASK_AUDIT = "audit"  # bundle audit (second-model gate)
TASK_RECONCILE = "reconcile"  # split-source reconcile
TASK_REVIEW_HELPER = "review_helper"  # review-studio helper features
TASK_NER = "ner"  # named-entity recognition (Azure Language)
TASK_KEY_PHRASES = "key_phrases"  # key-phrase extraction (Azure Language)
TASK_SENTIMENT = "sentiment"  # sentiment analysis (Azure Language)

# ─── The policy table ─────────────────────────────────────────────────────────
# Maps each task to its default engine per the locked hierarchy. Per-task
# overrides are supplied by callers (e.g. a book pinning Gemini for a task it
# does better); the override always wins.
_POLICY: dict[str, str] = {
    # Tier 1 — Claude Max (default for reasoning + text generation)
    TASK_TRANSLATE_LITERARY: ENGINE_CLAUDE_MAX,
    TASK_CHAPTER_DESIGN: ENGINE_CLAUDE_MAX,
    TASK_ENRICH: ENGINE_CLAUDE_MAX,
    TASK_AUTHOR: ENGINE_CLAUDE_MAX,
    TASK_IMAGE_PROMPT: ENGINE_CLAUDE_MAX,  # swapped from Gemini (Max-first)
    TASK_AUGMENT: ENGINE_CLAUDE_MAX,
    # Tier 2 — Azure (the attached committed services do these jobs)
    TASK_OCR: ENGINE_AZURE,
    TASK_TRANSLATE_BULK: ENGINE_AZURE,
    TASK_TRANSCRIBE: ENGINE_AZURE,
    TASK_TTS: ENGINE_AZURE,
    # Tier 2 — Azure Language (TextAnalytics — NER, key-phrase, sentiment)
    TASK_NER: ENGINE_AZURE,
    TASK_KEY_PHRASES: ENGINE_AZURE,
    TASK_SENTIMENT: ENGINE_AZURE,
    # Tier 3 — Gemini (image gen: Azure OpenAI has no active image model in eastus as of 2026-06-06;
    #           DALL-E 3 deprecated March 2026, gpt-image-1 not yet available in this region.
    #           Revisit when Azure lands gpt-image-1. Route through _engine so the swap is one line.)
    TASK_IMAGE_GEN: ENGINE_GEMINI,
    # Tier 3 — Gemini (kept where genuinely better today)
    TASK_REVOICE: ENGINE_GEMINI,  # kept (Gemini-tuned today)
    TASK_DENOISE: ENGINE_GEMINI,
    TASK_VOWEL: ENGINE_GEMINI,
    TASK_AUDIT: ENGINE_GEMINI,  # second-model gate vs Claude
    TASK_RECONCILE: ENGINE_GEMINI,
    TASK_REVIEW_HELPER: ENGINE_GEMINI,
    # Registered exception — windowed parallelism the CLI can't do
    TASK_REFINE_WINDOWED: ENGINE_ANTHROPIC_SDK,
}

# Human-readable rationale per task (for logs + the policy doc; tested for coverage).
_RATIONALE: dict[str, str] = {
    TASK_TRANSLATE_LITERARY: "tier-1 Max; better literary quality than Azure MT",
    TASK_TRANSLATE_BULK: "tier-2 Azure Translator for bulk/utility translation",
    TASK_OCR: "tier-2 Azure Document Intelligence",
    TASK_TRANSCRIBE: "tier-2 Azure Speech STT",
    TASK_TTS: "tier-2 Azure Speech Neural TTS",
    TASK_REFINE_WINDOWED: "exception: SDK windowed parallelism the CLI can't do",
    TASK_CHAPTER_DESIGN: "tier-1 Max reasoning",
    TASK_ENRICH: "tier-1 Max reasoning",
    TASK_AUTHOR: "tier-1 Max reasoning",
    TASK_IMAGE_PROMPT: "tier-1 Max (Max-first swap off Gemini text)",
    TASK_IMAGE_GEN: "tier-3 Gemini Imagen3 — Azure OpenAI DALL-E deprecated Mar 2026, gpt-image-1 not yet in eastus",
    TASK_AUGMENT: "tier-1 Max reasoning",
    TASK_NER: "tier-2 Azure Language TextAnalytics (journal-language-market, F0 free)",
    TASK_KEY_PHRASES: "tier-2 Azure Language TextAnalytics (journal-language-market, F0 free)",
    TASK_SENTIMENT: "tier-2 Azure Language TextAnalytics (journal-language-market, F0 free)",
    TASK_VOWEL: "tier-3 Gemini 2.5 Pro — vocalising an ambiguous verb is a reasoning task, and the marks-only gate bounds it",
    TASK_REVOICE: "tier-3 Gemini — kept where currently better",
    TASK_DENOISE: "tier-3 Gemini — kept where currently better",
    TASK_AUDIT: "tier-3 Gemini — independent second-model gate",
    TASK_RECONCILE: "tier-3 Gemini — kept where currently better",
    TASK_REVIEW_HELPER: "tier-3 Gemini — review-studio helpers",
}


def select_engine(task: str, *, override: str | None = None) -> str:
    """Return the engine for *task* per the locked hierarchy.

    A non-None *override* (one of the ENGINE_* constants) always wins — used by a
    book/config that pins a different engine for a task it does better. Raises
    ValueError on an unknown task or an invalid override, so a typo can never
    silently fall through to a wrong (e.g. pay-as-you-go) engine.
    """
    if override is not None:
        if override not in ENGINE_TIER:
            raise ValueError(f"select_engine: unknown override engine {override!r}")
        return override
    try:
        return _POLICY[task]
    except KeyError:
        raise ValueError(
            f"select_engine: unknown task {task!r}. Add it to _POLICY in _engine.py "
            f"with an explicit engine — engine choice must never be implicit."
        ) from None


def rationale(task: str) -> str:
    """One-line reason for the policy choice (for logging / the policy doc)."""
    return _RATIONALE.get(task, "(no rationale recorded)")


def engine_tier(engine: str) -> int | str:
    """Return the cost tier of an engine (1 Max / 2 Azure / 3 Gemini / exception)."""
    if engine not in ENGINE_TIER:
        raise ValueError(f"engine_tier: unknown engine {engine!r}")
    return ENGINE_TIER[engine]


def all_tasks() -> list[str]:
    """Every task the policy governs (used by tests to assert full coverage)."""
    return sorted(_POLICY)


def engine_guard(task: str, actual_engine: str) -> None:
    """Assert that `actual_engine` matches the policy for `task`.

    Call this at the top of every engine-specific helper function so that a
    policy change in `_POLICY` immediately surfaces as a runtime warning —
    rather than silently using the wrong (e.g. pay-as-you-go) engine.

    Raises ValueError on an unknown task (same as select_engine). Logs a
    warning to stderr when there is a policy mismatch so shipped code is never
    silently wrong, but does NOT raise on mismatch — callers own the engine
    choice; the guard is diagnostic, not a hard gate.
    """
    expected = select_engine(task)
    if expected != actual_engine:
        import sys

        print(
            f"[engine-policy] WARNING: {task!r} policy says {expected!r} "
            f"but this function uses {actual_engine!r}. "
            f"Rationale: {rationale(task)}",
            file=sys.stderr,
        )
