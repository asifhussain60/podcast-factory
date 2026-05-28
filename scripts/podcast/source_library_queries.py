"""source_library_queries.py — Wave J (J0): six canonical query functions.

All functions delegate to tools.source_extractor.db.query_json which routes
queries through the local wisdom-mssql Docker container via sqlcmd.
This module has no transport logic — it is shared by both the HTTP and MCP
stdio transports in source_library_server.py.

Six functions:
    quran_lookup        — single verse by surah + ayat
    quran_theme_search  — LIKE keyword search across translations (FTS5 in J1)
    word_etymology      — root + derivatives from KQUR
    topic_search        — LIKE search over KASHKOLE Topics
    topic_get           — full topic record + ayats + glossary
    session_style_fetch — style passages from KSESSIONS SessionSummary
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.source_extractor.db import query_json


# ── helpers ──────────────────────────────────────────────────────────────────

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not text:
        return ""
    cleaned = _HTML_TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", cleaned).strip()


def _esc(value: str) -> str:
    """Minimal SQL string escape: replace single-quotes with doubled quotes."""
    return value.replace("'", "''")


# ── public API ────────────────────────────────────────────────────────────────

def quran_lookup(surah: int, ayat: int) -> dict[str, Any]:
    """Return a single Quran verse by surah and ayat numbers.

    Returns a dict with keys: surah, ayat, arabic, pickthall, asad, urdu,
    phonetic.  Returns {"error": "..."} if the verse is not found.
    """
    sql = f"""
SELECT TOP 1
    SurahNumber        AS surah,
    AyatNumber         AS ayat,
    AyatUNICODE        AS arabic,
    AyatTranslation    AS pickthall,
    Translation_Asad   AS asad,
    UrduTranslation    AS urdu,
    Phonetic           AS phonetic
FROM QuranAyats
WHERE SurahNumber = {int(surah)} AND AyatNumber = {int(ayat)}
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER;
"""
    rows = query_json("KQUR", sql)
    if not rows:
        return {"error": f"Verse {surah}:{ayat} not found"}
    return rows[0]


def quran_theme_search(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search Quran verses by keyword (LIKE scan; FTS5 in J1).

    Searches Pickthall and Asad translations.  Returns up to `limit` results,
    each with keys: surah, ayat, arabic, pickthall, asad, phonetic.
    """
    kw = _esc(keyword.strip())
    n = max(1, min(int(limit), 50))
    sql = f"""
SELECT TOP {n}
    SurahNumber        AS surah,
    AyatNumber         AS ayat,
    AyatUNICODE        AS arabic,
    AyatTranslation    AS pickthall,
    Translation_Asad   AS asad,
    Phonetic           AS phonetic
FROM QuranAyats
WHERE AyatTranslation LIKE '%{kw}%'
   OR Translation_Asad LIKE '%{kw}%'
ORDER BY SurahNumber, AyatNumber
FOR JSON PATH;
"""
    return query_json("KQUR", sql) or []


def word_etymology(term: str) -> dict[str, Any]:
    """Return root + derivatives for an Arabic term.

    Searches Roots.RootTransliteration and Roots.MeaningEnglish.  Returns
    {"root": {...}, "derivatives": [...]} or {"error": "..."}.
    """
    t = _esc(term.strip())
    root_sql = f"""
SELECT TOP 1
    RootID             AS root_id,
    RootWord           AS root_arabic,
    RootTransliteration AS transliteration,
    MeaningEnglish     AS meaning_en,
    MeaningArabic      AS meaning_ar,
    Definition         AS definition
FROM Roots
WHERE RootTransliteration LIKE '%{t}%'
   OR MeaningEnglish      LIKE '%{t}%'
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER;
"""
    roots = query_json("KQUR", root_sql)
    if not roots:
        return {"error": f"No root found for '{term}'"}
    root = roots[0]
    rid = int(root["root_id"])
    deriv_sql = f"""
SELECT
    Derivative         AS term,
    Transliteration    AS transliteration,
    MeaningEnglish     AS meaning_en,
    MeaningArabic      AS meaning_ar,
    Grammar            AS grammar,
    Definition         AS definition
FROM Derivatives
WHERE RootID = {rid}
ORDER BY SortOrder
FOR JSON PATH;
"""
    return {
        "root": root,
        "derivatives": query_json("KQUR", deriv_sql) or [],
    }


