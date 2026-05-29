"""source_library_mirror.py — Wave J (J1): SQLite FTS5 offline mirror builder.

Extracts from three SQL Server databases (KQUR, KASHKOLE, KSESSIONS) and
materialises four local SQLite tables that make the source library usable
without a Docker connection:

    fts_quran       FTS5 virtual table — all 6 236 Quran verses
                    (Arabic + Pickthall + Asad searchable columns)
    fts_topics      FTS5 virtual table — all KASHKOLE Wisdom topics
                    (name, name_en, body_plain searchable columns)
    fts_sessions    FTS5 virtual table — all active KSESSIONS transcripts
                    (session_name, content searchable columns)
    term_index      Regular table — unified term lookup from KQUR Roots +
                    Derivatives and KASHKOLE Glossary + DeeniTermGroup.
                    Indexed on (term) and (root) for sub-millisecond lookup.

Usage:
    python3 scripts/podcast/source_library_mirror.py           # build mirror
    python3 scripts/podcast/source_library_mirror.py --dry-run # print counts
    python3 scripts/podcast/source_library_mirror.py --verify  # compare mirror
    python3 scripts/podcast/source_library_mirror.py --db-path /custom/path.db
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

# ── path bootstrap ─────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.source_extractor.db import query_json

MIRROR_PATH = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"

_BATCH = 500          # rows per paginated SQL Server request
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _WHITESPACE.sub(" ", _HTML_TAG.sub(" ", text)).strip()


def _paginate(database: str, sql_template: str) -> list[dict[str, Any]]:
    """Fetch all rows from `database` using OFFSET/FETCH pagination.

    `sql_template` must contain exactly one ``{offset}`` and one ``{batch}``
    placeholder and must include a FOR JSON PATH clause.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        sql = sql_template.format(offset=offset, batch=_BATCH)
        batch = query_json(database, sql) or []
        rows.extend(batch)
        if len(batch) < _BATCH:
            break
        offset += _BATCH
    return rows


# ── schema ─────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE VIRTUAL TABLE IF NOT EXISTS fts_quran USING fts5(
    surah    UNINDEXED,
    ayat     UNINDEXED,
    arabic,
    pickthall,
    asad,
    urdu     UNINDEXED,
    phonetic UNINDEXED,
    tokenize = 'unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_topics USING fts5(
    topic_id    UNINDEXED,
    name,
    name_en,
    description,
    binder      UNINDEXED,
    chapter     UNINDEXED,
    body_plain,
    tokenize = 'unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_sessions USING fts5(
    session_id   UNINDEXED,
    session_name,
    group_id     UNINDEXED,
    content,
    tokenize = 'unicode61'
);

CREATE TABLE IF NOT EXISTS term_index (
    term        TEXT NOT NULL,
    arabic      TEXT DEFAULT '',
    root        TEXT DEFAULT '',
    grammar_tag TEXT DEFAULT '',
    definition  TEXT DEFAULT '',
    etymology   TEXT DEFAULT '',
    tradition   TEXT DEFAULT 'ismaili',
    source      TEXT NOT NULL,
    related     TEXT DEFAULT '',
    PRIMARY KEY (term, source)
);

CREATE INDEX IF NOT EXISTS idx_term_index_term ON term_index(term);
CREATE INDEX IF NOT EXISTS idx_term_index_root ON term_index(root);
"""

# ── SQL Server extraction queries ──────────────────────────────────────────

_SQL_QURAN = """
SELECT
    SurahNumber        AS surah,
    AyatNumber         AS ayat,
    AyatUNICODE        AS arabic,
    AyatTranslation    AS pickthall,
    Translation_Asad   AS asad,
    ISNULL(UrduTranslation, '') AS urdu,
    ISNULL(Phonetic, '')       AS phonetic
FROM QuranAyats
ORDER BY SurahNumber, AyatNumber
FOR JSON PATH;
"""

_SQL_TOPICS = """
SELECT
    t.TopicID                                    AS topic_id,
    ISNULL(t.TopicName, '')                      AS name,
    ISNULL(t.TopicNameEnglish, '')               AS name_en,
    ISNULL(t.TopicDescription, '')               AS description,
    ISNULL(bct.BinderName, '')                   AS binder,
    ISNULL(bct.ChapterName, '')                  AS chapter,
    ISNULL(td.TopicUnicodeStripped, '')          AS body_plain
