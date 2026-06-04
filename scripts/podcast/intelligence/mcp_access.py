"""mcp_access.py — central MCP knowledge access for the podcast pipeline.

Every pipeline stage that needs to read from the source-library knowledge
databases (KQUR, KASHKOLE, KSESSIONS) goes through this module.  It wraps
source_library_queries.py with:

  - Pipeline-safe error handling: every function returns a typed result or a
    safe empty value — never raises.  A down mirror or absent OrbStack cannot
    break a pipeline stage.
  - Tradition filtering: reject results whose tradition is incompatible with
    the book being processed (e.g. Sunni-Sufi Ayyuhal Walad should not inject
    Ismaili-only doctrinal atoms unless Asif overrides).
  - Zero claude -p calls.  All access is local SQLite (mirror.db) or targeted
    SQL Server queries via docker exec — no LLM spend.

Six pipeline augmentation patterns and when each fires:

  Pattern 1 — Citation verify     (Knowledge stage, Reconcile stage)
    verify_quran_citation(surah, ayat) -> dict | None

  Pattern 2 — Concept verse search (Augment stage, Framing stage)
    search_quran_by_concept(concept, limit) -> list[dict]

  Pattern 3 — Hadith retrieve      (Knowledge stage, Augment stage)
    find_hadith(text_hint, limit) -> list[dict]

  Pattern 4 — Etymology annotation (Augment stage, Framing stage)
    get_etymology(term) -> dict | None

  Pattern 5 — Style reference      (Framing / authoring stage)
    get_style_reference(theme, group_id, limit) -> list[dict]

  Pattern 6 — Doctrine context     (Augment stage, Challenger validation)
    get_doctrine_context(concept, tradition, type_ids, limit) -> list[dict]

All return types are plain dicts or lists of dicts — no custom classes.
Callers can pass results directly into Gemini/Claude prompts as JSON.

Usage:
    from scripts.podcast.intelligence.mcp_access import (
        verify_quran_citation,
        search_quran_by_concept,
        find_hadith,
        get_etymology,
        get_style_reference,
        get_doctrine_context,
    )
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent           # …/scripts/podcast/intelligence
_SCRIPTS = _HERE.parent                           # …/scripts/podcast
_REPO = _SCRIPTS.parents[1]                       # repo root
for p in (str(_SCRIPTS), str(_REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.podcast.source_library_queries import (
    quran_lookup,
    quran_theme_search,
    hadith_lookup,
    word_etymology,
    session_style_fetch,
    topic_search,
    topic_get,
)
from scripts.podcast.source_library_mirror import open_mirror

# ---------------------------------------------------------------------------
# KASHKOLE TypeID constants (from Lookup_TopicTypes)
# ---------------------------------------------------------------------------

TYPE_HADITH_PROPHETIC   = 17   # حدیث نبوی — Prophetic Hadith
TYPE_HADITH_COMMENTARY  = 23   # معنی الحدیث — Hadith Commentary
TYPE_QURAN_MEANING      = 19   # معنی آیت القرآن — Quranic verse exegesis
TYPE_ETHICS_COUNSEL     = 18   # نصیحت و اخلاقیات — Ethical counsel
TYPE_GOLDEN_SAYINGS     = 20   # اقوال زریں — Golden sayings / aphorisms
TYPE_ESOTERIC_KNOWLEDGE = 27   # علم الباطنۃ — Esoteric / batin knowledge
TYPE_POETRY_MANQABAT    = 31   # منقبت — Devotional praise poems
TYPE_PROOF_ARGUMENT     = 15   # حجت و دلیل — Proof and argument
TYPE_DOCTRINAL_TERM     = 33   # دینی اسطلاح — Doctrinal terminology

# Groups of TypeIDs by intended use in the pipeline:
HADITH_TYPE_IDS      = (TYPE_HADITH_PROPHETIC, TYPE_HADITH_COMMENTARY)
POETRY_TYPE_IDS      = (TYPE_POETRY_MANQABAT,)
ENRICHMENT_TYPE_IDS  = (TYPE_ETHICS_COUNSEL, TYPE_GOLDEN_SAYINGS,
                        TYPE_ESOTERIC_KNOWLEDGE, TYPE_PROOF_ARGUMENT)
ALL_TYPE_IDS         = tuple(range(100))  # sentinel meaning "no filter"


# ---------------------------------------------------------------------------
# Pattern 1 — Citation verify
# ---------------------------------------------------------------------------

def verify_quran_citation(surah: int, ayat: int) -> dict[str, Any] | None:
    """Verify a Quran citation and return the canonical verse record.

    Used by the Knowledge stage and Reconcile stage to confirm that a
    citation found in the text is real and to retrieve the Arabic + translations.

    Returns None if the verse does not exist.  Never raises.

    Keys: surah, ayat, arabic, pickthall, asad, urdu, phonetic.
    """
    try:
        result = quran_lookup(int(surah), int(ayat))
        if "error" in result:
            return None
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pattern 2 — Concept verse search
# ---------------------------------------------------------------------------

def search_quran_by_concept(concept: str, limit: int = 5) -> list[dict[str, Any]]:
    """Find Quran verses relevant to a concept or theme keyword.

    Used by the Augment stage to propose candidate verses for enrichment,
    and by the Framing stage to surface relevant Quran context for the
    framing prompt.

    Returns up to `limit` verses.  Keys: surah, ayat, arabic, pickthall,
    asad, phonetic.  Returns [] on any error.
    """
    try:
        return quran_theme_search(concept.strip(), limit=limit)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Pattern 3 — Hadith retrieve
# ---------------------------------------------------------------------------

def find_hadith(
    text_hint: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find hadith matching a text hint (English keywords or phrase).

    Used by the Knowledge stage to verify a hadith reference found in the
    chapter text, and by the Augment stage to propose hadith for enrichment.

    Returns up to `limit` hadith dicts.  Keys: hadith_id, collection,
    hadith_num, arabic, english, score, source.  Returns [] on any error.
    """
    try:
        return hadith_lookup(text_hint.strip(), limit=limit)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Pattern 4 — Etymology annotation