def topic_search(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search KASHKOLE topics by keyword (name search, LIKE; FTS5 in J1).

    Returns up to `limit` results, each with keys: topic_id, name, name_en,
    description, binder, chapter, snippet (first 400 chars of topic text).
    """
    kw = _esc(keyword.strip())
    n = max(1, min(int(limit), 50))
    sql = f"""
SELECT TOP {n}
    t.TopicID                          AS topic_id,
    t.TopicName                        AS name,
    t.TopicNameEnglish                 AS name_en,
    t.TopicDescription                 AS description,
    bc.BinderID                        AS binder_id,
    b.BinderName                       AS binder,
    bc.ChapterName                     AS chapter,
    LEFT(td.TopicUnicodeStripped, 400) AS snippet
FROM Topics t
LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
LEFT JOIN BinderChapterTopics bct ON bct.TopicID = t.TopicID
LEFT JOIN BinderChapters bc ON bc.BinderChapterID = bct.BinderChapterID
LEFT JOIN Binders b ON b.BinderID = bc.BinderID
WHERE t.TopicName        LIKE '%{kw}%'
   OR t.TopicNameEnglish LIKE '%{kw}%'
ORDER BY t.ViewCount DESC
FOR JSON PATH;
"""
    return query_json("KASHKOLE", sql) or []


def topic_get(topic_id: int) -> dict[str, Any]:
    """Return the full topic record including ayats and glossary terms.

    Returns {"topic": {...}, "ayats": [...], "glossary": [...]}
    or {"error": "..."} if not found.
    """
    tid = int(topic_id)
    topic_sql = f"""
SELECT
    t.TopicID          AS topic_id,
    t.TopicName        AS name,
    t.TopicNameEnglish AS name_en,
    t.TopicDescription AS description,
    td.TopicUnicode    AS body_arabic,
    td.TopicUnicodeStripped AS body_plain
FROM Topics t
LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
WHERE t.TopicID = {tid}
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER;
"""
    topics = query_json("KASHKOLE", topic_sql)
    if not topics:
        return {"error": f"Topic {topic_id} not found"}

    ayats_sql = f"""
SELECT
    ta.SurahAyat       AS ref,
    ta.Surah           AS surah,
    ta.Ayat            AS ayat
FROM TopicAyats ta
WHERE ta.TopicID = {tid}
ORDER BY ta.Surah, ta.Ayat
FOR JSON PATH;
"""
    glossary_sql = f"""
SELECT
    g.GlossaryID       AS glossary_id,
    g.TermName         AS term,
    g.TermDefinition   AS definition
FROM TopicGlossaries tg
JOIN Glossary g ON g.GlossaryID = tg.GlossaryID
WHERE tg.TopicID = {tid}
ORDER BY g.TermName
FOR JSON PATH;
"""
    return {
        "topic": topics[0],
        "ayats": query_json("KASHKOLE", ayats_sql) or [],
        "glossary": query_json("KASHKOLE", glossary_sql) or [],
    }


def session_style_fetch(
    theme: str,
    group_id: int | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Return style-reference passages from KSESSIONS that match a theme.

    Searches SessionSummary.SessionContent (HTML, stripped) and
    Sessions.SessionName.  Returns up to `limit` passages, each with keys:
    session_id, session_name, group_id, passage (plain text, HTML stripped).
    """
    kw = _esc(theme.strip())
    n = max(1, min(int(limit), 20))
    group_clause = (
        f"AND s.GroupID = {int(group_id)}" if group_id is not None else ""
    )
    sql = f"""
SELECT TOP {n}
    s.SessionID        AS session_id,
    s.SessionName      AS session_name,
    s.GroupID          AS group_id,
    ss.SessionContent  AS passage_html
FROM Sessions s
JOIN SessionSummary ss ON ss.SessionId = s.SessionID
WHERE ss.IsActive = 1
  AND (ss.SessionContent LIKE '%{kw}%'
       OR s.SessionName  LIKE '%{kw}%')
  {group_clause}
ORDER BY s.SessionDate DESC
FOR JSON PATH;
"""
    rows = query_json("KSESSIONS", sql) or []
    out = []
    for r in rows:
        out.append({
            "session_id": r.get("session_id"),
            "session_name": r.get("session_name"),
            "group_id": r.get("group_id"),
            "passage": _strip_html(r.get("passage_html") or ""),
        })
    return out