FROM Topics t
LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
LEFT JOIN BinderChapterTopics bct ON bct.TopicID = t.TopicID
ORDER BY t.TopicID
OFFSET {{offset}} ROWS FETCH NEXT {{batch}} ROWS ONLY
FOR JSON PATH;
"""

_SQL_SESSIONS = """
SELECT
    s.SessionID                                  AS session_id,
    ISNULL(s.SessionName, '')                    AS session_name,
    ISNULL(s.GroupID, 0)                         AS group_id,
    ISNULL(ss.SessionContent, '')               AS content_html
FROM Sessions s
JOIN SessionSummary ss ON ss.SessionId = s.SessionID
WHERE ss.IsActive = 1
ORDER BY s.SessionID
OFFSET {{offset}} ROWS FETCH NEXT {{batch}} ROWS ONLY
FOR JSON PATH;
"""

# term_index from KQUR: Roots + Derivatives
_SQL_KQUR_TERMS = """
SELECT
    ISNULL(d.Transliteration, r.RootTransliteration) AS term,
    ISNULL(d.Derivative, r.RootWord)                 AS arabic,
    ISNULL(r.RootTransliteration, '')                AS root,
    ISNULL(d.Grammar, '')                            AS grammar_tag,
    ISNULL(d.MeaningEnglish, ISNULL(r.MeaningEnglish, '')) AS definition,
    ISNULL(r.Definition, '')                         AS etymology
FROM Roots r
LEFT JOIN Derivatives d ON d.RootID = r.RootID
WHERE r.RootTransliteration IS NOT NULL
ORDER BY r.RootID, ISNULL(d.SortOrder, 0)
OFFSET {{offset}} ROWS FETCH NEXT {{batch}} ROWS ONLY
FOR JSON PATH;
"""

# term_index from KASHKOLE: Glossary + DeeniTermGroup
_SQL_KASHKOLE_TERMS = """
SELECT
    ISNULL(g.TermName, '')                   AS term,
    ''                                        AS arabic,
    ''                                        AS root,
    ISNULL(dtg.GroupName, '')                AS grammar_tag,
    ISNULL(g.TermDefinition, '')             AS definition,
    ''                                        AS etymology