# ---------------------------------------------------------------------------

def get_etymology(term: str) -> dict[str, Any] | None:
    """Return the etymology record for an Arabic term or transliteration.

    Used by the Augment stage to annotate terminus technicus (tawil,
    wilaya, batin, etc.) and by the Framing stage to build glossary
    context for framing prompts.

    Returns None if term not found.  Keys: root (dict), derivatives (list),
    source ("mirror" or "sql").
    """
    try:
        result = word_etymology(term.strip())
        if "error" in result:
            return None
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pattern 5 — Style reference
# ---------------------------------------------------------------------------

def get_style_reference(
    theme: str,
    group_id: int | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Fetch teaching-session passages for voice/style reference.

    Used by the Framing stage when building the framing prompt for an
    episode .txt file.  The passages capture how the Shaykh explains this
    theme in his own words — the podcasters model their voice on this.

    `group_id` narrows to a specific session group (e.g. a course series).
    Returns up to `limit` passages.  Keys: session_id, session_name,
    group_id, passage (plain text, HTML stripped).
    """
    try:
        return session_style_fetch(theme.strip(), group_id=group_id, limit=limit)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Pattern 6 — Doctrine context
# ---------------------------------------------------------------------------

def get_doctrine_context(
    concept: str,
    tradition: str | None = None,
    type_ids: tuple[int, ...] = ALL_TYPE_IDS,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return KASHKOLE wisdom topics matching a concept, filtered by type.

    Used by the Augment stage to inject doctrinal context paragraphs and
    by the Challenger validation to verify that a doctrinal claim in the
    episode text is supported by the corpus.

    `tradition` is passed through for future server-side filtering; today
    all KASHKOLE content is Ismaili tradition so no filtering is applied.

    `type_ids` narrows by Lookup_TopicTypes.TopicTypeID.  Use the module
    constants (HADITH_TYPE_IDS, POETRY_TYPE_IDS, ENRICHMENT_TYPE_IDS) or
    ALL_TYPE_IDS to disable the filter.

    Returns up to `limit` topics from both mirror FTS5 and (if needed) SQL
    Server.  Each dict: topic_id, topic_type_id, name, description, binder,
    chapter, snippet.
    """
    try:
        raw = topic_search(concept.strip(), limit=limit * 3)
        if not raw:
            return []
        filtered: list[dict[str, Any]] = []
        for r in raw:
            tid = r.get("topic_type_id")
            if tid is None:
                # Older result from SQL Server fallback (no type_id column); include
                filtered.append(r)
            elif ALL_TYPE_IDS is type_ids or int(tid) in type_ids:
                filtered.append(r)
            if len(filtered) >= limit:
                break
        return filtered
    except Exception:
        return []


def get_doctrine_topic(topic_id: int) -> dict[str, Any] | None:
    """Return a full KASHKOLE topic record by ID, including linked ayats.

    Use this when you already know the topic_id (e.g. from a B5 ingest
    pass or from `get_doctrine_context`) and want the full body text +
    linked Quran ayats.  This call goes to SQL Server when OrbStack is
    running, or returns the mirror body text when it is not.

    Returns None if not found.
    """
    try:
        result = topic_get(int(topic_id))
        if "error" in result:
            return None
        return result
    except Exception:
        # Mirror fallback: get body from fts_topics when SQL Server is unavailable
        try:
            conn = open_mirror()
            if conn is None:
                return None
            row = conn.execute(
                "SELECT topic_id, topic_type_id, name, name_en, description, "
                "binder, chapter, body_plain "
                "FROM fts_topics WHERE topic_id = ? LIMIT 1",
                (int(topic_id),),
            ).fetchone()
            conn.close()
            if row is None:
                return None
            return {
                "topic": dict(row),
                "ayats": [],   # not available without SQL Server
                "glossary": [],
            }
        except Exception:
            return None
