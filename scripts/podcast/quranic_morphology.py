#!/usr/bin/env python3
"""quranic_morphology.py — Quranic Arabic Corpus morphology: DB builder, query API, CLI.

Builds ``content/knowledge-base/quranic-corpus/morphology.db`` from the corpus
morphology file (GPL, Kais Dukes / corpus.quran.com) and exposes the root/lemma
query API the pipeline consumes: the etymology accuracy gate
(``_etymology.load_morphology_reference``), the deterministic glossary fill
(``fill_glossary_arabic``), and the standalone root-study CLI.

Conventions follow ``source_library_mirror.py``: module-level DB path, one
``_SCHEMA`` executescript constant (tests import it), transactional build with
rollback, ``--dry-run`` / ``--verify`` / ``--db-path`` CLI, per-table counts
printed after every build.

Verify, don't trust: the build hard-asserts the corpus's documented shape —
114 chapters, 6,236 verses, ~77k words, ~128k segments, 1,600+ roots, 3,000+
lemmas — and refuses to write a DB that misses any of those ranges. Every FORM/
LEM/ROOT must convert through the Buckwalter table (``_buckwalter``); characters
outside it are collected and reported, never silently dropped.

The raw corpus file cannot be fetched non-interactively (the download page
requires accepting the GPL terms); when it is absent the builder prints exact
instructions and exits cleanly.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _arabic_coverage import normalize_arabic  # noqa: E402
from _buckwalter import bw2ar, bw_skeleton  # noqa: E402
from _morphology_parse import group_words, parse_segments  # noqa: E402

REPO_ROOT = _HERE.parents[1]
CORPUS_DIR = REPO_ROOT / "content" / "knowledge-base" / "quranic-corpus"
CORPUS_SOURCE = CORPUS_DIR / "source" / "quranic-corpus-morphology-0.4.txt"
MORPHOLOGY_DB = CORPUS_DIR / "morphology.db"

DOWNLOAD_INSTRUCTIONS = f"""\
Corpus file not found: {CORPUS_SOURCE}

The Quranic Arabic Corpus morphology file must be downloaded manually
(the download page requires accepting the GPL license terms):

  1. Open https://corpus.quran.com/download/
  2. Accept the GNU GPL terms (the data is copyright Kais Dukes)
  3. Download quranic-corpus-morphology-0.4.txt
  4. Place it at: {CORPUS_SOURCE}

Then re-run:  python3 scripts/podcast/quranic_morphology.py
"""

# Documented corpus shape — asserted after parse, never assumed.
EXPECTED = {
    "chapters": (114, 114),
    "verses": (6236, 6236),
    "words": (70_000, 85_000),
    "segments": (120_000, 135_000),
    "roots": (1_600, 2_500),
    "lemmas": (3_000, 6_000),
}

_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS segments (
    chapter      INTEGER NOT NULL,
    verse        INTEGER NOT NULL,
    word         INTEGER NOT NULL,
    segment      INTEGER NOT NULL,
    form_bw      TEXT NOT NULL,
    form_ar      TEXT NOT NULL,
    tag          TEXT NOT NULL,
    segment_type TEXT NOT NULL,
    pos          TEXT,
    lemma_bw     TEXT,
    lemma_ar     TEXT,
    lemma_skel   TEXT,
    root_bw      TEXT,
    root_ar      TEXT,
    root_skel    TEXT,
    features     TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (chapter, verse, word, segment)
);
CREATE INDEX IF NOT EXISTS idx_segments_root_skel  ON segments(root_skel);
CREATE INDEX IF NOT EXISTS idx_segments_lemma_skel ON segments(lemma_skel);

CREATE TABLE IF NOT EXISTS words (
    chapter       INTEGER NOT NULL,
    verse         INTEGER NOT NULL,
    word          INTEGER NOT NULL,
    form_bw       TEXT NOT NULL,
    form_ar       TEXT NOT NULL,
    segment_count INTEGER NOT NULL,
    PRIMARY KEY (chapter, verse, word)
);

CREATE TABLE IF NOT EXISTS roots (
    root_bw          TEXT PRIMARY KEY,
    root_ar          TEXT NOT NULL,
    root_skel        TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    lemma_count      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_roots_skel ON roots(root_skel);

CREATE TABLE IF NOT EXISTS lemmas (
    lemma_bw         TEXT PRIMARY KEY,
    lemma_ar         TEXT NOT NULL,
    lemma_skel       TEXT NOT NULL,
    root_bw          TEXT,
    pos              TEXT,
    occurrence_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lemmas_skel ON lemmas(lemma_skel);
CREATE INDEX IF NOT EXISTS idx_lemmas_root ON lemmas(root_bw);
"""