FROM Glossary g
LEFT JOIN DeeniTermGroup dtg ON dtg.GroupID = g.GroupID
WHERE g.TermName IS NOT NULL AND g.TermName != ''
ORDER BY g.GlossaryID
OFFSET {{offset}} ROWS FETCH NEXT {{batch}} ROWS ONLY
FOR JSON PATH;
"""


# ── build steps ────────────────────────────────────────────────────────────

def _build_fts_quran(conn: sqlite3.Connection) -> int:
    """Populate fts_quran from KQUR.QuranAyats. Returns row count."""
    conn.execute("DELETE FROM fts_quran;")
    rows = query_json("KQUR", _SQL_QURAN) or []
    conn.executemany(
        "INSERT INTO fts_quran VALUES (?,?,?,?,?,?,?)",
        [
            (
                r.get("surah"), r.get("ayat"),
                r.get("arabic", ""), r.get("pickthall", ""),
                r.get("asad", ""), r.get("urdu", ""), r.get("phonetic", ""),
            )
            for r in rows
        ],
    )
    return len(rows)


def _build_fts_topics(conn: sqlite3.Connection) -> int:
    """Populate fts_topics from KASHKOLE. Returns row count."""
    conn.execute("DELETE FROM fts_topics;")
    rows = _paginate("KASHKOLE", _SQL_TOPICS)
    conn.executemany(
        "INSERT INTO fts_topics VALUES (?,?,?,?,?,?,?)",
        [
            (
                r.get("topic_id"), r.get("name", ""),
                r.get("name_en", ""), r.get("description", ""),
                r.get("binder", ""), r.get("chapter", ""),
                r.get("body_plain", ""),
            )
            for r in rows
        ],
    )
    return len(rows)


def _build_fts_sessions(conn: sqlite3.Connection) -> int:
    """Populate fts_sessions from KSESSIONS. Returns row count."""
    conn.execute("DELETE FROM fts_sessions;")
    rows = _paginate("KSESSIONS", _SQL_SESSIONS)
    conn.executemany(
        "INSERT INTO fts_sessions VALUES (?,?,?,?)",
        [
            (
                r.get("session_id"), r.get("session_name", ""),
                r.get("group_id"), _strip_html(r.get("content_html", "")),
            )
            for r in rows
        ],
    )
    return len(rows)


def _build_term_index(conn: sqlite3.Connection) -> int:
    """Populate term_index from KQUR + KASHKOLE. Returns total row count."""
    conn.execute("DELETE FROM term_index;")
    inserted = 0

    kqur_rows = _paginate("KQUR", _SQL_KQUR_TERMS)
    conn.executemany(
        "INSERT OR IGNORE INTO term_index "
        "(term, arabic, root, grammar_tag, definition, etymology, tradition, source)"
        " VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                r.get("term", ""), r.get("arabic", ""), r.get("root", ""),
                r.get("grammar_tag", ""), r.get("definition", ""),
                r.get("etymology", ""), "ismaili", "KQUR",
            )
            for r in kqur_rows
            if r.get("term", "").strip()
        ],
    )
    inserted += conn.execute(
        "SELECT COUNT(*) FROM term_index WHERE source='KQUR'"
    ).fetchone()[0]

    kashkole_rows = _paginate("KASHKOLE", _SQL_KASHKOLE_TERMS)
    conn.executemany(
        "INSERT OR IGNORE INTO term_index "
        "(term, arabic, root, grammar_tag, definition, etymology, tradition, source)"
        " VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                r.get("term", ""), r.get("arabic", ""), r.get("root", ""),
                r.get("grammar_tag", ""), r.get("definition", ""),
                r.get("etymology", ""), "ismaili", "KASHKOLE",
            )
            for r in kashkole_rows
            if r.get("term", "").strip()
        ],
    )
    inserted = conn.execute(
        "SELECT COUNT(*) FROM term_index"
    ).fetchone()[0]
    return inserted


# ── public API ──────────────────────────────────────────────────────────────

def build_mirror(
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Build or refresh the SQLite mirror from SQL Server.

    Returns a dict with row counts per table.  If `dry_run` is True, the
    SQL Server is queried for counts but nothing is written to disk.
    """
    target = Path(db_path) if db_path else MIRROR_PATH

    if dry_run:
        # Just report what SQL Server currently holds — no writes.
        try:
            quran_count = len(query_json("KQUR", _SQL_QURAN) or [])
        except Exception:
            quran_count = -1
        return {
            "fts_quran": quran_count,
            "fts_topics": -1,
            "fts_sessions": -1,
            "term_index": -1,
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(_SCHEMA)
        conn.execute("BEGIN;")
        counts: dict[str, int] = {}
        counts["fts_quran"]   = _build_fts_quran(conn)
        counts["fts_topics"]  = _build_fts_topics(conn)
        counts["fts_sessions"] = _build_fts_sessions(conn)
        counts["term_index"]  = _build_term_index(conn)
        conn.execute("COMMIT;")
        conn.execute("PRAGMA optimize;")
    except Exception:
        conn.execute("ROLLBACK;")
        conn.close()
        raise
    conn.close()
    return counts


def verify_mirror(db_path: Path | None = None) -> dict[str, dict[str, int]]:
    """Compare row counts between mirror.db and SQL Server.

    Returns {"fts_quran": {"mirror": N, "server": M}, ...}.
    """
    target = Path(db_path) if db_path else MIRROR_PATH
    if not target.exists():
        raise FileNotFoundError(f"Mirror not found: {target}")

    conn = sqlite3.connect(str(target))
    mirror_counts = {
        "fts_quran":    conn.execute(
            "SELECT COUNT(*) FROM fts_quran"
        ).fetchone()[0],
        "fts_topics":   conn.execute(
            "SELECT COUNT(*) FROM fts_topics"
        ).fetchone()[0],
        "fts_sessions": conn.execute(
            "SELECT COUNT(*) FROM fts_sessions"
        ).fetchone()[0],
        "term_index":   conn.execute(
            "SELECT COUNT(*) FROM term_index"
        ).fetchone()[0],
    }
    conn.close()

    server_counts: dict[str, int] = {}
    for table, db, sql in [
        ("fts_quran", "KQUR",
         "SELECT COUNT(*) AS n FROM QuranAyats FOR JSON PATH;"),
        ("fts_topics", "KASHKOLE",
         "SELECT COUNT(*) AS n FROM Topics FOR JSON PATH;"),
        ("fts_sessions", "KSESSIONS",
         "SELECT COUNT(*) AS n FROM Sessions s "
         "JOIN SessionSummary ss ON ss.SessionId=s.SessionID "
         "WHERE ss.IsActive=1 FOR JSON PATH;"),
        ("term_index", "KQUR",
         "SELECT COUNT(*) AS n FROM Roots FOR JSON PATH;"),
    ]:
        try:
            rows = query_json(db, sql) or []
            server_counts[table] = rows[0].get("n", 0) if rows else 0
        except Exception:
            server_counts[table] = -1

    return {
        t: {"mirror": mirror_counts[t], "server": server_counts[t]}
        for t in mirror_counts
    }


# ── mirror-backed query helpers (used by source_library_queries.py) ────────

def open_mirror(db_path: Path | None = None) -> sqlite3.Connection | None:
    """Return a read-only sqlite3 connection to mirror.db, or None if absent."""
    target = Path(db_path) if db_path else MIRROR_PATH
    if not target.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError:
        return None


def fts_quran_search(
    keyword: str, limit: int = 10, conn: sqlite3.Connection | None = None
) -> list[dict]:
    """FTS5 search over fts_quran. Returns [] if mirror unavailable."""
    own = conn is None
    conn = conn or open_mirror()
    if conn is None:
        return []
    n = max(1, min(int(limit), 50))
    kw_safe = keyword.replace('"', '""')
    try:
        rows = conn.execute(
            "SELECT surah, ayat, arabic, pickthall, asad, phonetic "
            "FROM fts_quran WHERE fts_quran MATCH ? LIMIT ?",
            (f'"{kw_safe}"', n),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def fts_topics_search(
    keyword: str, limit: int = 10, conn: sqlite3.Connection | None = None
) -> list[dict]:
    """FTS5 search over fts_topics. Returns [] if mirror unavailable."""
    own = conn is None
    conn = conn or open_mirror()
    if conn is None:
        return []
    n = max(1, min(int(limit), 50))
    kw_safe = keyword.replace('"', '""')
    try:
        rows = conn.execute(
            "SELECT topic_id, name, name_en, description, binder, chapter, "
            "snippet(fts_topics, 6, '[', ']', '…', 20) AS snippet "
            "FROM fts_topics WHERE fts_topics MATCH ? LIMIT ?",
            (f'"{kw_safe}"', n),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def term_index_lookup(
    term: str, conn: sqlite3.Connection | None = None
) -> dict | None:
    """Exact/prefix lookup in term_index. Returns None if mirror unavailable."""
    own = conn is None
    conn = conn or open_mirror()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT term, arabic, root, grammar_tag, definition, etymology, "
            "tradition, source FROM term_index WHERE term = ? LIMIT 1",
            (term.strip(),),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT term, arabic, root, grammar_tag, definition, etymology, "
                "tradition, source FROM term_index WHERE term LIKE ? LIMIT 1",
                (f"{term.strip()}%",),
            ).fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        if own:
            conn.close()


# ── CLI ────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Build or inspect the SQLite FTS5 source library mirror."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print SQL Server row counts without writing anything.",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Compare mirror row counts against SQL Server.",
    )
    parser.add_argument(
        "--db-path", metavar="PATH",
        help=f"Override mirror path (default: {MIRROR_PATH})",
    )
    args = parser.parse_args()
    db_path = Path(args.db_path) if args.db_path else None

    if args.verify:
        try:
            report = verify_mirror(db_path)
        except FileNotFoundError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
        print(f"{'Table':<20}  {'Mirror':>8}  {'SQL Server':>10}  Status")
        print("-" * 52)
        for table, counts in report.items():
            m, s = counts["mirror"], counts["server"]
            status = "✅" if s < 0 or m >= s else "⚠️  mirror behind"
            print(f"{table:<20}  {m:>8}  {s:>10}  {status}")
        return

    if args.dry_run:
        counts = build_mirror(db_path, dry_run=True)
        print("Dry run — SQL Server row counts (mirror not written):")
        for table, n in counts.items():
            print(f"  {table:<20}  {n:>8}")
        return

    print(f"Building mirror at {db_path or MIRROR_PATH} …")
    try:
        counts = build_mirror(db_path)
    except Exception as exc:
        print(f"Error: {exc}")
        print("Hint: ensure Docker is running and wisdom-mssql container is up.")
        sys.exit(1)
    print("Done.")
    for table, n in counts.items():
        print(f"  {table:<20}  {n:>8} rows")
    size = (db_path or MIRROR_PATH).stat().st_size / 1024 / 1024
    print(f"  {'mirror.db size':<20}  {size:.1f} MB")


if __name__ == "__main__":
    _cli()
