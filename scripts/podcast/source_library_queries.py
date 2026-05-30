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

_mirror: object = None  # lazy-imported to avoid circular import


def _get_mirror():
    """Lazy-import the mirror module and return an open connection, or None."""
    global _mirror
    try:
        import importlib
        mod = importlib.import_module("scripts.podcast.source_library_mirror")
        return mod.open_mirror()
    except Exception:
        return None


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
FOR JSON PATH;
"""
    rows = query_json("KQUR", sql)
    if not rows:
        return {"error": f"Verse {surah}:{ayat} not found"}
    return rows[0]


def quran_theme_search(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search Quran verses by keyword.  Tries FTS5 mirror first; falls back to
    LIKE scan on SQL Server.

    Returns up to `limit` results, each with keys: surah, ayat, arabic,
    pickthall, asad, phonetic.
    """
    from scripts.podcast.source_library_mirror import fts_quran_search  # noqa: PLC0415
    results = fts_quran_search(keyword, limit)
    if results:
        return results
    # Fall back to SQL Server LIKE scan
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
    """Return root + derivatives for an Arabic term.  Checks term_index in the
    local mirror first (sub-ms lookup); falls back to SQL Server on miss.

    Returns {"root": {...}, "derivatives": [...]} or {"error": "..."}.
    """
    from scripts.podcast.source_library_mirror import term_index_lookup  # noqa: PLC0415
    cached = term_index_lookup(term)
    if cached:
        return {
            "root": {
                "root_arabic":     cached.get("arabic", ""),
                "transliteration": cached.get("root", ""),
                "meaning_en":      cached.get("definition", ""),
                "meaning_ar":      cached.get("arabic", ""),
                "definition":      cached.get("etymology", ""),
            },
            "derivatives": [],
            "source": "mirror",
        }
    # Fall back to SQL Server
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
FOR JSON PATH;
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
    """Search KASHKOLE topics by keyword.  Tries FTS5 mirror first; falls back
    to LIKE scan on SQL Server.

    Returns up to `limit` results, each with keys: topic_id, name, name_en,
    description, binder, chapter, snippet.
    """
    from scripts.podcast.source_library_mirror import fts_topics_search  # noqa: PLC0415
    results = fts_topics_search(keyword, limit)
    if results:
        return results
    # Fall back to SQL Server LIKE scan
    kw = _esc(keyword.strip())
    n = max(1, min(int(limit), 50))
    sql = f"""
SELECT TOP {n}
    t.TopicID                          AS topic_id,
    t.TopicName                        AS name,
    t.TopicNameEnglish                 AS name_en,
    t.TopicDescription                 AS description,
    bct.BinderID                       AS binder_id,
    bct.BinderName                     AS binder,
    bct.ChapterName                    AS chapter,
    LEFT(td.TopicUnicodeStripped, 400) AS snippet
FROM Topics t
LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
LEFT JOIN BinderChapterTopics bct ON bct.TopicID = t.TopicID
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
FOR JSON PATH;
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


def discover_hadith_schema() -> list[str]:
    """Print and return KQUR.Ahadees column names (SELECT TOP 1 *).

    Run once before first mirror build to verify the column name guesses
    in source_library_mirror._SQL_HADITH. Update those aliases if any differ.
    """
    from scripts.podcast.source_library_mirror import discover_hadith_schema as _disc  # noqa: PLC0415
    return _disc()


def hadith_lookup(text_en: str, limit: int = 3) -> list[dict[str, Any]]:
    """Find hadith by English text similarity. Returns Arabic text when matched.

    Tries FTS5 mirror (fts_hadith) first; falls back to SQL Server LIKE scan.
    Each result: {hadith_id, collection, hadith_num, arabic, english, score}.
    Returns [] when the mirror has no hadith yet (schema not confirmed) or on error.
    """
    try:
        from scripts.podcast.source_library_mirror import open_mirror  # noqa: PLC0415
        conn = open_mirror()
        if conn is None:
            raise RuntimeError("mirror not available")
        n = max(1, min(int(limit), 20))
        # Check if fts_hadith is populated
        count = conn.execute("SELECT COUNT(*) FROM fts_hadith").fetchone()[0]
        if count == 0:
            raise RuntimeError("fts_hadith empty — run build_mirror() after confirming Ahadees schema")
        q = text_en.replace('"', '""')[:200]
        rows = conn.execute(
            f"SELECT hadith_id, collection, hadith_num, arabic, english FROM fts_hadith WHERE fts_hadith MATCH ? LIMIT ?",
            (q, n),
        ).fetchall()
        return [
            {"hadith_id": r[0], "collection": r[1], "hadith_num": r[2],
             "arabic": r[3], "english": r[4], "score": 1.0, "source": "mirror"}
            for r in rows
        ]
    except Exception:
        pass

    # Fall back to SQL Server LIKE scan (only if column names have been confirmed)
    try:
        kw = _esc(text_en.strip()[:100])
        n = max(1, min(int(limit), 20))
        sql = f"""
SELECT TOP {n}
    AhadeesID         AS hadith_id,
    CollectionName    AS collection,
    HadithNumber      AS hadith_num,
    ArabicText        AS arabic,
    EnglishText       AS english
FROM Ahadees
WHERE EnglishText LIKE '%{kw}%'
  AND ArabicText IS NOT NULL AND ArabicText != ''
ORDER BY AhadeesID
FOR JSON PATH;
"""
        rows = query_json("KQUR", sql) or []
        return [
            {"hadith_id": r.get("hadith_id"), "collection": r.get("collection", ""),
             "hadith_num": r.get("hadith_num"), "arabic": r.get("arabic", ""),
             "english": r.get("english", ""), "score": 0.7, "source": "sql_like"}
            for r in rows
        ]
    except Exception:
        return []