# ─── Build ───────────────────────────────────────────────────────────────────
def build_db(
    db_path: Path | None = None,
    source_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Parse the corpus file and (re)build morphology.db. Returns the counts.

    Raises ``FileNotFoundError`` (with download instructions) when the source
    file is absent, and ``RuntimeError`` when any count falls outside the
    documented corpus shape or any character escapes the Buckwalter table.
    """
    source = Path(source_path or CORPUS_SOURCE)
    if not source.is_file():
        raise FileNotFoundError(DOWNLOAD_INSTRUCTIONS)

    unknown_chars: set[str] = set()

    def _ar(bw: str) -> str:
        try:
            return bw2ar(bw)
        except ValueError:
            unknown_chars.update(c for c in bw if not c.isspace())
            return bw2ar(bw, strict=False)

    seg_rows: list[tuple] = []
    word_rows: list[tuple] = []
    root_occ: Counter[str] = Counter()
    root_lemmas: dict[str, set[str]] = {}
    lemma_occ: Counter[str] = Counter()
    lemma_root: dict[str, str] = {}
    lemma_pos: dict[str, Counter[str]] = {}
    chapters: set[int] = set()
    verses: set[tuple[int, int]] = set()

    with source.open(encoding="utf-8") as fh:
        for word_segs in group_words(parse_segments(fh)):
            loc = word_segs[0]["location"]
            chapters.add(loc["chapter"])
            verses.add((loc["chapter"], loc["verse"]))
            word_bw = "".join(s["form"] for s in word_segs)
            word_rows.append((loc["chapter"], loc["verse"], loc["word"], word_bw, _ar(word_bw), len(word_segs)))
            for s in word_segs:
                lemma, root = s["lemma"], s["root"]
                seg_rows.append(
                    (
                        s["location"]["chapter"],
                        s["location"]["verse"],
                        s["location"]["word"],
                        s["location"]["segment"],
                        s["form"],
                        _ar(s["form"]),
                        s["tag"],
                        s["segment_type"],
                        s["pos"],
                        lemma,
                        _ar(lemma) if lemma else None,
                        bw_skeleton(lemma) if lemma else None,
                        root,
                        _ar(root) if root else None,
                        bw_skeleton(root) if root else None,
                        json.dumps(s["features"], ensure_ascii=False, sort_keys=True),
                    )
                )
                if root:
                    root_occ[root] += 1
                    if lemma:
                        root_lemmas.setdefault(root, set()).add(lemma)
                if lemma:
                    lemma_occ[lemma] += 1
                    if root:
                        lemma_root.setdefault(lemma, root)
                    if s["pos"]:
                        lemma_pos.setdefault(lemma, Counter())[s["pos"]] += 1

    if unknown_chars:
        raise RuntimeError(
            f"characters outside the Buckwalter table: {sorted(unknown_chars)!r} — "
            "extend _buckwalter.py rather than dropping data"
        )

    counts = {
        "chapters": len(chapters),
        "verses": len(verses),
        "words": len(word_rows),
        "segments": len(seg_rows),
        "roots": len(root_occ),
        "lemmas": len(lemma_occ),
    }
    _assert_expected(counts)

    if dry_run:
        return counts

    path = Path(db_path or MORPHOLOGY_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA)
        conn.execute("BEGIN")
        for table in ("segments", "words", "roots", "lemmas"):
            conn.execute(f"DELETE FROM {table}")
        conn.executemany("INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", seg_rows)
        conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?)", word_rows)
        conn.executemany(
            "INSERT INTO roots VALUES (?,?,?,?,?)",
            [(r, _ar(r), bw_skeleton(r), n, len(root_lemmas.get(r, ()))) for r, n in sorted(root_occ.items())],
        )
        conn.executemany(
            "INSERT INTO lemmas VALUES (?,?,?,?,?,?)",
            [
                (
                    lemma,
                    _ar(lemma),
                    bw_skeleton(lemma),
                    lemma_root.get(lemma),
                    (lemma_pos[lemma].most_common(1)[0][0] if lemma in lemma_pos else None),
                    n,
                )
                for lemma, n in sorted(lemma_occ.items())
            ],
        )
        conn.execute("COMMIT")
        conn.execute("PRAGMA optimize")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return counts


def _assert_expected(counts: dict[str, int]) -> None:
    for key, (lo, hi) in EXPECTED.items():
        got = counts[key]
        if not lo <= got <= hi:
            raise RuntimeError(
                f"corpus shape check failed: {key}={got}, expected within [{lo}, {hi}] — "
                "wrong/truncated source file, or a parser regression"
            )


def verify_db(db_path: Path | None = None) -> dict[str, int]:
    """Re-derive the counts from an existing DB and assert the same ranges."""
    conn = open_db(db_path)
    if conn is None:
        raise FileNotFoundError(f"morphology DB absent: {db_path or MORPHOLOGY_DB}")
    try:
        counts = {
            "chapters": conn.execute("SELECT COUNT(DISTINCT chapter) FROM segments").fetchone()[0],
            "verses": conn.execute("SELECT COUNT(*) FROM (SELECT DISTINCT chapter, verse FROM segments)").fetchone()[0],
            "words": conn.execute("SELECT COUNT(*) FROM words").fetchone()[0],
            "segments": conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0],
            "roots": conn.execute("SELECT COUNT(*) FROM roots").fetchone()[0],
            "lemmas": conn.execute("SELECT COUNT(*) FROM lemmas").fetchone()[0],
        }
    finally:
        conn.close()
    _assert_expected(counts)
    return counts


# ─── Query API ───────────────────────────────────────────────────────────────
def open_db(db_path: Path | None = None) -> sqlite3.Connection | None:
    """Read-only connection, or None when the DB does not exist."""
    path = Path(db_path or MORPHOLOGY_DB)
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def query_skeleton(term: str) -> str:
    """The skeleton join key for either input script (Arabic or Buckwalter)."""
    term = (term or "").strip()
    if any("؀" <= c <= "ۿ" for c in term):
        return normalize_arabic(term)
    return bw_skeleton(term.replace("-", "").replace(" ", ""))


def get_by_root(root: str, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Every segment derived from a root (Arabic or Buckwalter input), with locations."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            """SELECT chapter, verse, word, segment, form_bw, form_ar, tag, pos,
                      lemma_bw, lemma_ar, root_bw, root_ar
               FROM segments WHERE root_skel = ?
               ORDER BY chapter, verse, word, segment""",
            (query_skeleton(root),),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def root_summary(root: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Root overview: Arabic + Buckwalter forms, derived lemmas, POS spread, counts."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return None
    try:
        skel = query_skeleton(root)
        head = conn.execute(
            "SELECT root_bw, root_ar, occurrence_count, lemma_count FROM roots WHERE root_skel = ?",
            (skel,),
        ).fetchone()
        if head is None:
            return None
        lemmas = conn.execute(
            """SELECT lemma_bw, lemma_ar, pos, occurrence_count FROM lemmas
               WHERE root_bw = ? ORDER BY occurrence_count DESC, lemma_bw""",
            (head["root_bw"],),
        ).fetchall()
        pos_rows = conn.execute(
            """SELECT pos, COUNT(*) AS n FROM segments
               WHERE root_skel = ? AND pos IS NOT NULL GROUP BY pos ORDER BY n DESC""",
            (skel,),
        ).fetchall()
        samples = conn.execute(
            """SELECT DISTINCT chapter, verse, word FROM segments
               WHERE root_skel = ? ORDER BY chapter, verse, word LIMIT 8""",
            (skel,),
        ).fetchall()
        return {
            "root_bw": head["root_bw"],
            "root_ar": head["root_ar"],
            "occurrences": head["occurrence_count"],
            "lemma_count": head["lemma_count"],
            "lemmas": [dict(r) for r in lemmas],
            "pos_distribution": {r["pos"]: r["n"] for r in pos_rows},
            "sample_locations": [f"{r['chapter']}:{r['verse']}:{r['word']}" for r in samples],
        }
    except sqlite3.OperationalError:
        return None
    finally:
        if own:
            conn.close()


def get_word(chapter: int, verse: int, word: int, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """One word: its surface form and its morphological segments."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return None
    try:
        head = conn.execute(
            "SELECT * FROM words WHERE chapter=? AND verse=? AND word=?", (chapter, verse, word)
        ).fetchone()
        if head is None:
            return None
        segs = conn.execute(
            "SELECT * FROM segments WHERE chapter=? AND verse=? AND word=? ORDER BY segment",
            (chapter, verse, word),
        ).fetchall()
        out = dict(head)
        out["segments"] = [dict(s) for s in segs]
        return out
    except sqlite3.OperationalError:
        return None
    finally:
        if own:
            conn.close()


def get_verse(chapter: int, verse: int, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """All words of a verse, each with its segments."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return []
    try:
        words = conn.execute(
            "SELECT word FROM words WHERE chapter=? AND verse=? ORDER BY word", (chapter, verse)
        ).fetchall()
        return [w for r in words if (w := get_word(chapter, verse, r["word"], conn)) is not None]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def search_lemma(term: str, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Lemmas matching a term (Arabic or Buckwalter), by skeleton."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT * FROM lemmas WHERE lemma_skel = ? ORDER BY occurrence_count DESC",
            (query_skeleton(term),),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def list_roots(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Every root with counts, most frequent first."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return []
    try:
        rows = conn.execute("SELECT * FROM roots ORDER BY occurrence_count DESC, root_bw").fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


def list_lemmas(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Every lemma with counts, most frequent first."""
    own = conn is None
    conn = conn or open_db()
    if conn is None:
        return []
    try:
        rows = conn.execute("SELECT * FROM lemmas ORDER BY occurrence_count DESC, lemma_bw").fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        if own:
            conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────
def _print_counts(counts: dict[str, int], db_path: Path | None) -> None:
    for key in ("chapters", "verses", "words", "segments", "roots", "lemmas"):
        lo, hi = EXPECTED[key]
        rng = f"= {lo}" if lo == hi else f"in [{lo}, {hi}]"
        print(f"  {key:>9}: {counts[key]:>7,}   (expected {rng})")
    path = Path(db_path or MORPHOLOGY_DB)
    if path.is_file():
        print(f"  morphology.db size: {path.stat().st_size / 1e6:.1f} MB")


def _print_root(root: str) -> int:
    summary = root_summary(root)
    if summary is None:
        print(f"root not found: {root!r} (skeleton {query_skeleton(root)!r})")
        return 1
    print(f"ROOT {summary['root_bw']}  {summary['root_ar']}")
    print(f"  occurrences: {summary['occurrences']:,}   lemmas: {summary['lemma_count']}")
    print("  POS: " + ", ".join(f"{p}={n}" for p, n in summary["pos_distribution"].items()))
    print("  derived lemmas:")
    for lem in summary["lemmas"]:
        pos = f" [{lem['pos']}]" if lem["pos"] else ""
        print(f"    {lem['lemma_bw']:<16} {lem['lemma_ar']:<12}{pos}  x{lem['occurrence_count']}")
    print("  sample locations: " + ", ".join(summary["sample_locations"]))
    return 0


def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="parse + verify counts, write nothing")
    ap.add_argument("--verify", action="store_true", help="verify an existing DB's counts")
    ap.add_argument("--db-path", type=Path, default=None)
    ap.add_argument("--source", type=Path, default=None)
    ap.add_argument("--root", help="query mode: print a root's derived family")
    args = ap.parse_args()

    if args.root:
        return _print_root(args.root)

    try:
        if args.verify:
            counts = verify_db(args.db_path)
            print("morphology.db verified:")
        else:
            counts = build_db(args.db_path, args.source, dry_run=args.dry_run)
            print("morphology.db " + ("dry-run (nothing written):" if args.dry_run else "built:"))
    except FileNotFoundError as e:
        print(e)
        return 2
    except RuntimeError as e:
        print(f"FAILED: {e}")
        return 1
    _print_counts(counts, args.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
