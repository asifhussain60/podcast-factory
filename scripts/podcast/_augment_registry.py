"""_augment_registry.py — Profile-keyed augmentation registry + need-detector.

Four content profiles, each with a named strategy, placement mode, and a
cheap text-only need-detector that decides BEFORE spending LLM tokens
whether a chapter actually has augmentation gaps.

DESIGN PRINCIPLES
  - The need-detector runs on plain text with zero LLM calls (heuristics only).
    It is a GATE, not an enricher. When it returns False, augmentation is skipped.
  - The registry is the single source of truth for profile → strategy mapping.
    Add new profiles here; search-and-replace is never needed.
  - "fiction-sidecar" is the ONLY strategy that must NEVER mutate narrative prose.
    All other strategies enrich inline. The sidecar constraint is enforced by
    convention (the Phase 0e fiction augmenter writes a companion file, not the
    chapter file in place).

Engine routing: all LLM augmentation uses ENGINE_CLAUDE_MAX (TASK_AUGMENT).
The need-detector itself is pure Python and does not call any engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# ─── Strategy identifiers ────────────────────────────────────────────────────

STRATEGY_ISLAMIC = "7-tier-islamic"
STRATEGY_TECHNICAL = "technical-accuracy"
STRATEGY_FICTION = "fiction-sidecar"
STRATEGY_GUIDES = "guides-anchoring"
STRATEGY_SKIP = "skip"

# Placement modes
PLACEMENT_INLINE = "inline"  # enriches the chapter file in place
PLACEMENT_SIDECAR = "sidecar"  # writes a companion glossary/aside file ONLY


@dataclass(frozen=True)
class AugmentStrategy:
    name: str
    placement: str
    trigger_description: str  # one-line plain-English description of when augmentation fires
    needs_fn: Callable[[str], bool]


# ─── Category → strategy registry ────────────────────────────────────────────
# Maps the pipeline's `category` field (series-config.yaml) to a strategy name.
# Separate from content_profile (the engine policy field) — some categories
# share strategies (all Islamic scholarly categories map to 7-tier-islamic).

_CATEGORY_TO_STRATEGY: dict[str, str] = {
    # Islamic / scholarly (all variants)
    "books": STRATEGY_ISLAMIC,
    "letters": STRATEGY_ISLAMIC,
    "lectures": STRATEGY_ISLAMIC,
    "articles": STRATEGY_ISLAMIC,
    "asbaaq": STRATEGY_ISLAMIC,
    "documents": STRATEGY_ISLAMIC,
    "interviews": STRATEGY_ISLAMIC,
    # Technical
    "explainers": STRATEGY_TECHNICAL,
    # Fiction / narrative
    "fiction": STRATEGY_FICTION,
    "novels": STRATEGY_FICTION,
    "narrative": STRATEGY_FICTION,
    # Guides / how-to
    "guides": STRATEGY_GUIDES,
    "howto": STRATEGY_GUIDES,
    # Authoritative product docs — skip enrichment entirely
    "sites": STRATEGY_SKIP,
}

# content_profile (engine-policy field) → strategy, for callers that have the
# profile but not the category.
_PROFILE_TO_STRATEGY: dict[str, str] = {
    "islamic_scholarly": STRATEGY_ISLAMIC,
    "technical": STRATEGY_TECHNICAL,
    "fiction": STRATEGY_FICTION,
    "guides": STRATEGY_GUIDES,
    # A delivered lecture is already finished teaching. Augmentation exists to add
    # material the source lacks; here it would put words into a talk Asif gave.
    "islamic_session": STRATEGY_SKIP,
}


# ─── Need-detectors (cheap, text-only heuristics) ────────────────────────────


def _needs_islamic(text: str) -> bool:
    """True if any scriptural quote lacks a Surah:Ayah or hadith attribution.

    Heuristic: look for quoted text (≥ 8 words in quotes) that is not
    followed within 50 chars by a citation pattern (Surah, verse, hadith, etc.).
    A chapter with zero quoted content has nothing to cite — also True, because
    the Islamic 7-tier mandate is to ADD citations to bare doctrinal claims.
    """
    quoted = re.findall(r'"([^"]{30,})"', text)
    if not quoted:
        # No quotations at all → enrichment needed (no sourced citations present)
        return True
    # Check that each quotation has a following citation
    citation_pattern = re.compile(
        r"(?:Surah|surah|verse|Quran|hadith|Nahj|Bihar|Daaim|narrated|reported|"
        r"ibn|Ibn|al-|recorded|referenced|\d+:\d+)",
        re.IGNORECASE,
    )
    for q in quoted[:5]:  # sample first 5
        q_start = text.find(f'"{q}"')
        if q_start == -1:
            continue
        after = text[q_start + len(q) + 2 : q_start + len(q) + 2 + 120]
        if not citation_pattern.search(after):
            return True
    return False


_TECH_ABSTRACT = re.compile(
    r"\b(typically|usually|often|can|may|might|could|generally|sometimes|"
    r"helps|enables|allows|supports|provides)\b",
    re.IGNORECASE,
)
_TECH_VERSION_CLAIM = re.compile(
    r"\b(version|v\d|release|update|since|latest|current|new in|added in)\b",
    re.IGNORECASE,
)


def _needs_technical(text: str) -> bool:
    """True if chapter has abstract claims without version pins or examples.

    Heuristic: count abstract-language triggers vs. concrete anchors
    (code fences, version numbers, explicit 'run X → see Y' patterns).
    If abstract density exceeds concrete density, enrichment is warranted.
    """
    abstract_hits = len(_TECH_ABSTRACT.findall(text))
    code_fences = text.count("```")
    version_hits = len(_TECH_VERSION_CLAIM.findall(text))
    concrete_hits = code_fences + version_hits
    # More abstract claims than concrete anchors → needs enrichment
    return abstract_hits > max(concrete_hits, 3)


_FICTION_CULTURE_TERMS = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"  # Title-cased proper noun phrases
)
_FICTION_CAST_THRESHOLD = 6  # distinct proper-noun clusters indicating a large cast
_FICTION_MYTH_WORDS = re.compile(
    r"\b(immortal|celestial|deity|demon|spirit|heaven|palace|emperor|king|"
    r"dragon|jade|monk|pilgrim|scripture|prophecy|divine|general|army|"
    r"kingdom|dynasty|mountain|cloud|thunder|magic|spell|transformation)\b",
    re.IGNORECASE,
)


def _needs_fiction(text: str) -> bool:
    """True if chapter has culture-dense content: large cast, mythological terms,
    or allusions that a Western listener would likely miss.

    Heuristic: count distinct proper-noun clusters and mythology-density score.
    """
    proper_nouns = {
        m.group(1)
        for m in _FICTION_CULTURE_TERMS.finditer(text)
        if len(m.group(1).split()) >= 2 or m.group(1)[0].isupper()
    }
    cast_size = len(proper_nouns)
    myth_density = len(_FICTION_MYTH_WORDS.findall(text))
    words = len(text.split())
    myth_ratio = myth_density / max(words, 1)

    return cast_size >= _FICTION_CAST_THRESHOLD or myth_ratio > 0.015


_GUIDES_ABSOLUTE = re.compile(
    r"\b(always|never|must|will|guaranteed|certainly|definitely|"
    r"every time|in all cases|without exception)\b",
    re.IGNORECASE,
)
_GUIDES_CITATION = re.compile(
    r"(?:according to|source:|study|research|found that|shows that|"
    r"data|evidence|cited|referenced|per \w)",
    re.IGNORECASE,
)


def _needs_guides(text: str) -> bool:
    """True if chapter uses absolute phrasing without sourced evidence.

    Heuristic: absolute-language hits vs. citation anchors.
    """
    absolute_hits = len(_GUIDES_ABSOLUTE.findall(text))
    citation_hits = len(_GUIDES_CITATION.findall(text))
    return absolute_hits > max(citation_hits, 2)


def _skip(_: str) -> bool:
    return False


# ─── Strategy registry (built after detectors are defined) ───────────────────

_REGISTRY: dict[str, AugmentStrategy] = {
    STRATEGY_ISLAMIC: AugmentStrategy(
        name=STRATEGY_ISLAMIC,
        placement=PLACEMENT_INLINE,
        trigger_description="uncited scriptural quotation or bare doctrinal claim",
        needs_fn=_needs_islamic,
    ),
    STRATEGY_TECHNICAL: AugmentStrategy(
        name=STRATEGY_TECHNICAL,
        placement=PLACEMENT_INLINE,
        trigger_description="abstract claim without version pin, code example, or concrete anchor",
        needs_fn=_needs_technical,
    ),
    STRATEGY_FICTION: AugmentStrategy(
        name=STRATEGY_FICTION,
        placement=PLACEMENT_SIDECAR,
        trigger_description="culture-dense text with large cast, mythological terms, or unfamiliar allusions",
        needs_fn=_needs_fiction,
    ),
    STRATEGY_GUIDES: AugmentStrategy(
        name=STRATEGY_GUIDES,
        placement=PLACEMENT_INLINE,
        trigger_description="absolute phrasing (always/never/must) without sourced evidence",
        needs_fn=_needs_guides,
    ),
    STRATEGY_SKIP: AugmentStrategy(
        name=STRATEGY_SKIP,
        placement=PLACEMENT_INLINE,
        trigger_description="never — source is authoritative, enrichment would introduce inaccuracy",
        needs_fn=_skip,
    ),
}


# ─── Public API ───────────────────────────────────────────────────────────────


def strategy_for_category(category: str) -> AugmentStrategy:
    """Return the augmentation strategy for a pipeline `category` string.

    Unknown categories default to STRATEGY_SKIP to avoid accidentally enriching
    an unclassified book with the wrong strategy.
    """
    name = _CATEGORY_TO_STRATEGY.get(category.lower().strip(), STRATEGY_SKIP)
    return _REGISTRY[name]


def strategy_for_profile(content_profile: str) -> AugmentStrategy:
    """Return the augmentation strategy for a `content_profile` string.

    Unknown profiles default to STRATEGY_SKIP for the same reason as above.
    """
    name = _PROFILE_TO_STRATEGY.get(content_profile.lower().strip(), STRATEGY_SKIP)
    return _REGISTRY[name]


def needs_augmentation(chapter_text: str, *, category: str = "", content_profile: str = "") -> bool:
    """Return True if this chapter has augmentation gaps per its profile's detector.

    Exactly one of `category` or `content_profile` must be supplied.
    Always returns False for the SKIP strategy (authoritative source docs).
    Never calls an LLM — this is a cheap heuristic gate.

    Raises ValueError if neither argument is supplied.
    """
    if category:
        strat = strategy_for_category(category)
    elif content_profile:
        strat = strategy_for_profile(content_profile)
    else:
        raise ValueError("needs_augmentation: supply either category= or content_profile=")
    return strat.needs_fn(chapter_text)


def all_strategies() -> list[str]:
    """All strategy names (used by tests to assert full coverage)."""
    return sorted(_REGISTRY)
